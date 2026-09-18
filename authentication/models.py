

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager, Group
import uuid
from disposable_email_checker.validators import validate_disposable_email

import pyotp
from django.contrib.postgres.fields import ArrayField


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is mandatory")
        email = self.normalize_email(email)
        role = extra_fields.get('role', None)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        if role:
            group, _ = Group.objects.get_or_create(name=role.capitalize())
            user.groups.add(group)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, role="Admin", **extra_fields)
    


def check_disposable_email(value):
    return validate_disposable_email(value)
class CustomUser(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        ("client", "Client"),
        ("staff", "Staff"),
        ("admin", "Admin"),
    )
    
    
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    email = models.EmailField(validators=[check_disposable_email],unique=True)
    username = models.CharField(max_length=24, unique=True, default="")
    bio =models.TextField(null=True,blank=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    password = models.CharField(max_length=255)
    avatar = models.ImageField(upload_to="user/avatars/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now_add=True)
    role = models.CharField(choices=ROLE_CHOICES, max_length=10, blank=True, null=True, default="client")
    
    is_staff = models.BooleanField(default=False)

    is_email_verified = models.BooleanField(default=False)
    email_otp = models.CharField(max_length=6, blank=True, null=True)
    email_otp_expiry = models.DateTimeField(blank=True, null=True)
    last_email_change = models.DateTimeField(blank=True, null=True)

    # For email change flow
    new_email = models.EmailField(blank=True, null=True)
    #for phone change
    new_phone = models.CharField(blank=True, null=True)
    #username change
    last_username_change=models.DateTimeField(blank=True, null=True)
    #password reset otp section
    password_reset_otp = models.CharField(max_length=255, blank=True, null=True)
    password_reset_otp_expiry = models.DateTimeField(blank=True, null=True)
    
    #phone number
    phone= models.CharField(max_length=20, blank=True, null=True)
    phone_verified= models.BooleanField(default=False)
    phone_otp=models.CharField(max_length=6, blank=True, null=True)
    phone_otp_expiry= models.DateTimeField(blank=True, null=True)
    last_phone_change= models.DateTimeField(blank=True, null=True)
    
    #password change
    password_change_otp = models.CharField(max_length=6, blank=True, null=True)
    password_change_expiry = models.DateTimeField(blank=True, null=True)
    new_password = models.CharField(max_length=255, blank=True, null=True)

    
    is_active= models.BooleanField(default=True)
    is_locked = models.BooleanField(default=False)
    is_deactivated = models.BooleanField(default=False) 

    followers = models.PositiveIntegerField(default=0)
    following = models.PositiveIntegerField(default=0)
    total_posts = models.PositiveIntegerField(default=0)
    rating=models.FloatField(default=0.0)
    reviews_count=models.PositiveIntegerField(default=0)
    
    location= models.CharField(max_length=255, blank=True, null=True)
    last_seen=models.DateTimeField(blank=True, null=True)
    
    
    #fcm notifications
    fcm_token=models.CharField(max_length=255,blank=True,null=True)
    fcm_token_updated_at=models.DateTimeField(null=True,blank=True)
    avatar = models.ImageField(upload_to="user/avatars/", null=True, blank=True)
    
    #account deletion
    account_delete_email_otp=models.CharField(max_length=6,blank=True,null=True)
    account_delete_email_otp_expiry=models.DateTimeField(null=True,blank=True)
    
    
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]
    objects = UserManager()
    
    
    class Meta:
        db_table="CustomUser"
        
    def __str__(self):
        return f"{self.email} : {self.username}"

  
    
    @property
    def verification_level(self) -> int:
        level = 0
        if self.is_email_verified:
            level += 1
        if self.phone_verified:
            level += 1
        try:
            vr = self.verification_request
            if vr.identity_status == "approved" and not vr.identity_is_expired:
                level += 1
            if vr.business_status == "approved":
                level += 1
        except VerificationRequest.DoesNotExist:
            pass
        return level

    @property
    def verification_badge(self) -> dict:   
        badges = {
        0: {"label": None, "color": None, "icon": None},
        1: {"label": "Email Verified", "color": "#6B7280", "icon": "📧","description":"Email address confirmed"},
        2: {"label": "Trusted Member", "color": "#3B82F6", "icon": "📱","description":"Phone number confirmed"},
        3: {"label": "ID Verified", "color": "#10B981", "icon": "🪪","description":"Government ID confirmed"},
        4: {"label": "Verified Business", "color": "#F59E0B", "icon": "🏢","description":"Business registration confirmed"},
    }
        return badges[self.verification_level]
    
class Contacts(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    owner=models.ForeignKey(CustomUser,on_delete=models.CASCADE,related_name="contacts")
    contact_type=models.CharField()
    lable=models.CharField()
    value=models.CharField()
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'Contacts'
    def __str__(self):
        
        return f"{self.owner.username} {self.lable}'s contact"
class Follow(models.Model):
    
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    follower=models.ForeignKey(CustomUser,on_delete=models.CASCADE,related_name="folower")
    following=models.ForeignKey(CustomUser,on_delete=models.CASCADE,related_name="following_set")
    created_at=models.DateTimeField(auto_now_add=True)
    
    class  Meta:
        db_table = 'Follow'
        unique_together=("follower","following")
    def __str__(self):
        return f"{self.follower.username} follow {self.following.username}"

        
        
class LoginActivity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="login_activities")
    ip_address = models.GenericIPAddressField(null=True)
    device = models.CharField(max_length=255, null=True)
    os = models.CharField(max_length=100, null=True)
    browser = models.CharField(max_length=100, null=True)
    location = models.CharField(max_length=255, null=True)
    was_suspicious = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "Login Activity"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.ip_address} - {self.created_at}"




class VerificationRequest(models.Model):
    
    # --- choices ---
    IDENTITY_TYPE = (
        ("nin", "NIN"),
        ("passport", "International Passport"),
        ("national_id", "National ID Card"),
        ("drivers_license", "Driver's License"),
    )

    STATUS = (
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("resubmitted", "Resubmitted"),
        ("exhausted", "Exhausted"),
        ("expired", "Expired"),
    )

    # --- core ---
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name="verification_request"
    )

    # --- identity section ---
    identity_status = models.CharField(
        max_length=20, choices=STATUS, default="pending", null=True, blank=True
    )
    id_type = models.CharField(
        max_length=20, choices=IDENTITY_TYPE, null=True, blank=True
    )
    id_number = models.CharField(max_length=255, null=True, blank=True)  # we encrypt this
    id_front = models.ImageField(null=True, blank=True)
    id_back = models.ImageField(null=True, blank=True)   # nullable — NIN doesn't need back
    selfie = models.ImageField(null=True, blank=True)
    document_expiry_date = models.DateField(null=True, blank=True)
    identity_rejection_reason = models.TextField(null=True, blank=True)
    identity_reviewed_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name="identity_reviews"
    )
    identity_reviewed_at = models.DateTimeField(null=True, blank=True)
    identity_attempt_count = models.PositiveIntegerField(default=0)

    # --- business section ---
    business_status = models.CharField(
        max_length=20, choices=STATUS, null=True, blank=True
    )
    business_name = models.CharField(max_length=255, null=True, blank=True)
    rc_number = models.CharField(max_length=50, null=True, blank=True)
    business_address = models.TextField(null=True, blank=True)
    cac_document = models.ImageField(null=True, blank=True)
    business_rejection_reason = models.TextField(null=True, blank=True)
    business_reviewed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="business_reviews"
    )
    business_reviewed_at = models.DateTimeField(null=True, blank=True)
    business_attempt_count = models.PositiveIntegerField(default=0)

    # --- timestamps ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "Verification Requests"

    def __str__(self):
        return f"{self.user.username} - verification"

    # --- document types that have expiry ---
    EXPIRY_REQUIRED = {"passport", "national_id", "drivers_license"}

    @property
    def has_document_expiry(self) -> bool:
        return self.id_type in self.EXPIRY_REQUIRED

    @property
    def identity_is_expired(self) -> bool:
        if not self.document_expiry_date:
            return False
        return self.document_expiry_date < timezone.now().date()

    @property
    def can_resubmit_identity(self) -> bool:
        return (
            self.identity_attempt_count < 5 and
            self.identity_status != "exhausted"
        )

    @property
    def can_resubmit_business(self) -> bool:
        return (
            self.business_attempt_count < 5 and
            self.business_status != "exhausted"
        )
        
        

        #session management
class UserSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name="sessions"
    )
    jti = models.CharField(max_length=255, unique=True)  # JWT ID — unique per token
    device = models.CharField(max_length=255, null=True)
    os = models.CharField(max_length=100, null=True)
    browser = models.CharField(max_length=100, null=True)
    ip_address = models.GenericIPAddressField(null=True)
    location = models.CharField(max_length=255, null=True)
    last_active = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "User Sessions"
        ordering = ["-last_active"]

    def __str__(self):
        return f"{self.user.username} - {self.device} - {self.ip_address}"

    
    def is_current(self, request_jti: str) -> bool:
        return self.jti == request_jti
    
    
    #2factor authentication

class TwoFactorSettings(models.Model):
    METHOD_CHOICES = (
        ("email", "Email OTP"),
        ("sms", "SMS OTP"),
        ("totp", "Authenticator App"),
    )

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="two_factor"
    )
    is_enabled = models.BooleanField(default=False)
    method = models.CharField(
        max_length=10,
        choices=METHOD_CHOICES,
        default="email"
    )
    totp_secret = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )  # encrypted, only for totp method
    backup_codes = models.JSONField(default=list)  # list of hashed codes
    backup_codes_viewed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "Two Factor Settings"

    def __str__(self):
        return f"{self.user.username} - 2FA ({self.method})"


class TrustedDevice(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="trusted_devices"
    )
    device_fingerprint = models.CharField(max_length=255)  # SHA256 hash
    device_label = models.CharField(max_length=255, null=True)
    ip_address = models.GenericIPAddressField(null=True)
    location = models.CharField(max_length=255, null=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "Trusted Devices"
        unique_together = ("user", "device_fingerprint")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.device_label}"

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at
    
#overall notification
class Notification(models.Model):
    TYPE_CHOICES = (
        ("report_action", "Report Action"),
        ("appeal_update", "Appeal Update"),
        ("verification", "Verification Update"),
        ("post_approved", "Post Approved"),
        ("post_rejected", "Post Rejected"),
        ("new_follower", "New Follower"),
        ("post_upvote", "Post Upvoted"),
        ("new_comment", "New Comment"),
        ("comment_reply", "Comment Reply"),
        ("new_review", "New Review"),
        ("account_warning", "Account Warning"),
        ("account_suspended", "Account Suspended"),
        ("two_fa", "2FA Alert"),
        ("system", "System"),
        ("group_invite","Group Invite"),
        ("accepted_group_invite","Accepted Group invite"),
        ("group_request_accepted","Group join request accepted"),
        ("new_group_member","New Group Member"),
        ("group_join_request","Group join request")
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="notifications"
    )
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    title = models.CharField(max_length=255)
    body = models.TextField()
    data = models.JSONField(default=dict)  # extra context — post id, report id etc
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "Notifications"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.recipient.username} - {self.notification_type}"
    
    
    

class NotificationPreferences(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="notifications_preferences"
    )
    new_message=models.BooleanField(default=True)
    product_approved=models.BooleanField(default=True)
    new_follower=models.BooleanField(default=True)
    product_rejected=models.BooleanField(default=True)
    product_upvote=models.BooleanField(default=True)
    new_comment=models.BooleanField(default=True)
    new_review=models.BooleanField(default=True)
    account_alerts=models.BooleanField(default=True)
    promotions=models.BooleanField(default=True)
    class Meta:
        verbose_name_plural = 'Notification preferences'
    def __str__(self):
        return self.user
class ProfileReport(models.Model):
    REASON_CHOICES = (
        ("Spam or scam", "Spam or scam"),
        ("Fake Account", "Fake Account"),
        ("Harassment", "Harassment"),
        ("Inappropriate Content", "Inappropriate Content"),
        ("Inappropriate Behavior","Inappropriate Behavior"),
        ("Impersonation", "Impersonation"),
        ("Other", "Other"),
    )

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("reviewed", "Reviewed"),
        ("dismissed", "Dismissed"),
    )

    ACTION_CHOICES = (
        ("none", "No Action"),
        ("warn", "Warning Issued"),
        ("suspend", "Account Suspended"),
        ("ban", "Account Banned"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reporter = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="reports_filed"
    )
    target = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="reports_received"
    )
    reason = models.CharField(max_length=1000, choices=REASON_CHOICES)
    description = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    action_taken = models.CharField(max_length=20, choices=ACTION_CHOICES, default="none")
    reviewed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="reports_reviewed"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "Profile Reports"
        unique_together = ("reporter", "target", "reason")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.reporter.username} reported {self.target.username} for {self.reason}"

    
class ProfileBlock(models.Model):
    REASON_CHOICES = (
        ("Spam or scam", "Spam or scam"),
        ("Fake Account", "Fake Account"),
        ("Harassment", "Harassment"),
        ("Inappropriate Content", "Inappropriate Content"),
        ("Inappropriate Behavior","Inappropriate Behavior"),
        ("Impersonation", "Impersonation"),
        ("Other", "Other"),
    )

    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    blocker = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="blocker"
    )
    target = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="blocker_target"
    )
    reason = models.CharField(max_length=1000, choices=REASON_CHOICES,null=True,blank=True)
    description = models.TextField(null=True, blank=True)
   
    
    blocked_at = models.DateTimeField(null=True, blank=True)
    unblocked_at= models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_invalidated=models.BooleanField(default=False)
    class Meta:
        db_table = "Profile Blocks"
        unique_together = ("blocker", "target", "reason")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.blocker.username} → {self.target.username}"


class ReportAppeal(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report = models.OneToOneField(
        ProfileReport,
        on_delete=models.CASCADE,
        related_name="appeal"
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="appeals"
    )
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    reviewed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="appeals_reviewed"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "Report Appeals"
        ordering = ["-created_at"]
        
        
        
class HelpCenter(models.Model):
    user=   models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="helprequests"
    )
    created_at=models.DateTimeField(auto_now_add=True)
    description=models.TextField()
    def __str__(self):
        return self.user
        





