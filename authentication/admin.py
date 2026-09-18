from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import( CustomUser,Contacts,Follow,LoginActivity,
                    VerificationRequest,UserSession,Notification,LoginActivity,TwoFactorSettings,TrustedDevice,
                    ProfileReport,ReportAppeal,ProfileBlock,LoginActivity,HelpCenter
                    )


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['email', 'username', 'name', 'role', 'is_email_verified', 'is_deactivated']
    list_filter = ['role', 'is_email_verified', 'is_deactivated', 'is_staff']
    search_fields = ['email', 'username', 'name']
    ordering = ['-created_at']
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal', {'fields': ('username', 'name', 'avatar',"bio","phone")}),
        ('Status', {'fields': ('role', 'is_email_verified', "phone_verified",'is_deactivated',"is_active", 'is_locked', 'is_staff', 'is_superuser',"last_email_change","last_phone_change")}),
        ('Counts', {'fields': ("followers","following","total_posts","reviews_count","rating")}),
        ('OTP / Reset', {'fields': ("new_email",'email_otp', 'email_otp_expiry', 'password_change_otp', 'password_change_expiry', 'password_reset_otp', 'password_reset_otp_expiry',"new_phone","phone_otp","phone_otp_expiry","account_delete_email_otp","account_delete_email_otp_expiry")}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('email', 'username', 'password1', 'password2')}),
    )


@admin.register(VerificationRequest)
class VerificationRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'identity_status', 'business_status']
    list_filter = ['identity_status', 'business_status']
    search_fields = ['user__username']
    ordering = ['-created_at']
    
@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'last_active','device', 'os',"browser"]
    ordering = ['-created_at']
    list_filter = ['user__username']
    search_fields = ['user__username']
    
    
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'title']
    ordering = ['-created_at']
    search_fields = ['recipient__username',"was_suspicious"]
    list_filter = ['recipient__username']
    
    
@admin.register(LoginActivity)
class LoginActivityAdmin(admin.ModelAdmin):
    list_display = ['user', 'was_suspicious']
    ordering = ['-created_at']
    search_fields = ['user__username',"was_suspicious"]
    list_filter = ['user__username']
    
    
    
@admin.register(TwoFactorSettings)
class TwoFactorSettingsAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_enabled']
    ordering = ['-created_at']
    search_fields = ['user__username',"is_enabled"]
    list_filter = ['user__username']
    
@admin.register(TrustedDevice)
class TrustedDeviceAdmin(admin.ModelAdmin):
    list_display = ['user', 'device_label']
    ordering = ['-created_at']
    search_fields = ['user__username']
    list_filter = ['user__username']
    
    


@admin.register(ProfileReport)
class ProfileReportAdmin(admin.ModelAdmin):
    list_display = ['reporter', 'target']
    ordering = ['-created_at']
    search_fields = ['reporter__username', 'target__username']
    filter_fields=["status"]
    
@admin.register(ReportAppeal)
class ReportAppealAdmin(admin.ModelAdmin):
    list_display = ['user', 'status',"reviewed_by"]
    ordering = ['-created_at']
    search_fields = ['user__username', 'reviewed_by']
    filter_fields=["reviewed_by","status"]
    
    
    
    
@admin.register(ProfileBlock)
class ReportAppealAdmin(admin.ModelAdmin):
    list_display = ['blocker', 'target']
    ordering = ['-created_at']
    search_fields = ['blocker__username', 'target__username']
    
@admin.register(HelpCenter)
class HelpCenterAdmin(admin.ModelAdmin):
    list_display = ['user']
    ordering = ['-created_at']
    search_fields = ['user__username']
    
 
