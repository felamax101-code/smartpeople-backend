from rest_framework import serializers
from django.contrib.auth import get_user_model


from django.contrib.auth.password_validation import validate_password

from django.db.models import Q
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
from datetime import date
from django.contrib.auth.hashers import make_password

User = get_user_model()
import magic
from PIL import Image
import io
from django.core.files.uploadedfile import InMemoryUploadedFile
from feed.upload import upload_image
from .fields import PhoneNumberField
from .models import VerificationRequest,ProfileReport,ReportAppeal,Notification,NotificationPreferences
from .tasks import activate_user_posts
from .utils import send_otp_email
from .Verification import Verification
from .validators import EmailValidator, FlexibleUsernameValidator,normalize_phone



#  Helpers 


class UserSerializer(serializers.ModelSerializer):
    """Full user info — for /users/me/"""
    
    verification_badge=serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = [
            'id', 'username', 'name',  'avatar',"followers","following","role",
            "bio","phone","email","phone","is_email_verified","phone_verified","total_posts","rating","reviews_count",
            "verification_level","verification_badge","created_at",
            
             
        ]
        
    def get_verification_badge(self,obj):
        badge=obj.verification_badge
        return {
                "label":badge.get("label"),
                "color":badge.get("color"),
                "icon":badge.get("icon")
        }
    
    


class OtherUserSerializer(serializers.ModelSerializer):

    contacts=serializers.SerializerMethodField()
   
    class Meta:
        model = User
        fields = [
            'id', 'username', 'name', 'avatar',
            'followers', "following",'total_post', 'rating', 'review_count',"location","last_seen",
            "contacts","posts","created_at",
        ]
  

    def get_contacts(self, obj):
        request = self.context.get('request')
        user=request.user
        if not request :
            return 
        from .models import Contacts
        contacts=Contact.objects.get(owner=user)
        for i in contacts :
            return [
                {"type":"i.contact_type"},
                {"label":"i.label"},
                {"value","i.value"}
            ]
    def get_posts(self,obj):
        if not request:
            return
        return Post.objects.filter(owner=obj)
    

#  Auth Serializers 

class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True, validators=[EmailValidator()])
    username = serializers.CharField(required=True, validators=[FlexibleUsernameValidator()])
    name = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True)
    password_confirm=serializers.CharField(write_only=True, required=False)
    def validate_password(self, value):
        validate_password(value)
        return value
    def validate(self,data):
        password=data.get("password")
        password_confirm=data.get("password_confirm")
        if password_confirm and password_confirm!=password:
            raise serializers.ValidationError("password and password confirm must match")
        return data
    def create(self, validated_data):
        
        with transaction.atomic():
            user = User.objects.create_user(
                email=validated_data['email'],
                username=validated_data['username'],
                name=validated_data['name'],
                password=validated_data['password'],
                role='client',
            )
            success, otp = Verification.generate_email_otp(user.email)
            if success:
                send_otp_email(user.email, otp, user.username)
        return user


class VerifyEmailSerializer(serializers.Serializer):
    otp = serializers.CharField(required=True, min_length=6, max_length=6)
    email=serializers.CharField(required=True)

    def validate(self, data):
        otp = data.get('otp')
        email = data.get('email')
        try:
            user = User.objects.get(email=email)
            if user.is_email_verified:
                raise serializers.ValidationError("Email is already verified. GO back to login")
            success, message = Verification.verify_email_otp(user, otp)
            if not success:
                raise serializers.ValidationError(message)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found.")
        data['user'] = user
        return data


class ResendSerializer(serializers.Serializer):
    email = serializers.CharField(required=True)

    def validate(self, data):
        email = data.get('email')
        try:
            user = User.objects.get(email=email)
            if user.is_email_verified:
                raise serializers.ValidationError("Email is already verified.Press go back to proceed to login page")
            with transaction.atomic():
                success, otp = Verification.generate_email_otp(user.email)
                if success:
                    send_otp_email(user.email, otp, user.username)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found.")
        return data


class LoginSerializer(serializers.Serializer):
    email = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')

        try:
            user = User.objects.get(Q(email__iexact=email) )
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid credentials.")
        if not user.is_email_verified:
            with transaction.atomic():
                success, otp = Verification.generate_email_otp(user.email)
                if success:
                    send_otp_email(user.email, otp, user.username)
            raise serializers.ValidationError("Please verify your email before logging in.")

        if not user.check_password(password):
            raise serializers.ValidationError("Invalid credentials.")

        

        if user.is_deactivated:
            with transaction.atomic():
                user.is_deactivated=False
                user.save()
                activate_user_posts.delay(user.id)

        if user.is_locked:
            raise serializers.ValidationError("This account is locked. Contact support.")

        data['user'] = user
        return data


class PasswordResetConfirmSerializer(serializers.Serializer):
    otp = serializers.CharField(required=True)
    new_password = serializers.CharField(write_only=True, required=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value

    def validate(self, data):
        otp = data.get('otp')
        try:
            user = User.objects.get(password_reset_otp=otp)
            if not user.password_reset_otp_expiry or timezone.now() > user.password_reset_otp_expiry:
                raise serializers.ValidationError("Reset otp has expired. Please request a new one.")
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid or expired reset otp.")
        data['user'] = user
        return data

    def save(self, **kwargs):
        user = self.validated_data['user']
        password = self.validated_data['new_password']
        user.set_password(password)
        user.password_reset_otp = None
        user.password_reset_otp_expiry = None
        user.save()
        return user


#  Profile Serializers 
import filetype

class UpdateProfileSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, allow_blank=True)
    bio = serializers.CharField(required=False, allow_blank=True)
    avatar=serializers.ImageField(required=False)
    location=serializers.CharField(required=False, allow_blank=True)
    username=serializers.CharField(required=False, allow_blank=True,validators=[])

    def validate_avatar(self, value):
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("Avatar too large. Max 5MB.")

    # detect from actual bytes, not client headers
        kind = filetype.guess(value.read(2048))
        value.seek(0)
        if kind is None or kind.mime not in ['image/jpeg', 'image/png', 'image/webp']:
            raise serializers.ValidationError("Invalid file. Upload a JPEG, PNG, or WebP image.")

    # verify it's not corrupt
        try:
            img = Image.open(value)
            img.verify()
            value.seek(0)
        except Exception:
            raise serializers.ValidationError("Uploaded file is not a valid image.")

        return value
    def _compress(self, image_file):
        img = Image.open(image_file).convert('RGB')  # convert PNG/WebP to RGB
        img.thumbnail((400, 400))  # resize in place, keeps aspect ratio

        output = io.BytesIO()
        img.save(output, format='JPEG', quality=85, optimize=True)
        output.seek(0)

        filename = image_file.name.rsplit('.', 1)[0] + '.jpg'

        return InMemoryUploadedFile(
            output,
            'ImageField',
            filename,
            'image/jpeg',
            output.getbuffer().nbytes,
            None
        )
    def validate_location(self,value):
        return  sanitize_plain(value)
    def validate_bio(self,value):
        return sanitize_plain(value)
    def validate_username(self,value):
        user=User.objects.filter(username=value).first()
        if user!=self.context.get("request").user:
            raise serializers.ValidationError("username already taken .")
        return  sanitize_plain(value)
    def validate_name(self,value):
        return  sanitize_plain(value)
    def update_user(self):
        request = self.context.get('request')
        user = request.user
        name = self.validated_data.get('name')
        bio = self.validated_data.get('bio')
        username = self.validated_data.get('username')
        location = self.validated_data.get('location')
        avatar=self.validated_data.get("avatar")
        if avatar is not None:
            user.avatar=self._compress(avatar)
        if name is not None:
            user.name = name
        if username is not None:
            user.username=username
        if location is not None:
            user.location=location
        if bio is not None:
            user.bio = bio
        user.save()
        return user




class AvatarSerializer(serializers.Serializer):
    avatar = serializers.ImageField(required=True)

    def validate_avatar(self, value):
        # 1. Size check
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("Avatar too large. Max 5MB.")

        # 2. Check actual file bytes, not the header the client sent
        file_type = magic.from_buffer(value.read(2048), mime=True)
        value.seek(0)  # rewind after reading
        if file_type not in ['image/jpeg', 'image/png', 'image/webp']:
            raise serializers.ValidationError("Invalid file. Upload a JPEG, PNG, or WebP image.")

        # 3. Verify it's a real image PIL can open (catches corrupt files)
        try:
            img = Image.open(value)
            img.verify()  # checks for corruption without fully decoding
            value.seek(0)
        except Exception:
            raise serializers.ValidationError("Uploaded file is not a valid image.")

        return value

    def save_avatar(self):
        user = self.context.get('request').user
        avatar_file = self.validated_data['avatar']

        # Compress and resize before saving
        compressed = self._compress(avatar_file)

        if user.avatar:
            user.avatar.delete(save=False)
        # url=upload_image(compressed,folder="user/avatars")
        user.avatar = compressed
        user.save()
        return user

    def _compress(self, image_file):
        img = Image.open(image_file).convert('RGB')  # convert PNG/WebP to RGB
        img.thumbnail((400, 400))  # resize in place, keeps aspect ratio

        output = io.BytesIO()
        img.save(output, format='JPEG', quality=85, optimize=True)
        output.seek(0)

        filename = image_file.name.rsplit('.', 1)[0] + '.jpg'

        return InMemoryUploadedFile(
            output,
            'ImageField',
            filename,
            'image/jpeg',
            output.getbuffer().nbytes,
            None
        )


class AccountDeletionSerializer(serializers.Serializer):
    password = serializers.CharField(required=True, write_only=True)
    otp=serializers.CharField(required=True,max_length=6,min_length=6, write_only=True)
    def validate(self, data):
        request = self.context.get('request')
        user = request.user
        if not user.check_password(data.get('password')):
            raise serializers.ValidationError("Incorrect password.")
        success,message=Verification().verify_email_account_delete_otp(user=user,otp = data.get('otp'))
        if not success:
            raise serializers.ValidationError(message)

    def delete_account(self):
        request = self.context.get('request')
        request.user.delete()


#  Password Change 

class ChangePasswordRequestSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)

    def validate(self, data):
        request = self.context.get('request')
        user = request.user
        if not user.check_password(data.get('current_password')):
            raise serializers.ValidationError("Current password is incorrect.")
        validate_password(data.get('new_password'), user)
        return data

    def send_otp(self):
        request = self.context.get('request')
        user = request.user
        new_password = self.validated_data['new_password']
        with transaction.atomic():
            # Store hashed new password temporarily
            user.new_password = make_password(new_password)
            user.save()
            success, otp = Verification.generate_password_change_otp(user.email)
            if success:
                send_otp_email(user.email, otp, user.username)


class ChangePasswordConfirmSerializer(serializers.Serializer):
    otp = serializers.CharField(required=True, max_length=6, min_length=6)

    def validate(self, data):
        request = self.context.get('request')
        user = request.user
        otp = data.get('otp')
        success, message = Verification.verify_password_change_otp(user, otp)
        if not success:
            raise serializers.ValidationError(message)
        if not user.new_password:
            raise serializers.ValidationError("No pending password change found.")
        return data

    def apply_change(self):
        request = self.context.get('request')
        user = request.user
        with transaction.atomic():
            user.password = user.new_password
            user.new_password = None
            user.save()


#  Email Change ─

class ChangeEmailRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True,validators=[EmailValidator()])

  
    def validate_email(self,value):
        user=User.objects.filter(email__iexact=value).first()
        if user and user!=self.context.get("request").user:
            raise serializers.ValidationError("This email number is already in use by another user")
    def validate(self, data):
        request = self.context.get('request')
        user = request.user
        # Enforce 7-day cooldown
        if user.last_email_change:
            days_since = (timezone.now() - user.last_email_change).days
            if days_since < 7:
                remaining = 7 - days_since
                raise serializers.ValidationError(
                    f"You can only change your email once every 7 days. "
                    f"{remaining} day(s) remaining."
                )
        return data

    def send_otp(self):
        request = self.context.get('request')
        user = request.user
        new_email = self.validated_data['email']
        with transaction.atomic():
            user.new_email = new_email
            user.save()
            success, otp = Verification.generate_email_otp(user.email)
            if success:
                send_otp_email(new_email, otp, user.username)


class ChangeEmailConfirmSerializer(serializers.Serializer):
    otp = serializers.CharField(required=True, max_length=6, min_length=6)

    def validate(self, data):
        request = self.context.get('request')
        user = request.user
        otp = data.get('otp')
        if not user.new_email:
            raise serializers.ValidationError("No pending email change found.")
        success, message = Verification.verify_email_otp(user, otp)
        if not success:
            raise serializers.ValidationError(message)
        return data

    def apply_change(self):
        request = self.context.get('request')
        user = request.user
        with transaction.atomic():
            user.email = user.new_email
            user.new_email = None
            user.last_email_change = timezone.now()
            user.save()


#  Social Links ─

class SocialLinkCreateSerializer(serializers.Serializer):
    platform = serializers.ChoiceField(choices=[
        'GitHub', 'Twitter', 'LinkedIn', 'YouTube',
        'Website', 'Dev.to', 'Hashnode', 'Other'
    ])
    name = serializers.CharField(max_length=100)
    url = serializers.URLField()

    def create_link(self):
        from .models import SocialLink
        request = self.context.get('request')
        return SocialLink.objects.create(
            user=request.user,
            platform=self.validated_data['platform'],
            name=self.validated_data['name'],
            url=self.validated_data['url'],
            
            
        )



#phone number



class PhoneAddSerializer(serializers.Serializer):
    phone = PhoneNumberField(default_country="KE")

    def validate_phone(self, value):
        # value is already E.164 at this point
        user=User.objects.filter(phone=value).first()
        if user and user!=self.context.get("request").user:
            raise serializers.ValidationError("This phone number is already in use by another user")
        # if user.last_phone_change:
        #     days_since = (timezone.now() - user.last_phone_change).days
        #     if days_since < 7:
        #         remaining = 7 - days_since
        #         raise serializers.ValidationError(
        #             f"You can only change your phone once every 7 days. "
        #             f"{remaining} day(s) remaining."
        #         )
        return value

class PhoneVerifySerializer(serializers.Serializer):

    otp=serializers.CharField(required=True)
    


class IdentityVerificationSerializer(serializers.Serializer):
    id_type = serializers.ChoiceField(choices=["nin", "passport", "national_id", "drivers_license"])
    id_number = serializers.CharField(max_length=50)
    id_front = serializers.URLField()
    id_back = serializers.URLField(required=False, allow_null=True)
    selfie = serializers.URLField()
    document_expiry_date = serializers.DateField(required=False, allow_null=True)

    def validate(self, data):
        expiry_required = {"passport", "national_id", "drivers_license"}
        if data.get("id_type") in expiry_required:
            if not data.get("document_expiry_date"):
                raise serializers.ValidationError({
                    "document_expiry_date": f"Required for {data['id_type']}"
                })
            if data["document_expiry_date"] < date.today():
                raise serializers.ValidationError({
                    "document_expiry_date": "Document is already expired"
                })
        return data


class BusinessVerificationSerializer(serializers.Serializer):
    business_name = serializers.CharField(max_length=255)
    rc_number = serializers.CharField(max_length=50)
    business_address = serializers.CharField()
    cac_document = serializers.URLField()


class VerificationReviewSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "reject"])
    reason = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        if data["action"] == "reject" and not data.get("reason"):
            raise serializers.ValidationError({
                "reason": "Required when rejecting"
            })
        return data


class VerificationStatusSerializer(serializers.ModelSerializer):
    attempts_remaining_identity = serializers.SerializerMethodField()
    attempts_remaining_business = serializers.SerializerMethodField()
    identity_is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = VerificationRequest
        fields = [
            "identity_status",
            "id_type",
            "document_expiry_date",
            "identity_rejection_reason",
            "identity_reviewed_at",
            "identity_is_expired",
            "attempts_remaining_identity",
            "business_status",
            "business_name",
            "rc_number",
            "business_rejection_reason",
            "business_reviewed_at",
            "attempts_remaining_business",
            "updated_at",
        ]

    def get_attempts_remaining_identity(self, obj) -> int:
        return max(0, 5 - obj.identity_attempt_count)

    def get_attempts_remaining_business(self, obj) -> int:
        return max(0, 5 - obj.business_attempt_count)
    
from .sanitize import sanitize_plain
        
class ProfileReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfileReport
        fields = ["id", "reason", "description", "status", "action_taken", "created_at"]
        read_only_fields = ["id", "status", "action_taken", "created_at"]

    def validate(self, data):
        if data.get("reason") == "Other" and not data.get("description"):
            raise serializers.ValidationError({
                "description": "Required when reason is 'other'"
            })
        reason =data.get("reason")
        description=data.get("description")
        reason=sanitize_plain(reason)
        data['reason']=sanitize_plain(reason)
        data["description"]=sanitize_plain(description)
        return data


class ReportReviewSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["none", "warn", "suspend", "ban", "dismiss"])


class ReportAppealSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportAppeal
        fields = ["id", "message", "status", "created_at"]
        read_only_fields = ["id", "status", "created_at"]


class AppealReviewSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["accepted", "rejected"])


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id", "notification_type", "title",
            "body", "data", "is_read", "created_at"
        ]
        
        

from datetime import date


class IdentityVerificationSerializer(serializers.Serializer):
    id_type = serializers.ChoiceField(
        choices=["nin", "passport", "national_id", "drivers_license"]
    )
    id_number = serializers.CharField(max_length=50)
    id_front = serializers.ImageField()          # actual file
    id_back = serializers.ImageField(required=False, allow_null=True)
    selfie = serializers.ImageField()            # actual file
    document_expiry_date = serializers.DateField(required=False, allow_null=True)

    def validate(self, data):
        expiry_required = {"passport", "national_id", "drivers_license"}
        if data.get("id_type") in expiry_required:
            if not data.get("document_expiry_date"):
                raise serializers.ValidationError({
                    "document_expiry_date": f"Required for {data['id_type']}"
                })
            if data["document_expiry_date"] < date.today():
                raise serializers.ValidationError({
                    "document_expiry_date": "Document is already expired"
                })
        return data


class BusinessVerificationSerializer(serializers.Serializer):
    business_name = serializers.CharField(max_length=255)
    rc_number = serializers.CharField(max_length=50)
    business_address = serializers.CharField()
    cac_document = serializers.ImageField()      # actual file
    
    
class NotificationPreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model=NotificationPreferences
        fields=["new_message","product_approved","product_rejected","new_follower",
                "product_upvote","new_comment","new_review","account_alerts","promotions"]
    
    def update(self,instance,validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
    
    




