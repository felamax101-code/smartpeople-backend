from rest_framework import serializers
from django.contrib.auth import get_user_model
from feed.models import Conversation, Message
import magic
User = get_user_model()


class ParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "avatar"]


class MessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source="sender.username", read_only=True)

    class Meta:
        model = Message
        fields = [
            "id", "conversation", "sender", "sender_username",
            "message_type", "body", "image_url", "video_url",
            "offer_data", "is_read", "read_at", "is_deleted",
            "created_at", "reply_to",
        ]
        read_only_fields = ["id", "sender", "is_read", "read_at", "is_deleted", "created_at"]


class ConversationSerializer(serializers.ModelSerializer):
    participants = ParticipantSerializer(many=True, read_only=True)
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id", "is_group", "group_name", "group_avatar", "created_by",
            "post", "participants", "last_message_preview", "last_message_at",
            "unread_count", "created_at",
        ]

    def get_unread_count(self, obj):
        request = self.context.get("request")
        if not request:
            return 0
        return Message.objects.filter(
            conversation=obj, is_read=False
        ).exclude(sender=request.user).count()


class ConversationCreateSerializer(serializers.Serializer):
    """Equivalent of your Pydantic ConversationCreate schema."""
    recipient_id = serializers.UUIDField()
    post_id = serializers.UUIDField(required=False, allow_null=True)
    initial_message = serializers.CharField()

    def validate_initial_message(self, value):
        if not value.strip():
            raise serializers.ValidationError("Initial message cannot be empty")
        return value.strip()


class MessageCreateSerializer(serializers.Serializer):
    body = serializers.CharField(required=False, allow_null=True)
    message_type = serializers.ChoiceField(
        choices=["text", "image", "video", "offer"], default="text"
    )
    reply_to = serializers.UUIDField(required=False, allow_null=True)
    image_url = serializers.ImageField(required=False, allow_null=True)
    video_url = serializers.FileField(required=False, allow_null=True)
    
    

    def validate_video_url(self,value):
        mime = magic.from_buffer(value.read(2048), mime=True)
        value.seek(0)  # reset pointer after reading
        if not mime.startswith("video/"):
            raise serializers.ValidationError(f"Expected a video file, got {mime}")
        return value