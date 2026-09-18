import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings

# initialize once at module level
_firebase_initialized = False

def _init_firebase():
    global _firebase_initialized
    if not _firebase_initialized and settings.FCM_ENABLED:
        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
        firebase_admin.initialize_app(cred)
        _firebase_initialized = True


def send_push_notification(
    fcm_token: str,
    title: str,
    body: str,
    data: dict | None = None
) -> dict:
    """
    Sends a push notification to a single device
    Returns {"success": bool, "error": str | None}
    """
    if not settings.FCM_ENABLED:
        return {"success": True, "error": None}

    _init_firebase()

    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data={k: str(v) for k, v in (data or {}).items()},  # FCM requires string values
            token=fcm_token,
        )
        messaging.send(message)
        return {"success": True, "error": None}

    except messaging.UnregisteredError:
        # token is invalid — remove it from user
        return {"success": False, "error": "unregistered_token"}

    except Exception as e:
        return {"success": False, "error": str(e)}


def send_push_to_multiple(
    fcm_tokens: list[str],
    title: str,
    body: str,
    data: dict | None = None
) -> None:
    """Sends to multiple devices — for staff broadcasts etc"""
    if not fcm_tokens:
        return

    if not settings.FCM_ENABLED:
        print(f"[PUSH - DEV] Multicast to {len(fcm_tokens)} devices | {title}")
        return

    _init_firebase()

    message = messaging.MulticastMessage(
        notification=messaging.Notification(title=title, body=body),
        data={k: str(v) for k, v in (data or {}).items()},
        tokens=fcm_tokens,
    )
    messaging.send_each_for_multicast(message)