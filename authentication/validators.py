from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import re
from disposable_email_checker.validators import validate_disposable_email
from django.contrib.auth import get_user_model
CustomUser=get_user_model()


class EmailValidator:
    def __call__(self, email):
        email = email.strip().lower()
        validate_email(email)
        try:
            validate_disposable_email(email)
        except ValidationError:
            raise ValidationError("To ensure security,please use a permanent email adress")
        if CustomUser.objects.filter(email__iexact=email).first():
            raise ValidationError("Email already used to register another account.Try another one")
        return email


class StrongPasswordValidator:
    """Used in AUTH_PASSWORD_VALIDATORS"""

    def validate(self, password, user=None):
        if not re.search(r"[A-Z]", password):
            raise ValidationError(
                _("Password must contain at least one uppercase letter."),
                code="password_no_uppercase",
            )
        if not re.search(r"[a-z]", password):
            raise ValidationError(
                _("Password must contain at least one lowercase letter."),
                code="password_no_lowercase",
            )
        if not re.search(r"[0-9]", password):
            raise ValidationError(
                _("Password must contain at least one number."),
                code="password_no_number",
            )
        if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", password):
            raise ValidationError(
                _("Password must contain at least one special character."),
                code="password_no_special",
            )
        common = ['password123', 'qwerty123', 'admin123', '12345678', 'welcome123']
        if password.lower() in common:
            raise ValidationError(_("This password is too common. Choose a stronger one."))

    def get_help_text(self):
        return _(
            "Password must have uppercase, lowercase, a number, and a special character."
        )


class FlexibleUsernameValidator:
    def __init__(self, *, min_length=3, max_length=24):
        self.min_length = min_length
        self.max_length = max_length
        self.forbidden = {"admin", "root", "support", "system", "staff", "superuser"}

    def __call__(self, username):
        username = username.strip()

        if CustomUser.objects.filter(username__iexact=username).exists():
            raise ValidationError(_("This username is already taken."))

        if len(username) < self.min_length:
            raise ValidationError(_(f"Username must be at least {self.min_length} characters."))

        if len(username) > self.max_length:
            raise ValidationError(_(f"Username must not exceed {self.max_length} characters."))

        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise ValidationError(_("Username can only contain letters, numbers, and underscores."))

        if username.isdigit():
            raise ValidationError(_("Username cannot be only numbers."))

        if username.lower() in self.forbidden:
            raise ValidationError(_("This username is forbidden."))

        return username
    
    

            
            
            
            
import phonenumbers
from phonenumbers import NumberParseException

def normalize_phone(phone: str, default_country: str = "KE") -> dict:
    """
    Normalizes any phone input to E.164 format (+2348012345678)
    
    Handles:
        0812345678        → +2348012345678  (local with leading 0)
        812345678         → +2348012345678  (no leading 0)
        2348012345678     → +2348012345678  (country code, no +)
        +2348012345678    → +2348012345678  (already correct)
        +254712345678     → +254712345678   (Kenya, respected as-is)
        07 1234 5678      → +2348012345678  (spaces handled)
        (0812) 345-6789   → +2348012345678  (dashes/brackets handled)
    
    default_country: ISO 3166-1 alpha-2 code (NG, KE, GH, ZA, US etc.)
                     used only when no country code is present
    """
    if not phone:
        return {"success": True, "error": "Phone number is required"}

    # strip whitespace, dashes, brackets — phonenumbers handles most but let's be safe
    cleaned = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")

    try:
        # if number starts with + it has explicit country code — parse directly
        # otherwise use default_country as hint
        parsed = phonenumbers.parse(
            cleaned, 
            None if cleaned.startswith("+") else default_country
        )
    except NumberParseException as e:
        return {"success": False, "error": f"Invalid phone number: {str(e)}"}

    # validate the number is actually possible/valid
    if not phonenumbers.is_possible_number(parsed):
        return {"success": False, "error": "Phone number is not possible"}

    if not phonenumbers.is_valid_number(parsed):
        return {"success": False, "error": "Phone number is not valid"}

    # format to E.164 — the universal standard (+2348012345678)
    e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)

    # extract useful metadata
    country_code = parsed.country_code                          # 234
    national = phonenumbers.format_number(                      # 08012345678
        parsed, phonenumbers.PhoneNumberFormat.NATIONAL
    )
    international = phonenumbers.format_number(                 # +234 801 234 5678
        parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL
    )
    region = phonenumbers.region_code_for_number(parsed)        # "NG"

    return {
        "success": True,
        "e164": e164,                   # store this in DB — always consistent
        "national": national,           # display to user
        "international": international, # display internationally
        "country_code": country_code,
        "region": region,
    }
