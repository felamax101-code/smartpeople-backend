   
from django.utils import timezone
from datetime import timedelta
from .models import TwoFactorSettings, TrustedDevice, CustomUser
from .utils import (
    generate_totp_secret, get_totp_uri, generate_qr_code,
    generate_backup_codes, verify_backup_code,
    generate_2fa_otp, create_2fa_challenge, verify_2fa_challenge,
    generate_device_fingerprint, get_ip_address,
    get_location_from_ip, parse_user_agent,
    encrypt_id_number, decrypt_id_number,  # reuse for totp secret encryption
    generate_temp_token, consume_temp_token,
    verify_totp_code,send_2fa_otp_sms,send_2fa_otp_email,verify_temp_token
)

TRUSTED_DEVICE_DAYS = 30


# ── setup ──────────────────────────────────────────────────────

def initiate_setup(user: CustomUser, method: str) -> dict:
    """Step 1 of setup — prepares 2FA for the chosen method"""

    if method == "sms" and not user.phone_verified:
        return {
            "success": False,
            "error": "Phone must be verified before enabling SMS 2FA"
        }

    if method == "email" and not user.is_email_verified:
        return {
            "success": False,
            "error": "Email must be verified before enabling Email 2FA"
        }

    tf = user.two_factor

    if method == "totp":
        # generate secret — user must confirm before we save is_enabled
        secret = generate_totp_secret()
        encrypted_secret = encrypt_id_number(secret)  # reuse encryption util
        
        tf.totp_secret = encrypted_secret
        tf.method = method
        tf.save()

        uri = get_totp_uri(secret, user.username)
        qr_code = generate_qr_code(uri)

        return {
            "success": True,
            "method": method,
            "qr_code": qr_code,        # base64 PNG — display in frontend
            "manual_key": secret,       # for users who can't scan QR
            "message": "Scan QR code then confirm with a code from your app"
        }

    # email or sms — no extra setup step needed
    tf.method = method
    tf.save()
    return {
        "success": True,
        "method": method,
        "message": f"Send a confirmation code to complete setup"
    }


def confirm_setup(user: CustomUser, code: str) -> dict:
    """
    Step 2 of setup — verifies the method works before enabling
    For TOTP: verifies first app code
    For email/SMS: verifies OTP that was sent
    """
    tf = user.two_factor

    if tf.method == "totp":
        secret = decrypt_id_number(tf.totp_secret)
        if not verify_totp_code(secret, code):
            return {"success": False, "error": "Invalid code. Check your authenticator app."}

    else:
        # email/sms — verify against challenge
        result = verify_2fa_challenge(str(user.id), code)
        if not result["success"]:
            return result

    # confirmed — fully enable 2FA and generate backup codes
    plain_codes, hashed_codes = generate_backup_codes()
    tf.is_enabled = True
    
    tf.backup_codes = hashed_codes
    tf.backup_codes_viewed = False
    tf.save()

    return {
        "success": True,
        "message": "2FA enabled successfully",
        "backup_codes": plain_codes,  # shown ONCE — user must save these
        "warning": "Save these codes somewhere safe. They won't be shown again."
    }


def disable_2fa(user: CustomUser, code: str) -> dict:
    """Requires current 2FA code to disable — prevents attacker from disabling"""
    result = _verify_code(user, code)
    if not result["success"]:
        return result

    tf = user.two_factor
    tf.is_enabled = False
    tf.method = "email"
    tf.totp_secret = None
    tf.backup_codes = []
    tf.backup_codes_viewed = False
    tf.save()

    # clear all trusted devices
    user.trusted_devices.all().delete()

    return {"success": True, "message": "2FA disabled"}


# ── login flow ──────────────────────────────────────────────────

def check_trusted_device(user: CustomUser, request) -> bool:
    """Returns True if device is trusted and not expired"""
    fingerprint = generate_device_fingerprint(request)
    device = TrustedDevice.objects.filter(
        user=user,
        device_fingerprint=fingerprint
    ).first()

    if not device:
        return False

    if device.is_expired:
        device.delete()
        return False

    return True


def initiate_login_challenge(user: CustomUser, request) -> dict:
    """
    Called after password verified — starts 2FA challenge
    Returns temp_token for the /verify/ endpoint
    """
    tf = user.two_factor
    temp_token = generate_temp_token(str(user.id))

    if tf.method == "totp":
        # no code to send — user reads from app
        return {
            "success": True,
            "temp_token": temp_token,
            "method": "totp",
            "message": "Enter the code from your authenticator app"
        }

    elif tf.method == "email":
        code = generate_2fa_otp()
        create_2fa_challenge(str(user.id), code, "email")
        send_2fa_otp_email(user.email, user.username, code)

    elif tf.method == "sms":
        code = generate_2fa_otp()
        create_2fa_challenge(str(user.id), code, "sms")
        send_2fa_otp_sms(user.phone, code)

    return {
        "success": True,
        "temp_token": temp_token,
        "method": tf.method,
        "message": f"Code sent to your {'email' if tf.method == 'email' else 'phone'}"
    }


def verify_login_challenge(
    temp_token: str,
    code: str,
    request,
    trust_device: bool = False
) -> dict:
    """
    Verifies 2FA code during login
    Returns user_id on success so view can create session
    """
    from .models import CustomUser

    # validate temp token
    user_id = consume_temp_token(temp_token)
    if not user_id:
        return {"success": False, "error": "Session expired. Please log in again. okayyy"}

    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return {"success": False, "error": "User not found"}

    # check if it's a backup code first
    tf = user.two_factor
    backup_index = verify_backup_code(code, tf.backup_codes)
    if backup_index is not None:
        # consume the backup code — remove it from list
        tf.backup_codes.pop(backup_index)
        tf.save()
        return {
            "success": True,
            "user": user,
            "used_backup_code": True,
            "backup_codes_remaining": len(tf.backup_codes)
        }

    # verify actual 2FA code
    result = _verify_code(user, code)
    if not result["success"]:
        return result

    # optionally trust this device
    if trust_device:
        _trust_device(user, request)

    return {"success": True, "user": user, "used_backup_code": False}


def resend_challenge(temp_token: str) -> dict:
    """Resend OTP for email/SMS methods"""
    from .models import CustomUser

    user_id = verify_temp_token(temp_token)  # don't consume — still need it
    if not user_id:
        return {"success": False, "error": "Session expired. Please log in again."}

    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return {"success": False, "error": "User not found"}

    tf = user.two_factor
    if tf.method == "totp":
        return {"success": False, "error": "Authenticator app codes cannot be resent"}

    code = generate_2fa_otp()
    create_2fa_challenge(str(user.id), code, tf.method)

    if tf.method == "email":
        send_2fa_otp_email(user.email, user.username, code)
    else:
        send_2fa_otp_sms.delay(user.phone, code)

    return {"success": True, "message": "Code resent"}


# ── backup codes ───────────────────────────────────────────────

def view_backup_codes(user: CustomUser, code: str) -> dict:
    """
    User must verify 2FA to view backup codes
    Backup codes are hashed in DB so we can't show originals —
    we regenerate fresh ones instead
    """
    result = _verify_code(user, code)
    if not result["success"]:
        return result

    plain_codes, hashed_codes = generate_backup_codes()
    tf = user.two_factor
    tf.backup_codes = hashed_codes
    tf.backup_codes_viewed = True
    tf.save()

    return {
        "success": True,
        "backup_codes": plain_codes,
        "warning": "These codes replace your previous ones. Save them now."
    }


# ── internal helpers ───────────────────────────────────────────

def _verify_code(user: CustomUser, code: str) -> dict:
    """Unified code verification regardless of method"""
    tf = user.two_factor

    if tf.method == "totp":
        secret = decrypt_id_number(tf.totp_secret)
        if not verify_totp_code(secret, code):
            return {"success": False, "error": "Invalid authenticator code"}
        return {"success": True, "error": None}

    else:
        return verify_2fa_challenge(str(user.id), code)


def _trust_device(user: CustomUser, request) -> TrustedDevice:
    fingerprint = generate_device_fingerprint(request)
    ua = parse_user_agent(request)
    ip = get_ip_address(request)
    location = get_location_from_ip(ip)

    device, _ = TrustedDevice.objects.update_or_create(
        user=user,
        device_fingerprint=fingerprint,
        defaults={
            "device_label": f"{ua['browser']} on {ua['os']}",
            "ip_address": ip,
            "location": location,
            "expires_at": timezone.now() + timedelta(days=TRUSTED_DEVICE_DAYS)
        }
    )
    return device


# import tasks here to avoid circular imports
# from .tasks import send_2fa_otp_email, send_2fa_otp_sms
        