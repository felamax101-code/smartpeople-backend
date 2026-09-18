
from .models import Notification, CustomUser
from .push_service import send_push_notification

def notify(
    recipient: CustomUser,
    notification_type: str,
    title: str,
    body: str,
    data: dict | None = None,
    send_push: bool = True,
    send_email: bool = False,
    email_task=None,  # optional celery task
) -> Notification:
    """
    Central notification dispatcher
    Always creates in-app notification
    Optionally sends push and/or email
    """
    # 1. in-app notification — always
    notification = Notification.objects.create(
        recipient=recipient,
        notification_type=notification_type,
        title=title,
        body=body,
        data=data or {}
    )

    # 2. push notification — if user has FCM token
    if send_push and recipient.fcm_token:
        result = send_push_notification(
            fcm_token=recipient.fcm_token,
            title=title,
            body=body,
            data=data
        )
        # token invalid? clear it
        if result.get("error") == "unregistered_token":
            recipient.fcm_token = None
            recipient.save()

    # 3. email — if explicitly requested
    if send_email and email_task:
        email_task.delay(recipient.email, recipient.username, title, body)

    return notification


def mark_as_read(user: CustomUser, notification_id: str) -> dict:
    try:
        notification = Notification.objects.get(
            id=notification_id,
            recipient=user
        )
        notification.is_read = True
        notification.save()
        return {"success": True}
    except Notification.DoesNotExist:
        return {"success": False, "error": "Notification not found"}


def mark_all_as_read(user: CustomUser) -> None:
    Notification.objects.filter(
        recipient=user,
        is_read=False
    ).update(is_read=True)


def get_unread_count(user: CustomUser) -> int:
    return Notification.objects.filter(
        recipient=user,
        is_read=False
    ).count()