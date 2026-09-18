from django.urls import path,include
from .views import (
    RegisterView, VerifyEmailView, ResendVerifyEmailView,
    LoginView, LogoutView, LogoutAllView, CustomRefreshView,
    ForgotPasswordView, ForgotPasswordResetConfirmView,
    UserOwnView, AvatarView, DeactivateAccountView,
    ChangePasswordRequestView, ChangePasswordConfirmView,
    ChangeEmailRequestView, ChangeEmailConfirmView,
    OtherUserProfileView,
    SocialLinkListCreateView, SocialLinkDetailView,
    MentionSuggestionsView, CheckEmailView,LoginActivityView,
    PhoneAddView,VerificationSubmitView,VerificationReviewView,
    VerificationUnlockView,PhoneVerifyView,PhoneResendOTPView,
    UserSessionView,TwoFactorSetupView,TwoFactorConfirmSetupView,
    TwoFactorDisableView,TwoFactorVerifyView,
    TwoFactorResendView,BackupCodesView,TrustedDeviceView,LogoutOtherSessionsView,ProfileReporFromIdView,
    FCMTokenView,ProfileReportView,AdminReportView,AppealView,AdminAppealView,
    NotificationView,User2faStatusView,NotificationUnreadCountView,ProfileBlockView,PermissionsCheckView,UploadGroupAvatar,
    DeleteConfirmAccountView,DeleteRequestAccountView,NotificationPreferencesView,HelpCenterView
)

urlpatterns = [
    # Registration & verification
    path("register/", RegisterView.as_view(), name="register"),
    path("verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path("resend-verification/", ResendVerifyEmailView.as_view(), name="resend-otp"),

    # Login / logout
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("logout-all/", LogoutAllView.as_view(), name="logout-all"),
    path("auth/logout-others/", LogoutOtherSessionsView.as_view(), name="logout-others"),
    path("token/refresh/", CustomRefreshView.as_view(), name="token-refresh"),

    # Password reset
    path("password/reset/", ForgotPasswordView.as_view(), name="forgot-password"),
    path("password/reset/confirm/", ForgotPasswordResetConfirmView.as_view(), name="reset-password"),

    # Own profile
    path("users/me/2fa-status/", User2faStatusView.as_view(), name="2fa-status"),
    path("users/me/", UserOwnView.as_view(), name="own-profile"),
    path("users/me/avatar/", AvatarView.as_view(), name="avatar"),
    
    #deactivate accout
    path("users/me/deactivate/", DeactivateAccountView.as_view(), name="deactivate-account"),

    #delete account
    path("users/me/account-delete/request/", DeleteRequestAccountView.as_view(), name="delete-account-request"),
    path("users/me/account-delete/confirm/", DeleteConfirmAccountView.as_view(), name="delete-account-confirm"),
    
    
    #block
    path("block/<uuid:id>/",ProfileBlockView.as_view(),name="block-user"),
    # Password & email change
    path("users/me/change-password/", ChangePasswordRequestView.as_view(), name="change-password"),
    path("users/me/change-password/confirm/", ChangePasswordConfirmView.as_view(), name="change-password-confirm"),
    path("users/me/change-email/", ChangeEmailRequestView.as_view(), name="change-email"),
    path("users/me/change-email/confirm/", ChangeEmailConfirmView.as_view(), name="change-email-confirm"),
    # Social links
    path("users/me/social-links/", SocialLinkListCreateView.as_view(), name="social-links"),
    path("users/me/social-links/<int:pk>/", SocialLinkDetailView.as_view(), name="social-link-detail"),

    # Other users
    path("users/<str:username>/", OtherUserProfileView.as_view(), name="other-profile"),
   
    #check email/username change permissions
    path("users/me/permissions/", PermissionsCheckView.as_view(), name="mentions"),
    
    # Utils
    path("users/mentions/", MentionSuggestionsView.as_view(), name="mentions"),
    path("check-email/", CheckEmailView.as_view(), name="check-email"),
    
    path("users/me/login-activity/", LoginActivityView.as_view(), name="login-activity"),


    #phone number
    path("users/me/phone/", PhoneAddView.as_view(), name="phone-add"),
    path("users/me/phone/verify/", PhoneVerifyView.as_view(), name="phone-verify"),
    path("users/me/phone/resend/", PhoneResendOTPView.as_view(), name="phone-resend"),
    
    
    # user facing
    path("users/me/verification/", VerificationSubmitView.as_view(), name="verification-status"),
    path ("users/me/verification/<str:section>/", VerificationSubmitView.as_view(), name="verification-submit"),

    # staff facing
    path("admin/verifications/", VerificationReviewView.as_view(), name="verification-list"),
    path("admin/verifications/<uuid:user_id>/<str:section>/", VerificationReviewView.as_view(), name="verification-review"),
    path("admin/verifications/<uuid:user_id>/<str:section>/unlock/", VerificationUnlockView.as_view(), name="verification-unlock"),

    path("users/me/sessions/", UserSessionView.as_view(), name="sessions-list"),
    path("users/me/sessions/<uuid:session_id>/", UserSessionView.as_view(), name="session-terminate"),
    

    # setup
    path("auth/2fa/setup/", TwoFactorSetupView.as_view(), name="2fa-setup"),
    path("auth/2fa/setup/confirm/", TwoFactorConfirmSetupView.as_view(), name="2fa-setup-confirm"),
    path("2fa/disable/", TwoFactorDisableView.as_view(), name="2fa-disable"),

    # login flow with 2fa
    path("2fa/verify/", TwoFactorVerifyView.as_view(), name="2fa-verify"),
    path("2fa/resend/", TwoFactorResendView.as_view(), name="2fa-resend"),

    # backup codes
    path("2fa/backup-codes/", BackupCodesView.as_view(), name="2fa-backup-codes"),
    
    # trusted devices
    path("2fa/trusted-devices/", TrustedDeviceView.as_view(), name="2fa-trusted-devices"),
    path("2fa/trusted-devices/<uuid:device_id>/", TrustedDeviceView.as_view(), name="2fa-trusted-device-remove"),
    
    
    
    #fcm register for notificaton
    path("users/me/fcm-token/", FCMTokenView.as_view(), name="fcm-token"),
    
    path("users/<str:username>/report/", ProfileReportView.as_view(), name="profile-report"),
    path("admin/reports/", AdminReportView.as_view(), name="admin-reports"),
    path("admin/reports/<uuid:report_id>/", AdminReportView.as_view(), name="admin-report-review"),

    # appeals
    path("users/byid/<uuid:id>/report/", ProfileReporFromIdView.as_view(), name="profile-report"),
    path("users/me/appeals/<uuid:report_id>/", AppealView.as_view(), name="submit-appeal"),
    path("admin/appeals/", AdminAppealView.as_view(), name="admin-appeals"),
    path("admin/appeals/<uuid:appeal_id>/", AdminAppealView.as_view(), name="admin-appeal-review"),

    # notifications
    path("notifications/", NotificationView.as_view(), name="notifications"),
    path("notifications/<uuid:notification_id>/", NotificationView.as_view(), name="notification-detail"),
    
    
    #polled unread count
    path("notifications/unread-count/", NotificationUnreadCountView.as_view()),
    
    
    #group avatar upload
    path("api/upload/",UploadGroupAvatar.as_view(),name="upload-group-avatar"),

    path("preference/notifications/",NotificationPreferencesView.as_view(),name="view-update-notificatiopreference"),
    path("help/",HelpCenterView.as_view(),name="HelpCenterView")

]

