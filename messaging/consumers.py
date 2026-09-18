import json
from urllib.parse import parse_qs
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from jose import jwt, JWTError
from django.conf import settings
from authentication.models import CustomUser  # adjust import to wherever your user model lives
from .presence import set_online, set_offline, refresh_presence, set_typing, clear_typing, HEARTBEAT_INTERVAL

class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.user_id = self.scope["url_route"]["kwargs"]["user_id"]

        token = self._get_token()
        if not token:
            await self._reject("Unauthorized", 4001)
            return

        user = await self._get_user_from_token(token)
        if not user:
            await self._reject("Unauthorized", 4001)
            return

        if str(user.id) != self.user_id:
            await self._reject("Forbidden", 4003)
            return

        self.user = user
        self.conversation_ids = await self._get_conversation_ids(user)

        # ── join groups — replaces your manual subscribe() call ──
        self.group_names = [f"user_{self.user_id}"] + [
            f"conversation_{cid}" for cid in self.conversation_ids
        ]
        for group_name in self.group_names:
            await self.channel_layer.group_add(group_name, self.channel_name)
        await database_sync_to_async(set_online)(self.user_id)

        # notify other participants this user is online, same as your original loop
        for cid in self.conversation_ids:
            await self.channel_layer.group_send(
                f"conversation_{cid}",
                {"type": "presence.event", "data": {"type": "online", "data": {"user_id": self.user_id}}}
            )
        await self.accept()
        await self.send(text_data=json.dumps({
            "type": "connected",
            "data": {
                "user_id": self.user_id,
                "message": "Connected successfully",
                "heartbeat_interval": HEARTBEAT_INTERVAL,
            }
        }))

    async def disconnect(self, close_code):
        for group_name in getattr(self, "group_names", []):
            await self.channel_layer.group_discard(group_name, self.channel_name)

        await database_sync_to_async(set_offline)(self.user_id)
        for cid in getattr(self, "conversation_ids", []):
            await self.channel_layer.group_send(
                f"conversation_{cid}",
                {"type": "presence.event", "data": {"type": "offline", "data": {"user_id": self.user_id}}}
            )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({"type": "error", "data": {"message": "Invalid JSON"}}))
            return

        event_type = data.get("type")

        if event_type == "ping":
            await database_sync_to_async(refresh_presence)(self.user_id)
            await self.send(text_data=json.dumps({"type": "pong"}))

        elif event_type == "typing":
            conversation_id = data.get("data", {}).get("conversation_id")
            is_typing = data.get("data", {}).get("is_typing", True)
            if conversation_id:
                fn = set_typing if is_typing else clear_typing
                await database_sync_to_async(fn)(conversation_id, self.user_id)

                await self.channel_layer.group_send(
                    f"conversation_{conversation_id}",
                    {
                        "type": "typing.event",
                        "data": {
                            "type": "typing",
                            "data": {
                                "conversation_id": conversation_id,
                                "user_id": self.user_id,
                                "is_typing": is_typing,
                            },
                        },
                        "sender_channel": self.channel_name,
                    }
                )
                
    async def presence_event(self, event):
        await self.send(text_data=json.dumps(event["data"]))
    # ── handler — called when something else sends to a group this consumer is in ──
    async def chat_message(self, event):
        """
        Channels routes group_send() calls to a method named after the event's "type",
        with underscores instead of dots — event {"type": "chat.message"} calls this method.
        """
        await self.send(text_data=json.dumps(event["data"]))
    async def typing_event(self, event):
        # skip echoing your own typing event back to yourself, same filter your redis_task() did
        if event.get("sender_channel") == self.channel_name:
            return
        await self.send(text_data=json.dumps(event["data"]))
    async def _reject(self, message, code):
        await self.accept()
        await self.send(text_data=json.dumps({"type": "error", "data": {"message": message}}))
        await self.close(code=code)

    def _get_token(self):
        query_string = self.scope["query_string"].decode()
        params = parse_qs(query_string)
        token = params.get("token", [None])[0]
        if not token:
            cookies = self.scope.get("cookies", {})
            token = cookies.get("access_token")
        return token

    @database_sync_to_async
    def _get_user_from_token(self, token):
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        except JWTError:
            return None
        user_id = payload.get("user_id")
        if not user_id:
            return None
        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return None
        if not user.is_active or user.is_locked:
            return None
        return user

    @database_sync_to_async
    def _get_conversation_ids(self, user):
        from feed.models import ConversationParticipant  # adjust import path

        return list(
            ConversationParticipant.objects
            .filter(user=user)
            .values_list("conversation_id", flat=True)
        )