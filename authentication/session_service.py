from django.utils import timezone
from .models import UserSession, CustomUser
from .utils import get_ip_address, parse_user_agent, get_location_from_ip

def create_session(user: CustomUser, request, jti: str) -> UserSession:
    """Called right after login — creates a session record"""
    ip = get_ip_address(request)
    ua = parse_user_agent(request)
    location = get_location_from_ip(ip)

    session = UserSession.objects.create(
        user=user,
        jti=jti,
        device=ua["device"],
        os=ua["os"],
        browser=ua["browser"],
        ip_address=ip,
        location=location,
    )
    return session


def refresh_session(jti: str) -> None:
    """
    Called on every authenticated request
    Updates last_active — auto_now=True handles the timestamp
    We use update() to avoid triggering signals unnecessarily
    """
    UserSession.objects.filter(jti=jti).update(
        last_active=timezone.now()
    )


def terminate_session(jti: str) -> None:
    """Called on logout — deletes the session"""
    UserSession.objects.filter(jti=jti).delete()


def terminate_all_sessions(user: CustomUser) -> None:
    """Called on logout-all — wipes every session for the user"""
    UserSession.objects.filter(user=user).delete()


def terminate_other_sessions(user: CustomUser, current_jti: str) -> None:
    """Logs out all devices except the current one"""
    UserSession.objects.filter(user=user).exclude(jti=current_jti).delete()


def is_valid_session(jti: str) -> bool:
    """
    Middleware uses this to validate every request
    If session was deleted (logout, suspicious activity) → token rejected
    """
    return UserSession.objects.filter(jti=jti).exists()