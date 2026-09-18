from django.db.models.signals import post_save
from .models import  ProfilePrivacy
from django.dispatch import receiver
from authentication.models import CustomUser

@receiver(post_save, sender=CustomUser)
def create_user_privacy(sender, instance, created, **kwargs):
    if created:
        ProfilePrivacy.objects.create(user=instance)