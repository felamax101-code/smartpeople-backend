from rest_framework import serializers
from .models import ProfilePrivacy


class ProfilePrivacySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfilePrivacy
        fields = [
            "show_phone",
            "show_email", 
            "show_location",
            "show_followers",
            "show_following",
            "who_can_message",
            "who_can_follow",
            "show_online_status",
            "updated_at"
        ]
        read_only_fields = ["updated_at"]
    def update(self,instance,validated_data):
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance