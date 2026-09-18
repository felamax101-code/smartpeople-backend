from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
#from celery import shared_task
import logging
import requests
#from twilio.rest import Client


logger = logging.getLogger(__name__)


# EMAIL SENDING (Async with Celery - optional)

#@shared_task
def send_email_async(subject, html_message, recipient_list):
   #if no celery
    try:
        send_email_sync(subject, html_message, recipient_list)
    except Exception as e:
       pass


def send_email_sync(subject, html_message, recipient_list):
    """Synchronous email sending"""
    plain_message = strip_tags(html_message)
    
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipient_list,
        html_message=html_message,
        fail_silently=False,
    )
    
# PHONE SMS SENDING (Async with Celery - optional)
    
#@shared_task
def send_sms_async(phone, code):
    """Celery worker execution wrapper"""
    send_2fa_otp_sms(phone, code)


def send_2fa_otp_sms(phone, code):
    """Synchronous core logic executing the Termii API call"""
    print(f"Sending code {code} to {phone}")
    
    # payload = {
    #     "to": phone,
    #     "from": settings.TERMII_SENDER_ID,
    #     "sms": f"Your login code is {code}. Valid for 10 minutes. Do not share.",
    #     "type": "plain",
    #     "api_key": settings.TERMII_API_KEY,
    #     "channel": settings.TERMII_CHANNEL,
    # }
    
    # # Building URL dynamically using settings
    # url = f"{settings.TERMII_BASE_URL}/api/sms/send"
    
    # response = requests.post(url, json=payload)
    # return response
    
    
    
    
def send_phone_otp_sms(phone, code):
    print(code)
    # """
    # Main entry point to send OTP via SMS. 
    # Tries Celery first; falls back to synchronous execution if the broker is down.
    # """
    # try:
    #     # 1. Attempt running it asynchronously via Celery
    #     send_sms_async.delay(phone, code)
    # except Exception:
    #     # 2. Fallback to immediate sync execution if Celery/Redis fails
    #     send_2fa_otp_sms(phone, code)
        

def send_2fa_otp_sms(phone,code):
    print(code)
    # try:
    #     # 1. Attempt running it asynchronously via Celery
    #     send_sms_async.delay(phone, code)
    # except Exception:
    #     # 2. Fallback to immediate sync execution if Celery/Redis fails
    #     send_2fa_otp_sms(phone, code)
    
    
    
def send_2fa_otp_email(email,username,otp):
    """Send 6-digit OTP for email verification"""
    subject = 'Your 2FA setup Code'
    html_message = f"""
    <!DOCTYPE html>
    <html>
    <body style="margin:0;padding:0;background:#080a0e;font-family:'Courier New',monospace">
      <div style="max-width:480px;margin:40px auto;background:#0c0f16;border:1px solid #1c2030;border-radius:12px;overflow:hidden">
        <div style="background:linear-gradient(135deg,#0d1f15,#0a1520);padding:28px;text-align:center;border-bottom:1px solid #1c2030">
          <div style="font-size:28px;margin-bottom:8px">SPH</div>
          <div style="font-family:sans-serif;font-size:20px;font-weight:900;color:#3bff9e;letter-spacing:-0.03em">SmartPyhub</div>
          <div style="font-size:11px;color:#536080;margin-top:4px">Email Verification</div>
        </div>
        <div style="padding:32px">
          <p style="font-size:13px;color:#536080;margin-bottom:20px">
            Hey {username or ''} , use the code below to verify your email address.
            It expires in <strong style="color:#ffbf47">10 minutes</strong>.
          </p>
          <div style="background:#080a0e;border:1px solid #1c2030;border-radius:8px;padding:24px;text-align:center;margin:20px 0">
            <div style="font-size:10px;color:#536080;letter-spacing:0.15em;text-transform:uppercase;margin-bottom:12px">Verification Code</div>
            <div style="font-size:40px;font-weight:900;letter-spacing:0.18em;color:#3bff9e;text-shadow:0 0 20px rgba(59,255,158,0.4)">{otp}</div>
          </div>
          <p style="font-size:11px;color:#2e3a52;text-align:center;margin-top:16px">
            If you didn't create an account, you can safely ignore this email.
          </p>
        </div>
      </div>
    </body>
    </html>
    """
    try:
        send_email_async.delay(subject, html_message, [email])
    except:
        send_email_sync(subject, html_message, [email])







    
def send_otp_email(email, otp, username=''):
    """Send 6-digit OTP for email verification"""
    subject = 'Your email Verification Code'
    html_message = f"""
    <!DOCTYPE html>
    <html>
    <body style="margin:0;padding:0;background:#080a0e;font-family:'Courier New',monospace">
      <div style="max-width:480px;margin:40px auto;background:#0c0f16;border:1px solid #1c2030;border-radius:12px;overflow:hidden">
        <div style="background:linear-gradient(135deg,#0d1f15,#0a1520);padding:28px;text-align:center;border-bottom:1px solid #1c2030">
          <div style="font-size:28px;margin-bottom:8px">SPH</div>
          <div style="font-family:sans-serif;font-size:20px;font-weight:900;color:#3bff9e;letter-spacing:-0.03em">SmartPyhub</div>
          <div style="font-size:11px;color:#536080;margin-top:4px">Email Verification</div>
        </div>
        <div style="padding:32px">
          <p style="font-size:13px;color:#536080;margin-bottom:20px">
            Hey {username or ' '} , use the code below to verify your email address.
            It expires in <strong style="color:#ffbf47">10 minutes</strong>.
          </p>
          <div style="background:#080a0e;border:1px solid #1c2030;border-radius:8px;padding:15px;text-align:center;margin:20px 0">
            <div style="font-size:10px;color:#536080;letter-spacing:0.15em;text-transform:uppercase;margin-bottom:12px">Verification Code</div>
            <div style="font-size:30px;font-weight:900;letter-spacing:0.18em;color:#3bff9e;text-shadow:0 0 20px rgba(59,255,158,0.4)">{otp}</div>
          </div>
          <p style="font-size:11px;color:#2e3a52;text-align:center;margin-top:16px">
            If you didn't create an account, you can safely ignore this email.
          </p>
        </div>
      </div>
    </body>
    </html>
    """
    try:
        send_email_async.delay(subject, html_message, [email])
    except:
        send_email_sync(subject, html_message, [email])
        
        
def send_account_delete_email(email, username=''):
    """Send 6-digit OTP for email verification"""
    subject = 'Account deletion '
    html_message = f"""
    <!DOCTYPE html>
    <html>
    <body style="margin:0;padding:0;background:#080a0e;font-family:'Courier New',monospace">
      <div style="max-width:480px;margin:40px auto;background:#0c0f16;border:1px solid #1c2030;border-radius:12px;overflow:hidden">
        <div style="background:linear-gradient(135deg,#0d1f15,#0a1520);padding:28px;text-align:center;border-bottom:1px solid #1c2030">
          <div style="font-size:28px;margin-bottom:8px">SPH</div>
          <div style="font-family:sans-serif;font-size:20px;font-weight:900;color:#3bff9e;letter-spacing:-0.03em">SmartPyhub</div>
          <div style="font-size:11px;color:#536080;margin-top:4px">ACCOUNT DELETION NOTICE</div>
        </div>
        <div style="padding:32px">
          <p style="font-size:13px;color:#536080;margin-bottom:20px">
            Hey {username or ' '} , your account has been successfully deleted.
            This means that <strong style="color:#ffbf47">your account and it's related data including your posts(if any),any interaction in terms of comments,likes,saves ,message (or any other associated actions) has been completely deleted and cannot be recovered in any way</strong>.
          </p>
          <div style="background:#080a0e;border:1px solid #1c2030;border-radius:8px;padding:24px;text-align:center;margin:20px 0">
            <div style="font-size:10px;color:#536080;letter-spacing:0.15em;text-transform:uppercase;margin-bottom:12px">❌</div>
            <div style="font-size:40px;font-weight:900;letter-spacing:0.18em;color:#3bff9e;text-shadow:0 0 20px rgba(59,255,158,0.4)">Account Deleted</div>
          </div>
          <p style="font-size:11px;color:#2e3a52;text-align:center;margin-top:16px">
          Thanks for using our products,you can always create another account as you wish
              </p>
        </div>
      </div>
    </body>
    </html>
    """
    try:
        send_email_async.delay(subject, html_message, [email])
    except:
        send_email_sync(subject, html_message, [email])
        
        



def send_phone_otp_sms(phone,otp):
    print(otp)
    # import requests
    # payload = {
    #     "to": phone,
    #     "from": "YourApp",
    #     "sms": f"Your login code is {code}. Valid for 10 minutes. Do not share.",
    #     "type": "plain",
    #     "api_key": settings.TERMII_API_KEY,
    #     "channel": "generic"
    # }
    # requests.post("https://api.ng.termii.com/api/sms/send", json=payload)
def set_phone_otp():
    pass
    # import requests
    # payload = {
    #     "to": phone,
    #     "from": "YourApp",
    #     "sms": f"Your login code is {code}. Valid for 10 minutes. Do not share.",
    #     "type": "plain",
    #     "api_key": settings.TERMII_API_KEY,
    #     "channel": "generic"
    # }
    
    # # requests.post("https://api.ng.termii.com/api/sms/send", json=payload)
        
        
        
#login activity
import user_agents
import requests

def parse_user_agent(request):
    ua_string = request.META.get("HTTP_USER_AGENT", "")
    ua = user_agents.parse(ua_string)

    return {
        "device": ua.get_device(),
        "os": ua.os.family,
        "browser": ua.browser.family,
    }

def get_ip_address(request):
    """Handles proxies and load balancers"""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")

def get_location_from_ip(ip):
    """Free IP geolocation - no API key needed"""
    try:
        response = requests.get(f"https://ipapi.co/{ip}/json/", timeout=3)
        data = response.json()
        city = data.get("city", "")
        country = data.get("country_name", "")
        return f"{city}, {country}" if city else country
    except Exception:
        return "Unknown"
      
#susupicious login detection
def is_suspicious_login(user, ip, location):
    """
    Flags login as suspicious if:
    - IP has never been seen before AND
    - Location is different from last known location
    """
    from .models import LoginActivity

    previous = LoginActivity.objects.filter(
        user=user,
        was_suspicious=False
    ).order_by("-created_at").first()

    if not previous:
        return False  # first ever login, not suspicious

    ip_changed = previous.ip_address != ip
    location_changed = (
        previous.location and 
        location and 
        previous.location.split(",")[-1].strip() != location.split(",")[-1].strip()
        # compares countries
    )
    return bool(ip_changed and location_changed)
  
  
  

from cryptography.fernet import Fernet
from django.conf import settings
import base64

def get_cipher():
    key = settings.FERNET_KEY.encode()
    return Fernet(key)

def encrypt_id_number(value: str) -> str:
    if not value:
        return value
    cipher = get_cipher()
    return cipher.encrypt(value.encode()).decode()

def decrypt_id_number(value: str) -> str:
    if not value:
        return value
    cipher = get_cipher()
    return cipher.decrypt(value.encode()).decode()
  
  
  
  #session management
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError

def get_jti_from_request(request) -> str | None:
    """
    Extracts the jti (JWT ID) from the access token in cookies
    Returns None if token is missing or invalid
    """
    token=None
    token=request.COOKIES.get("access_token")
    if not token:
        auth_header=request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer"):
            token=auth_header.split(" ")[1]
    if not token:
        return None
    try:
        decoded = AccessToken(token)
        return str(decoded["jti"])
    except TokenError as e:
        return None
      
    
    #2FA 
import hashlib
import secrets
import pyotp
import qrcode
import io
from django.core.cache import cache

# --- device fingerprint ---
def generate_device_fingerprint(request) -> str:
    """
    SHA256 hash of device + os + browser + user agent
    Same device always produces same fingerprint
    """
    ua = parse_user_agent(request)
    raw = f"{ua['device']}{ua['os']}{ua['browser']}{request.META.get('HTTP_USER_AGENT', '')}"
    return hashlib.sha256(raw.encode()).hexdigest()


# --- backup codes ---
def generate_backup_codes() -> tuple[list[str], list[str]]:
    """
    Returns (plain_codes, hashed_codes)
    plain_codes → shown to user once, never stored
    hashed_codes → stored in DB
    """
    plain_codes = [secrets.token_hex(4).upper() for _ in range(8)]
    # format as XXXX-XXXX for readability
    formatted = [f"{c[:4]}-{c[4:]}" for c in plain_codes]
    hashed = [
        hashlib.sha256(code.encode()).hexdigest() 
        for code in formatted
    ]
    return formatted, hashed


def verify_backup_code(plain_code: str, hashed_codes: list) -> int | None:
    """
    Returns index of matched code or None
    Index is used to remove the code after use
    """
    hashed_input = hashlib.sha256(plain_code.upper().encode()).hexdigest()
    for i, code in enumerate(hashed_codes):
        if code == hashed_input:
            return i
    return None


# --- TOTP ---
def generate_totp_secret() -> str:
    return pyotp.random_base32()


def get_totp_uri(secret: str, username: str) -> str:
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(
        name=username,
        issuer_name="SmartMarketPlace"
    )


def generate_qr_code(uri: str) -> str:
    """Returns base64 encoded QR code image — send directly to frontend"""
    qr = qrcode.make(uri)
    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode()


def verify_totp_code(secret: str, code: str) -> bool:
    totp = pyotp.TOTP(secret)
    # valid_window=1 allows 1 period before/after
    # handles clock drift between server and user's phone
    return totp.verify(code, valid_window=1)


# --- OTP for email/sms methods ---
def generate_2fa_otp() -> str:
    return str(secrets.randbelow(900000) + 100000)  # 6 digits, cryptographically secure


# --- temp token --- (proves password was correct, before 2FA)
def generate_temp_token(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    cache.set(
        f"2fa_temp:{token}",
        {"user_id": user_id},
        timeout=600  # 10 minutes
    )
    return token


def verify_temp_token(token: str) -> str | None:
    """Returns user_id if valid, None if expired/invalid"""
    data = cache.get(f"2fa_temp:{token}")
    if not data:
        return None
    return data["user_id"]


def consume_temp_token(token: str) -> str | None:
    """Verify and delete in one step — can only be used once"""
    user_id = verify_temp_token(token)
    if user_id:
        cache.delete(f"2fa_temp:{token}")
    return user_id


# --- 2FA challenge (stored in Redis) ---
def create_2fa_challenge(user_id: str, code: str, method: str) -> None:
    hashed = hashlib.sha256(code.encode()).hexdigest()
    cache.set(
        f"2fa_challenge:{user_id}",
        {"code": hashed, "method": method, "attempts": 0},
        timeout=600  # 10 minutes
    )


def verify_2fa_challenge(user_id: str, code: str) -> dict:
    """
    Returns {"success": bool, "error": str | None}
    Tracks wrong attempts — destroys challenge at 5
    """
    key = f"2fa_challenge:{user_id}"
    challenge = cache.get(key)

    if not challenge:
        return {"success": False, "error": "Challenge expired. Please log in again."}

    challenge["attempts"] += 1

    if challenge["attempts"] >= 5:
        cache.delete(key)
        return {"success": False, "error": "Too many attempts. Please log in again."}

    hashed_input = hashlib.sha256(code.encode()).hexdigest()
    if challenge["code"] != hashed_input:
        cache.set(key, challenge, timeout=600)  # update attempt count
        remaining = 5 - challenge["attempts"]
        return {"success": False, "error": f"Invalid code. {remaining} attempts remaining."}

    cache.delete(key)  # consumed — delete immediately
    return {"success": True, "error": None}


def destroy_2fa_challenge(user_id: str) -> None:
    cache.delete(f"2fa_challenge:{user_id}")
    
    
    
