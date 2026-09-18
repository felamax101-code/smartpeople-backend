from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from .tasks import activate_user_posts
from django.db.models.signals import post_save
from .models import TwoFactorSettings,CustomUser,VerificationRequest
from authentication.notification_service import notify
from Profile.models import ProfilePrivacy


@receiver(user_logged_in)
def on_user_login(sender,request,user,**kwargs):
    activate_user_posts(str(user.id))
    
    
@receiver(post_save, sender=CustomUser)
def create_two_factor_settings(sender, instance, created, **kwargs):
    if created:
        TwoFactorSettings.objects.create(user=instance)

        
        
@receiver(post_save,sender=VerificationRequest)
def notify_seller_on_verification_status_change(sender,instance,created,**kwargs):
    if created:
        return
    
    if instance.identity_status=="approved":
        notify(
        recipient=instance.user,
        notification_type="verification",
        title="Your Verification request  was approved",
        body=f"{instance.id_type} was approved. Verification level:{instance.user.verification_level}. Verify your business to unlock level {instance.user.verification_level+1}",
        send_push=True,
    )
    elif instance.identity_status=="pending":
        notify(
        recipient=instance.user,
        notification_type="verification",
        title="Your Verification request  was approved",
        body=f"{instance.id_type} is under review.You will be notified once approved or rejected",
        send_push=True,
    )
    elif instance.identity_status=="rejected":
        notify(
        recipient=instance.user,
        notification_type="verification",
        title="Your Verification request  was rejected",
        body=f"{instance.id_type} was rejected due to {instance.business_rejection_reason}  Verification level:{instance.user.verification_level}. Resubmit  to unlock level {instance.user.verification_level+1}",
        send_push=True,
    )
        
    elif instance.identity_status=="exhausted":
        notify(
        recipient=instance.user,
        notification_type="verification",
        title=f"Your Verification request  is Exhausted",
        body=f"{instance.id_type} is exhausted. Verification level:{instance.user.verification_level}. Resubmit  to unlock level {instance.user.verification_level+1}",
        
        send_push=True,
    )
    elif instance.identity_status=="expired":
        notify(
        recipient=instance.user,
        notification_type="verification",
        title=f"Your Verification request  is expired",
        body=f"{instance.id_type} is expired. Verification level:{instance.user.verification_level}. Resubmit  to unlock level {instance.user.verification_level+1}",
        
        send_push=True,
    )
    