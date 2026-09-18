from django.db import models
from django.contrib.auth import get_user_model
User=get_user_model()
from authentication.models import CustomUser

class ProfilePrivacy(models.Model):
    WHO_CHOICES = (
        ("everyone", "Everyone"),
        ("followers", "Followers"),
        ("nobody", "Nobody"),
    )
    

    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="privacy")
    show_phone = models.BooleanField(default=False)
    show_email = models.BooleanField(default=False)
    show_location = models.BooleanField(default=True)
    show_followers = models.BooleanField(default=True)
    show_following = models.BooleanField(default=True)
    who_can_message = models.CharField(choices=WHO_CHOICES, default="everyone", max_length=20)
    who_can_follow = models.CharField(choices=WHO_CHOICES, default="everyone", max_length=20)
    show_online_status = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "Profile Privacy"

    def __str__(self):
        return f"{self.user.username}'s privacy settings"