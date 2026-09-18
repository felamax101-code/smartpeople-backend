from background_task import background
#from celery import shared_task
from feed.models import Post
from django.core.mail import send_mail
from django.conf import settings

#@shared_task
def activate_user_posts(user_id):
    Post.objects.filter(owner_id=user_id,is_active=False).update(is_active=True)
    



#@shared_task
def send_suspicious_login_email(email, username, ip, location, browser, os):
    send_mail(
        subject="⚠️ New login to your account",
        message=f"""
Hi {username},

We detected a new login to your account from an unrecognized location.

IP Address: {ip}
Location: {location}
Browser: {browser}
OS: {os}

If this was you, ignore this email.
If this wasn't you, secure your account immediately by changing your password.
        """,
        from_email="security@yourapp.com",
        recipient_list=[email]
    )
    
    
    
#@shared_task
def send_phone_otp_sms(phone, otp):
    """
    Swap the internals for Twilio, Termii, or any SMS provider
    
    """
    import requests
    
    payload = {
        "to": phone,
        "from": "YourApp",
        "sms": f"Your verification code is {otp}. Valid for 10 minutes. Do not share this.",
        "type": "plain",
        "api_key": settings.TERMII_API_KEY,
        "channel": "generic"
    }
    
    requests.post("https://api.ng.termii.com/api/sms/send", json=payload)
    
    
    

#@shared_task
def notify_staff_new_verification(username: str, section: str) -> None:
    send_mail(
        subject=f"New {section} verification submitted",
        message=f"{username} submitted a {section} verification request. Review it in the admin panel.",
        from_email="noreply@yourapp.com",
        recipient_list=["staff@yourapp.com"]
    )

#@shared_task
def notify_user_verification_result(
    email: str,
    username: str,
    section: str,
    action: str,
    reason: str | None
) -> None:
    if action == "approve":
        subject = f"Your {section} verification was approved"
        message = f"Hi {username}, your {section} verification has been approved. Your trust badge has been updated."
    else:
        subject = f"Your {section} verification was rejected"
        message = f"Hi {username}, your {section} verification was rejected.\n\nReason: {reason}\n\nYou may resubmit with a valid document."

    send_mail(
        subject=subject,
        message=message,
        from_email="noreply@yourapp.com",
        recipient_list=[email]
    )

#mark approved verifications as  expired verifications nightly
#@shared_task
def check_expired_verifications() -> None:
    """
    Runs nightly via Celery Beat
    Marks approved verifications as expired if document date has passed
    """
    from .models import VerificationRequest
    from django.utils import timezone

    today = timezone.now().date()

    expired = VerificationRequest.objects.filter(
        identity_status="approved",
        document_expiry_date__lt=today,
        document_expiry_date__isnull=False
    )

    for vr in expired:
        vr.identity_status = "expired"
        vr.identity_attempt_count = 0  # reset — new document, fresh start
        vr.save()
        notify_user_verification_result.delay(
            vr.user.email,
            vr.user.username,
            "identity",
            "reject",
            "Your verification document has expired. Please resubmit with a valid document."
        )
        
        
#cleanup stale sessions that were not properly terminated (e.g. user deleted account without logging out, or "remember me" sessions)
#@shared_task
def cleanup_stale_sessions() -> None:
    from .models import UserSession
    from django.utils import timezone
    from datetime import timedelta

    cutoff = timezone.now() - timedelta(days=30)
    deleted_count, _ = UserSession.objects.filter(
        last_active__lt=cutoff
    ).delete()
        







#@shared_task
def send_2fa_otp_email(email: str, username: str, code: str) -> None:
    send_mail(
        subject="Your login verification code",
        message=f"""
Hi {username},

Your verification code is: {code}

Valid for 10 minutes. Do not share this code with anyone.

If you didn't request this, secure your account immediately.
        """,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email]
    )


#@shared_task
def send_2fa_otp_sms(phone: str, code: str) -> None:
    import requests
    payload = {
        "to": phone,
        "from": "YourApp",
        "sms": f"Your login code is {code}. Valid for 10 minutes. Do not share.",
        "type": "plain",
        "api_key": settings.TERMII_API_KEY,
        "channel": "generic"
    }
    requests.post("https://api.ng.termii.com/api/sms/send", json=payload)


#@shared_task
def cleanup_expired_trusted_devices() -> None:
    from .models import TrustedDevice
    deleted, _ = TrustedDevice.objects.filter(
        expires_at__lt=timezone.now()
    ).delete()
    
    
    
       
        
#@shared_task
def notify_staff_flagged_account(username: str, report_count: int) -> None:
    send_mail(
        subject=f"âš ï¸ Flagged Account: {username}",
        message=f"{username} has received {report_count} reports and requires review.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=["staff@yourapp.com"]
    )



#@shared_task
def cleanup_old_notifications() -> None:
    from django.utils import timezone
    from datetime import timedelta

    cutoff = timezone.now() - timedelta(days=90)
    deleted, _ = Notification.objects.filter(
        created_at__lt=cutoff,
        is_read=True   # only delete read notifications
    ).delete()
    
