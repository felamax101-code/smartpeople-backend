from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from authentication.models import ProfileBlock
from Profile.models import ProfilePrivacy
from feed.models import Conversation, Message,MessageDeletes,ConversationDeletes,ConversationParticipant,MessageRead
from .serializers import (
    ConversationSerializer, ConversationCreateSerializer,
    MessageSerializer, MessageCreateSerializer,
)
from django.contrib.auth import get_user_model
from django.db.models import F


User = get_user_model()


class ConversationListCreateView(APIView):

    def get(self, request):
        deleted_conversation_ids = ConversationDeletes.objects.filter(
            user=request.user, is_active=True
        ).values("conversation_id")

        conversations = (
            Conversation.objects
            .filter(participants=request.user)
            .exclude(id__in=deleted_conversation_ids)
            .exclude(messages__isnull=True)  # drop conversations with zero messages
            .order_by(F("last_message_at").desc(nulls_last=True))
        )

        serializer = ConversationSerializer(
            conversations, many=True, context={"request": request}
        )
        return Response(serializer.data)

    def post(self, request):
        serializer = ConversationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if str(data["recipient_id"]) == str(request.user.id):
            return Response({"detail": "Cannot message yourself"}, status=400)

        recipient = get_object_or_404(User, id=data["recipient_id"])
        permission = check_messaging_permission(request.user, recipient)
        if not permission["allowed"]:
            return Response({"detail": permission["reason"]}, status=403)

        # ── block check ──
        if is_user_blocked(blocker_id=recipient.id, target_id=request.user.id):
            return Response({"detail": "You cannot send messages to this user"}, status=403)
        # find an existing 1-to-1 conversation between these two, or create one
        conversation = (
            Conversation.objects.filter(is_group=False, participants=request.user)
            .filter(participants=recipient)
            .first()
        )
        created = False
        if not conversation:
            conversation = Conversation.objects.create(
                post_id=data.get("post_id"),
                created_by=request.user,
            )
            conversation.participants.add(
                request.user, through_defaults={"is_admin": True}
            )
            conversation.participants.add(recipient)
            created = True

        # message = Message.objects.create(
        #     conversation=conversation,
        #     sender=request.user,
        #     body=data["initial_message"],
        #     message_type="text",
        # )
        # _update_last_message(conversation, message)
        # _broadcast_message(conversation.id, message)

        out = ConversationSerializer(conversation, context={"request": request})
        return Response(out.data, status=status.HTTP_201_CREATED)


class ConversationMessagesView(APIView):
    def get(self, request, conversation_id):
        conversation = get_object_or_404(
            Conversation, id=conversation_id, participants=request.user
        )

        before_id = request.query_params.get("before_id")
        limit = min(int(request.query_params.get("limit", 10)), 100)

        # exclude messages this user has "deleted for me"
        deleted_ids = MessageDeletes.objects.filter(user=request.user).values("message_id")

        qs = (
            Message.objects
            .filter(conversation=conversation)
            .exclude(id__in=deleted_ids)
            .order_by("-created_at")
        )

        if before_id:
            cursor_message = Message.objects.filter(id=before_id).first()
            if cursor_message:
                qs = qs.filter(created_at__lt=cursor_message.created_at)

        # if this user deleted the whole conversation at some point, don't show anything before that
        conv_deletion = ConversationDeletes.objects.filter(
            conversation=conversation, user=request.user
        ).order_by("-created_at").first()
        if conv_deletion:
            qs = qs.filter(created_at__gt=conv_deletion.created_at)

        rows = list(qs[: limit + 1])   # fetch one extra to detect "is there more"
        has_next = len(rows) > limit
        messages = list(reversed(rows[:limit] if has_next else rows))  # oldest-first for display

        # ── mark unread messages as read, 
        unread_ids = [
            m.id for m in messages
            if not m.is_read and str(m.sender_id) != str(request.user.id)
        ]

        if unread_ids:
            if conversation.is_group:
                now = timezone.now()
                MessageRead.objects.bulk_create(
                    [MessageRead(message_id=mid, user=request.user, read_at=now) for mid in unread_ids],
                    ignore_conflicts=True, 
                )
            else:
                Message.objects.filter(id__in=unread_ids).update(
                    is_read=True, read_at=timezone.now()
                )
                for mid in unread_ids:
                    _broadcast(conversation.id, "read", {"message_id": str(mid), "readers": [str(request.user.id)]})

        # ── batch-load readers for group messages, avoids N+1 ──
        readers_map = {}
        if conversation.is_group and messages:
            reads = (
                MessageRead.objects
                .filter(message_id__in=[m.id for m in messages])
                .select_related("user")
                .order_by("read_at")
            )
            for r in reads:
                readers_map.setdefault(str(r.message_id), []).append({
                    "user_id": str(r.user_id),
                    "username": r.user.username,
                    "avatar": r.user.avatar,
                    "read_at": r.read_at.isoformat(),
                })
        reactions_map = {
            str(m.id): get_reaction_summary(m.id, request.user.id) for m in messages
        }

        is_blocked = False
        if not conversation.is_group:
            other = conversation.participants.exclude(id=request.user.id).first()
            if other:
                is_blocked = is_user_blocked(blocker_id=request.user.id, target_id=other.id)
        data = MessageSerializer(messages, many=True).data
        for item in data:
            item["readers"] = readers_map.get(item["id"], [])

        return Response({
            "success": True,
            "data": {
                "messages": [
                    _build_message_response(
                        m, request=request, is_target_blocked=is_blocked,
                        readers=readers_map.get(str(m.id), []),
                        reactions=reactions_map.get(str(m.id), []),
                    )
                    for m in messages
                ],
                "has_next": has_next,
            },
        })


    def post(self, request, conversation_id):
        conversation = get_object_or_404(
            Conversation, id=conversation_id, participants=request.user
        )

        if not conversation.is_group:
            other = conversation.participants.exclude(id=request.user.id).first()
            if other and is_user_blocked(blocker_id=other.id, target_id=request.user.id):
                return Response({"detail": "You cannot send messages to this user"}, status=403)

        serializer = MessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        message_type=data.get("message_type","text")
        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            body=data.get("body"),
            message_type=message_type,
            reply_to_id=data.get("reply_to"),
            image_url=data.get("image_url") if message_type == "image" else None,
            video_url=data.get("video_url") if message_type == "video" else None,
        )
        _update_last_message(conversation, message)

        response_data = _build_message_response(
            message, request=request, is_target_blocked=False, readers=[], reactions=[],
        )
        _broadcast(conversation.id, "message", response_data)

        return Response(response_data, status=status.HTTP_201_CREATED) 


def _update_last_message(conversation, message):
    preview = message.body[:97] + "..." if message.body and len(message.body) > 100 else message.body
    conversation.last_message_preview = preview
    conversation.last_message_at = message.created_at
    conversation.save(update_fields=["last_message_preview", "last_message_at"])


def _broadcast_message(conversation_id, message):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"conversation_{conversation_id}",
        {
            "type": "chat.message",
            "data": {
                "type": "message",
                "data": {
                    "id": str(message.id),
                    "conversation_id": str(conversation_id),
                    "sender_id": str(message.sender_id),
                    "sender_username": message.sender.username,
                    "body": message.body,
                    "message_type": message.message_type,
                    "created_at": message.created_at.isoformat(),
                },
            },
        }
    )
    
class MessageReactionView(APIView):

    def post(self, request, conversation_id, message_id):
        get_object_or_404(Conversation, id=conversation_id, participants=request.user)
        message = get_object_or_404(Message, id=message_id, is_deleted=False)

        emoji = request.data.get("emoji")
        if not emoji:
            return Response({"detail": "emoji is required"}, status=400)

        MessageReaction.objects.get_or_create(
            message=message, user=request.user, emoji=emoji
        )  # get_or_create is the idempotency here — same role as ON CONFLICT DO NOTHING

        summary = get_reaction_summary(message_id, request.user.id)
        _broadcast_reaction(conversation_id, message_id, emoji, request.user.id, "reaction_added", summary)
        return Response({"reactions": summary})

    def delete(self, request, conversation_id, message_id, emoji):
        get_object_or_404(Conversation, id=conversation_id, participants=request.user)
        message = get_object_or_404(Message, id=message_id)

        MessageReaction.objects.filter(
            message=message, user=request.user, emoji=emoji
        ).delete()

        summary = get_reaction_summary(message_id, request.user.id)
        _broadcast_reaction(conversation_id, message_id, emoji, request.user.id, "reaction_removed", summary)
        return Response({"reactions": summary})


def _broadcast_reaction(conversation_id, message_id, emoji, user_id, event_type, summary):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"conversation_{conversation_id}",
        {
            "type": "chat.message",  # reuses the same handler as regular messages
            "data": {
                "type": event_type,
                "data": {
                    "message_id": str(message_id),
                    "emoji": emoji,
                    "user_id": str(user_id),
                    "reactions": summary,
                },
            },
        }
    )
    
    
from django.utils import timezone
from django.db.models import Count, Q


class MessageReadView(APIView):
    """PATCH /messages/<message_id>/read/"""

    def patch(self, request, message_id):
        message = get_object_or_404(Message, id=message_id)

        if str(message.sender_id) == str(request.user.id):
            return Response({"success": True})  # nothing to do, matches original

        conversation = message.conversation

        if not conversation.is_group:
            if not message.is_read:
                message.is_read = True
                message.read_at = timezone.now()
                message.save(update_fields=["is_read", "read_at"])

            _broadcast(conversation.id, "read", {
                "message_id": str(message_id),
                "reader_id": str(request.user.id),
                "read_at": message.read_at.isoformat(),
            })
            return Response({"success": True})

        # group path
        MessageRead.objects.get_or_create(message=message, user=request.user)

        total_non_senders = conversation.participants.exclude(id=message.sender_id).count()
        read_count = MessageRead.objects.filter(message=message).count()

        if read_count >= total_non_senders and not message.is_read:
            message.is_read = True
            message.read_at = timezone.now()
            message.save(update_fields=["is_read", "read_at"])

        readers = [
            {
                "user_id": str(r.user_id),
                "username": r.user.username,
                "avatar": r.user.avatar,
                "read_at": r.read_at.isoformat(),
            }
            for r in MessageRead.objects.filter(message=message).select_related("user").order_by("read_at")
        ]

        _broadcast(conversation.id, "read", {"message_id": str(message_id), "readers": readers})
        return Response({"success": True})


class OfferActionView(APIView):
    """POST /messages/<message_id>/offer/"""

    def post(self, request, message_id):
        message = get_object_or_404(Message, id=message_id)

        if message.message_type != "offer":
            return Response({"detail": "This message is not an offer"}, status=400)
        if str(message.sender_id) == str(request.user.id):
            return Response({"detail": "You cannot respond to your own offer"}, status=400)

        action = request.data.get("action")  # "accepted" | "declined" | "countered"
        counter_amount = request.data.get("counter_amount")
        if action == "countered" and not counter_amount:
            return Response({"detail": "counter_amount required when action is countered"}, status=400)

        offer_data = dict(message.offer_data or {})
        offer_data["status"] = action
        if action == "countered":
            offer_data["counter_amount"] = counter_amount
        message.offer_data = offer_data
        message.save(update_fields=["offer_data"])

        _broadcast(message.conversation_id, "offer_update", {
            "message_id": str(message_id), "offer_data": offer_data,
        })
        return Response({"success": True, "offer_data": offer_data})


class MessageDeleteView(APIView):
    """DELETE /conversations/<conversation_id>/messages/<message_id>/ — soft delete, sender only"""

    def delete(self, request, conversation_id, message_id):
        message = get_object_or_404(Message, id=message_id, conversation_id=conversation_id)

        if str(message.sender_id) != str(request.user.id):
            return Response({"detail": "You can only delete your own messages"}, status=403)

        if not message.is_deleted:
            message.is_deleted = True
            message.save(update_fields=["is_deleted"])
            Conversation.objects.filter(id=conversation_id).update(
                last_message_at=timezone.now(),
                last_message_preview="Message deleted",
            )
            _broadcast(conversation_id, "message_deleted", {
                "message_id": str(message_id),
                "conversation_id": str(conversation_id),
                "deleted_by": str(request.user.id),
            })

        return Response(MessageSerializer(message).data)


class MessageDeleteForMeView(APIView):
    """DELETE /conversations/message/delete-for-me/<conversation_id>/<message_id>/"""

    def delete(self, request, conversation_id, message_id):
        get_object_or_404(Conversation, id=conversation_id, participants=request.user)
        MessageDeletes.objects.get_or_create(message_id=message_id, user=request.user)
        return Response({"success": True})


class ConversationDeleteView(APIView):
    """DELETE /conversations/delete/<conversation_id>/conversation/ — delete-for-me only"""

    def delete(self, request, conversation_id):
        conversation = get_object_or_404(Conversation, id=conversation_id)
        record, created = ConversationDeletes.objects.get_or_create(
            conversation=conversation, user=request.user,
            defaults={"is_active": True},
        )
        if not created:
            record.is_active = True
            record.created_at = timezone.now()
            record.save(update_fields=["is_active", "created_at"])
        return Response({"success": True})

class GroupCreateView(APIView):
    """POST /conversations/groups/"""

    def post(self, request):
        group_name = request.data.get("group_name", "").strip()
        participant_ids = request.data.get("participant_ids", [])
        initial_message = request.data.get("initial_message", "").strip()

        if not group_name:
            return Response({"detail": "Group name cannot be empty"}, status=400)
        if len(participant_ids) < 2:
            return Response({"detail": "A group requires at least 2 other participants"}, status=400)
        if len(participant_ids) > 49:
            return Response({"detail": "A group can have at most 50 members"}, status=400)
        if not initial_message:
            return Response({"detail": "Initial message cannot be empty"}, status=400)
        if str(request.user.id) in [str(p) for p in participant_ids]:
            return Response({"detail": "Do not include yourself in participant_ids"}, status=400)

        all_member_ids = list({str(request.user.id), *[str(p) for p in participant_ids]})
        found_users = {str(u.id): u for u in User.objects.filter(id__in=all_member_ids)}
        missing = [uid for uid in all_member_ids if uid not in found_users]
        if missing:
            return Response({"detail": f"User(s) not found: {missing}"}, status=404)

        for i, uid_a in enumerate(all_member_ids):
            for uid_b in all_member_ids[i + 1:]:
                if is_user_blocked(blocker_id=uid_a, target_id=uid_b) or is_user_blocked(blocker_id=uid_b, target_id=uid_a):
                    return Response({
                        "detail": f"Cannot create group: {found_users[uid_a].username} and "
                                  f"{found_users[uid_b].username} have a block between them"
                    }, status=403)

        conversation = Conversation.objects.create(
            is_group=True, group_name=group_name, created_by=request.user,
        )
        now = timezone.now()
        for uid in all_member_ids:
            ConversationParticipant.objects.create(
                conversation=conversation, user_id=uid,
                is_admin=(uid == str(request.user.id)), joined_at=now,
            )

        message = Message.objects.create(
            conversation=conversation, sender=request.user, body=initial_message, message_type="text",
        )
        _update_last_message(conversation, message)
        _broadcast(conversation.id, "message", {
            "id": str(message.id), "conversation_id": str(conversation.id),
            "sender_id": str(request.user.id), "sender_username": request.user.username,
            "body": message.body, "message_type": "text", "created_at": message.created_at.isoformat(),
        })

        for uid in participant_ids:
            _notify_user(uid, "new_conversation", {
                "conversation_id": str(conversation.id), "is_group": True,
                "group_name": group_name, "creator_id": str(request.user.id),
                "creator_username": request.user.username,
            })

        out = ConversationSerializer(conversation, context={"request": request})
        return Response(out.data, status=status.HTTP_201_CREATED)


class GroupMembersView(APIView):
    """GET /conversations/groups/<conversation_id>/members/  and  POST to add members"""

    def get(self, request, conversation_id):
        get_object_or_404(Conversation, id=conversation_id, participants=request.user)
        rows = (
            ConversationParticipant.objects
            .filter(conversation_id=conversation_id)
            .select_related("user")
            .order_by("joined_at")
        )
        return Response([
            {
                "id": str(r.user.id), "username": r.user.username,
                "avatar": r.user.avatar, "is_admin": r.is_admin,
                "joined_at": r.joined_at.isoformat() if r.joined_at else None,
            }
            for r in rows
        ])

    def post(self, request, conversation_id):
        is_admin = ConversationParticipant.objects.filter(
            conversation_id=conversation_id, user=request.user, is_admin=True
        ).exists()
        if not is_admin:
            return Response({"detail": "Only group admins can add members"}, status=403)

        user_ids = request.data.get("user_ids", [])
        if not user_ids:
            return Response({"detail": "Provide at least one user_id"}, status=400)

        existing_ids = set(
            ConversationParticipant.objects.filter(conversation_id=conversation_id)
            .values_list("user_id", flat=True)
        )
        new_ids = [uid for uid in user_ids if str(uid) not in {str(e) for e in existing_ids}]
        if not new_ids:
            return Response({"detail": "All specified users are already members"}, status=400)

        new_users = {str(u.id): u for u in User.objects.filter(id__in=new_ids)}
        missing = [uid for uid in new_ids if str(uid) not in new_users]
        if missing:
            return Response({"detail": f"User(s) not found: {missing}"}, status=404)

        existing_users = {str(u.id): u for u in User.objects.filter(id__in=existing_ids)}
        for new_uid in new_ids:
            for existing_uid in existing_ids:
                if is_user_blocked(blocker_id=new_uid, target_id=existing_uid) or is_user_blocked(blocker_id=existing_uid, target_id=new_uid):
                    return Response({
                        "detail": f"Cannot add {new_users[str(new_uid)].username}: a block exists with "
                                  f"{existing_users[str(existing_uid)].username}"
                    }, status=403)

        now = timezone.now()
        for uid in new_ids:
            ConversationParticipant.objects.create(
                conversation_id=conversation_id, user_id=uid, is_admin=False, joined_at=now,
            )

        added_usernames = [new_users[str(uid)].username for uid in new_ids]
        _broadcast(conversation_id, "group_member_added", {
            "conversation_id": str(conversation_id),
            "added_user_ids": [str(uid) for uid in new_ids],
            "added_usernames": added_usernames,
            "added_by": str(request.user.id),
        })
        for uid in new_ids:
            _notify_user(uid, "new_conversation", {
                "conversation_id": str(conversation_id), "is_group": True, "added_by": str(request.user.id),
            })

        return Response({
            "success": True,
            "added": [{"id": str(u.id), "username": u.username} for u in new_users.values()],
        })


class GroupMemberDetailView(APIView):
    """DELETE /conversations/groups/<conversation_id>/members/<target_user_id>/ — admin removes someone"""

    def delete(self, request, conversation_id, target_user_id):
        return _remove_member(request, conversation_id, target_user_id, allow_self_leave=False)


class GroupLeaveView(APIView):
    """DELETE /conversations/groups/<conversation_id>/leave/ — anyone leaves"""

    def delete(self, request, conversation_id):
        return _remove_member(request, conversation_id, request.user.id, allow_self_leave=True)


def _remove_member(request, conversation_id, target_user_id, allow_self_leave):
    is_admin = ConversationParticipant.objects.filter(
        conversation_id=conversation_id, user=request.user, is_admin=True
    ).exists()
    is_self = str(request.user.id) == str(target_user_id)

    if not is_admin and not (allow_self_leave and is_self):
        return Response({"detail": "Only group admins can remove members"}, status=403)

    target = ConversationParticipant.objects.filter(
        conversation_id=conversation_id, user_id=target_user_id
    ).first()
    if not target:
        return Response({"detail": "User is not a member of this group"}, status=404)

    target.delete()

    if is_admin and is_self:
        still_has_admin = ConversationParticipant.objects.filter(
            conversation_id=conversation_id, is_admin=True
        ).exists()
        if not still_has_admin:
            next_member = ConversationParticipant.objects.filter(
                conversation_id=conversation_id
            ).order_by("joined_at").first()
            if next_member:
                next_member.is_admin = True
                next_member.save(update_fields=["is_admin"])

    _broadcast(conversation_id, "group_member_removed", {
        "conversation_id": str(conversation_id),
        "removed_user_id": str(target_user_id),
        "removed_by": str(request.user.id),
    })
    return Response({"success": True})


class GroupSettingsView(APIView):
    """PATCH /conversations/groups/<conversation_id>/ — rename/change avatar, admin only"""

    def patch(self, request, conversation_id):
        is_admin = ConversationParticipant.objects.filter(
            conversation_id=conversation_id, user=request.user, is_admin=True
        ).exists()
        if not is_admin:
            return Response({"detail": "Only group admins can update group settings"}, status=403)

        conversation = get_object_or_404(Conversation, id=conversation_id, is_group=True)

        group_name = request.data.get("group_name")
        group_avatar = request.data.get("group_avatar")
        if group_name is None and group_avatar is None:
            return Response({"detail": "Provide at least group_name or group_avatar"}, status=400)

        if group_name is not None:
            conversation.group_name = group_name.strip()
        if group_avatar is not None:
            conversation.group_avatar = group_avatar
        conversation.save()

        _broadcast(conversation_id, "group_updated", {
            "conversation_id": str(conversation_id),
            "group_name": conversation.group_name,
            "group_avatar": str(conversation.group_avatar) if conversation.group_avatar else None,
            "updated_by": str(request.user.id),
        })
        return Response(ConversationSerializer(conversation, context={"request": request}).data)


def _notify_user(user_id, event_type, data):
    """Personal channel push — same role as user_channel() in your Redis code."""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{user_id}",
        {"type": "chat.message", "data": {"type": event_type, "data": data}},
    )
def _broadcast(conversation_id, event_type, data):
    """Small shared helper — every feature from here on reuses this instead of repeating group_send boilerplate."""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"conversation_{conversation_id}",
        {"type": "chat.message", "data": {"type": event_type, "data": data}},
    )
class UnreadCountView(APIView):
    """GET /conversations/unreadCount/"""

    def get(self, request):
        conversations = Conversation.objects.filter(participants=request.user)
        total_unread = 0
        if not request.user.is_authenticated:
            return Response({"total_unread": 0})
        for conv in conversations:
            if conv.is_group:
                total_unread += (
                    Message.objects.filter(conversation=conv, is_deleted=False)
                    .exclude(sender=request.user)
                    .exclude(id__in=MessageRead.objects.filter(user=request.user).values("message_id"))
                    .count()
                )
            else:
                total_unread += Message.objects.filter(
                    conversation=conv, is_read=False, is_deleted=False,
                ).exclude(sender=request.user).count()

        return Response({"total_unread": total_unread})


class UserSearchView(APIView):
    """GET /users/search/?q=...&limit=..."""

    def get(self, request):
        q = request.query_params.get("q", "").strip()
        limit = min(int(request.query_params.get("limit", 20)), 50)
        if not q:
            return Response([])

        starts_with = list(
            User.objects.filter(username__istartswith=q).exclude(id=request.user.id)
            .order_by("username")[:limit]
        )
        remaining = limit - len(starts_with)
        contains = []
        if remaining > 0:
            already = {u.id for u in starts_with}
            contains = list(
                User.objects.filter(username__icontains=q)
                .exclude(username__istartswith=q)
                .exclude(id=request.user.id)
                .exclude(id__in=already)
                .order_by("username")[:remaining]
            )

        all_users = starts_with + contains

        candidate_ids = [u.id for u in all_users]
        block_rows = ProfileBlock.objects.filter(
            Q(blocker_id=request.user.id, target_id__in=candidate_ids) |
            Q(target_id=request.user.id, blocker_id__in=candidate_ids),
            is_invalidated=False,
        ).values_list("blocker_id", "target_id")

        blocked_ids = set()
        for blocker_id, target_id in block_rows:
            blocked_ids.add(blocker_id)
            blocked_ids.add(target_id)
        blocked_ids.discard(request.user.id)

        all_users = [u for u in all_users if u.id not in blocked_ids]

        return Response([
            {"id": str(u.id), "username": u.username, "avatar": u.avatar if u.avatar else None}
            for u in all_users
        ])
from feed.models import MessageReaction


def get_reaction_summary(message_id, current_user_id):
    reactions = (
        MessageReaction.objects
        .filter(message_id=message_id)
        .select_related("user")
        .order_by("created_at")
    )

    grouped = {}
    for reaction in reactions:
        entry = grouped.setdefault(reaction.emoji, {
            "emoji": reaction.emoji,
            "count": 0,
            "reacted_by_me": False,
            "reactors": [],
        })
        entry["count"] += 1
        entry["reactors"].append(reaction.user.username)
        if str(reaction.user_id) == str(current_user_id):
            entry["reacted_by_me"] = True

    for entry in grouped.values():
        entry["reactors"] = entry["reactors"][:3]

    return sorted(grouped.values(), key=lambda x: x["count"], reverse=True)
def _absolute_url(request, file_field):
    """Django's version of your _make_absolute_url — file_field is an ImageField/FileField instance."""
    if not file_field:
        return None
    try:
        return request.build_absolute_uri(file_field.url)
    except ValueError:
        return None


def _build_message_response(message, request, is_target_blocked, readers, reactions=None):
    media_url = None
    if message.image_url and not message.is_deleted:
        media_url = _absolute_url(request, message.image_url)
    if message.video_url and not message.is_deleted:
        media_url = _absolute_url(request, message.video_url)

    sender_avatar = _absolute_url(request, message.sender.avatar) if message.sender else None

    replied_to = None
    if message.reply_to:
        original = message.reply_to
        reply_media_url = None
        if original.image_url and not original.is_deleted:
            reply_media_url = _absolute_url(request, original.image_url)
        if original.video_url and not original.is_deleted:
            reply_media_url = _absolute_url(request, original.video_url)
        replied_to = {
            "id": str(original.id),
            "sender_id": str(original.sender_id),
            "sender_username": original.sender.username if original.sender else "",
            "message_type": original.message_type,
            "body": None if original.is_deleted else original.body,
            "media_url": reply_media_url,
            "is_deleted": original.is_deleted,
        }

    return {
        "id": str(message.id),
        "conversation_id": str(message.conversation_id),
        "sender_id": str(message.sender_id),
        "sender_username": message.sender.username if message.sender else "",
        "sender_avatar": sender_avatar,
        "message_type": message.message_type,
        "body": None if message.is_deleted else message.body,
        "media_url": media_url,
        "offer_data": None if message.is_deleted else message.offer_data,
        "is_read": message.is_read,
        "read_at": message.read_at.isoformat() if message.read_at else None,
        "is_deleted": message.is_deleted,
        "created_at": message.created_at.isoformat(),
        "is_target_blocked": is_target_blocked,
        "readers": readers,
        "reply_to_id": str(message.reply_to_id) if message.reply_to_id else None,
        "replied_to": replied_to,
        "reactions": reactions or [],
    }

def is_user_blocked(blocker_id, target_id):
    return ProfileBlock.objects.filter(
        blocker_id=blocker_id, target_id=target_id, is_invalidated=False,
    ).exists()


def check_messaging_permission(sender, recipient):
    try:
        privacy = ProfilePrivacy.objects.get(user_id=recipient.id)
    except ProfilePrivacy.DoesNotExist:
        return {"allowed": True, "reason": None}

    who = privacy.who_can_message

    if who == "everyone":
        return {"allowed": True, "reason": None}

    if who == "nobody":
        return {"allowed": False, "reason": "This user is not accepting messages"}

    if who == "followers":
        is_following = Follow.objects.filter(follower_id=sender.id, following_id=recipient.id).exists()
        return {
            "allowed": is_following,
            "reason": None if is_following else "This profile only accepts messages from its followers",
        }

    return {"allowed": True, "reason": None}