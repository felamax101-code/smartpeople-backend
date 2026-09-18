from django.contrib.auth import get_user_model
import secrets
from datetime import timedelta
from django.utils import timezone

User = get_user_model()


class Verification():

    @staticmethod
    def generate_email_otp(email):
        alphabet = "ABCDEFGHJKMNPQRTUVWXY23456789"
        otp = ''.join(secrets.choice(alphabet) for _ in range(6))
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return False, "User not found"
        user.email_otp = otp
        user.email_otp_expiry = timezone.now() + timedelta(minutes=10)
        user.save()
        return True, otp

    @staticmethod
    def verify_email_otp(user, otp):
        valid_otp = user.email_otp
        if not valid_otp:
            return False, "No OTP found. Please request a new one."
        if otp.upper() != valid_otp.upper():
            return False, "Wrong OTP. Please try again."
        if timezone.now() > user.email_otp_expiry:
            return False, "OTP has expired. Press resend to request a new one."
        # Clear OTP after successful verification
        user.email_otp = None
        user.email_otp_expiry = None
        user.is_email_verified = True
        user.save()
        return True, "Verified successfully"

    @staticmethod
    def generate_password_change_otp(email):
        """Generate OTP for password change confirmation"""
        alphabet = "ABCDEFGHJKMNPQRTUVWXY23456789"
        otp = ''.join(secrets.choice(alphabet) for _ in range(6))
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return False, "User not found"
        user.password_change_otp = otp
        user.password_change_expiry = timezone.now() + timedelta(minutes=10)
        user.save()
        return True, otp

    @staticmethod
    def verify_password_change_otp(user, otp):
        valid_otp = user.password_change_otp
        if not valid_otp:
            return False, "No OTP found. Please request a new one."
        if otp.upper() != valid_otp.upper():
            return False, "Wrong OTP. Please try again."
        if timezone.now() > user.password_change_expiry:
            return False, "OTP has expired. Please request a new one."
        user.password_change_otp = None
        user.password_change_expiry = None
        user.save()
        return True, "OTP verified"

    @staticmethod
    def set_phone_otp(user, phone):
        """Sets OTP and expiry on the user, returns the OTP"""
        alphabet = "ABCDEFGHJKMNPQRTUVWXY23456789"
        otp = ''.join(secrets.choice(alphabet) for _ in range(6))
        if user.phone!=phone:
            user.phone_verified=False
        user.new_phone = phone
        user.phone_otp = otp
        user.phone_otp_expiry = timezone.now() + timedelta(minutes=10)
        user.phone_verified = False
        user.save()
        return otp
    
    
    
    @staticmethod
    def generate_password_reset_otp(email):
        """Generate OTP for password change confirmation"""
        alphabet = "ABCDEFGHJKMNPQRTUVWXY23456789"
        otp = ''.join(secrets.choice(alphabet) for _ in range(6))
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return False, "User not found"
        user.password_reset_otp = otp
        user.password_reset_expiry = timezone.now() + timedelta(minutes=10)
        user.save()
        return True, otp

    @staticmethod
    def verify_password_reset_otp(user, otp):
        valid_otp = user.password_change_otp
        if not valid_otp:
            return False, "No OTP found. Please request a new one."
        if otp.upper() != valid_otp.upper():
            return False, "Wrong OTP. Please try again."
        if timezone.now() > user.password_change_expiry:
            return False, "OTP has expired. Please request a new one."
        user.password_change_otp = None
        user.password_change_expiry = None
        user.save()
        return True, "OTP verified"
    
    
    @staticmethod
    def generate_email_change_otp(user,email):
        alphabet = "ABCDEFGHJKMNPQRTUVWXY23456789"
        otp = ''.join(secrets.choice(alphabet) for _ in range(6))
        user.email_otp = otp
        user.email_otp_expiry = timezone.now() + timedelta(minutes=10)
        user.save()
        return True, otp

    @staticmethod
    def verify_email_change_otp(user, otp):
        valid_otp = user.email_otp
        if not valid_otp:
            return False, "No OTP found. Please request a new one."
        if otp.upper() != valid_otp.upper():
            return False, "Wrong OTP. Please try again."
        if timezone.now() > user.email_otp_expiry:
            return False, "OTP has expired. Press resend to request a new one."
        # Clear OTP after successful verification
        user.email_otp = None
        user.email_otp_expiry = None
        user.is_email_verified = True
        user.save()
        return True, "Verified successfully"
    
    
    
    
    @staticmethod
    def generate_email_account_delete_otp(email):
        alphabet = "ABCDEFGHJKMNPQRTUVWXY23456789"
        otp = ''.join(secrets.choice(alphabet) for _ in range(6))
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return False, "User not found"
        user.account_delete_email_otp = otp
        user.account_delete_email_otp_expiry = timezone.now() + timedelta(minutes=10)
        user.save()
        return True, otp

    @staticmethod
    def verify_email_account_delete_otp(user, otp):
        valid_otp = user.account_delete_email_otp
        if not valid_otp:
            return False, "No OTP found. Please request a new one."
        if otp.upper() != valid_otp.upper():
            return False, "Wrong OTP. Please try again."
        if timezone.now() > user.email_otp_expiry:
            return False, "OTP has expired. Press resend to request a new one."
        # Clear OTP after successful verification
        user.account_delete_email_otp = None
        user.account_delete_email_otp_expiry = None
        user.save()
        return True, "Verified successfully"

    