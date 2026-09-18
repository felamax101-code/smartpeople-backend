from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from django.middleware.csrf import get_token
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

from feed.models import Post


from .throttles import(LoginThrottle,RegisterThrottle,ForgotPasswordThrottle,
                       OTPVerifyThrottle,ResendOTPThrottle,CheckEmailThrottle,ResetPasswordThrottle)
from .serializers import (
    RegisterSerializer, VerifyEmailSerializer, ResendSerializer,
    LoginSerializer, PasswordResetConfirmSerializer,
    UserSerializer, OtherUserSerializer,
    UpdateProfileSerializer, AvatarSerializer, AccountDeletionSerializer,
    ChangePasswordRequestSerializer, ChangePasswordConfirmSerializer,
    ChangeEmailRequestSerializer, ChangeEmailConfirmSerializer,PhoneAddSerializer,
    PhoneVerifySerializer,NotificationSerializer,ProfileReportSerializer,IdentityVerificationSerializer,
    VerificationStatusSerializer,BusinessVerificationSerializer,NotificationPreferencesSerializer
    )
from .utils import (parse_user_agent, get_ip_address, get_location_from_ip,
                    is_suspicious_login,set_phone_otp,get_jti_from_request, 
                    generate_2fa_otp, create_2fa_challenge,send_2fa_otp_email,
                    send_2fa_otp_sms,send_otp_email,generate_device_fingerprint,send_phone_otp_sms,send_account_delete_email)

from .session_service import terminate_session, terminate_all_sessions, terminate_other_sessions
from .permissions import IsAdminOrStaff
from .session_service import create_session
from django.utils import timezone
from .verification_service import (
    submit_identity, submit_business,
    review_identity, review_business,
    unlock_attempts
)
from .models import NotificationPreferences,VerificationRequest,ProfileReport, ReportAppeal,Notification,Follow,TwoFactorSettings,HelpCenter
from rest_framework.parsers import MultiPartParser,FormParser
from .Verification import Verification
from feed.pagination import CustomPagination
User = get_user_model()
from .models import LoginActivity,UserSession,TrustedDevice,ProfileBlock
from .tasks import send_suspicious_login_email ,notify_staff_new_verification
from Profile.models import ProfilePrivacy
#  Registration & Email Verification 
from django.conf import settings

from .two_factor_service import (
    initiate_setup, confirm_setup, disable_2fa,
    check_trusted_device, initiate_login_challenge,
    verify_login_challenge, resend_challenge,
    view_backup_codes)
from .report_service import (
    submit_report, review_report,
    dismiss_report, submit_appeal, review_appeal
)
from .sanitize import sanitize_plain
from authentication.notification_service import (
    mark_as_read, mark_all_as_read, get_unread_count
)
def set_auth_cookies(response,request,refresh_token):
    """Attach access and refresh JWTs as httpOnly cookies."""
    is_dev = settings.DEBUG #removed in postion

    response.set_cookie(
        'access_token',
        str(refresh_token.access_token),
        max_age=100 * 60,        
        httponly=True,
        secure=False,      
        samesite="Lax",
    )
    response.set_cookie(
        'refresh_token',
        str(refresh_token),
        max_age=7 * 24 * 60 * 60,  # matches REFRESH_TOKEN_LIFETIME
        httponly=True,
        secure=False,
        samesite="Lax",
    )
    response.set_cookie(
        "csrftoken",
        get_token(request),
        httponly=False,
        secure=False,
        samesite="Lax",
    )
    return response


class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes=[]
    throttle_classes=[RegisterThrottle]
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            RegisterThrottle().reset_on_success(request)
            user=serializer.save()
            refresh = RefreshToken.for_user(user)
            access = refresh.access_token
            is_mobile=request.headers.get("X-Client-Type")=="mobile"
            if is_mobile:
                
                response = Response({
                    "success":True,
                    "message": "registration successful",
                    "access_token":str(access),
                    "refresh_token":str(refresh),}, status=200)
            
            else:
                
                responseW=Response({ 
                "success": True,
                "message": "Login successful",
            
            },status=200)
                response=  set_auth_cookies(responseW,request,refresh)
            return response
        return Response({"error":serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

class VerifyEmailView(APIView):
    permission_classes = [AllowAny]
    throttle_classes=[OTPVerifyThrottle]
    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        if serializer.is_valid():
            OTPVerifyThrottle().reset_on_success(request)
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            access = refresh.access_token
            jti = str(access["jti"])
            # create session record
            create_session(user, request, jti)
            is_mobile=request.headers.get("X-Client-Type")=="mobile"
            if is_mobile:
                    response = Response({"success":True,
                    "message": "Login successful",
                    "access_token":str(access),
                    "refresh_token":str(refresh)}, status=200)
            
            else:
                responseW=Response({ 
                "success": True,
                "message": "Login successful",
            
                },status=200)
                response=  set_auth_cookies(responseW,request,refresh)
            return response
        
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

class ResendVerifyEmailView(APIView):
    permission_classes = [AllowAny]
    throttle_classes=[ResendOTPThrottle]
    def post(self, request):
        serializer = ResendSerializer(data=request.data)
        if serializer.is_valid():
            ResendOTPThrottle().reset_on_success(request)
            return Response({"detail": "OTP resent successfully."}, status=status.HTTP_200_OK)
       
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

#  Login  
class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes=[LoginThrottle]
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            LoginThrottle().reset_on_success(request)
            user = serializer.validated_data['user']
            ip = get_ip_address(request)
            ua = parse_user_agent(request)
            location = get_location_from_ip(ip)
            suspicious = is_suspicious_login(user, ip, location)
            tf = user.two_factor
            if tf.is_enabled:
            # trusted device? skip 2FA
                trusted=check_trusted_device(user, request)
                if trusted:
                    
                    pass  # fall through to normal session creation below
                else:
                # initiate 2FA challenge → return 202
                    result = initiate_login_challenge(user, request)
                    return Response({
                        "success": True,
                        "requires_2fa": True,
                        "temp_token": result["temp_token"],
                        "method": result["method"],
                        "message": result["message"]
                    }, status=202)  # 202 = authenticated but not complete
          
            LoginActivity.objects.create(
            user=user,
            ip_address=ip,
            device=ua["device"],
            os=ua["os"],
            browser=ua["browser"],
            location=location,
            was_suspicious=suspicious
        )

            if suspicious:
                send_suspicious_login_email.delay(
                    request.user.email,
                    request.user.username,
                    ip,
                    location,
                    ua["browser"],
                    ua["os"]
            )
                
            refresh = RefreshToken.for_user(user)
            access = refresh.access_token
            jti = str(access["jti"])
            # create session record
            create_session(user, request, jti)
            is_mobile=request.headers.get("X-Client-Type")=="mobile"
            if is_mobile:
                response = Response({
                    "success":True,
                    "message": "Login successful",
                    "access_token":str(access),
                    "refresh_token":str(refresh),
                    }, status=200)
            
            else:
                responseW=Response({ 
                "success": True,
                "message": "Login successful",
            
                },status=200)
                response=  set_auth_cookies(responseW,request,refresh)
            return response
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        
        

        
        


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        jti = get_jti_from_request(request)
        if jti:
            terminate_session(jti)
        response = Response({
            "success": True,
            "message": "Logged out successfully"
        }, status=200)
        return response

class LogoutAllView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        terminate_all_sessions(request.user)

        response = Response({
            "success": True,
            "message": "Logged out from all devices"
        }, status=200)
        return response


class LogoutOtherSessionsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Keeps current session, kills everything else"""
        try:
            jti = get_jti_from_request(request)
            if not jti:
                return Response({"error": "Could not identify current session"}, status=400)

            terminate_other_sessions(request.user, jti)
            return Response({
                "success": True,
             "message": "All other sessions terminated"
            }, status=200)
        except Exception as e:
            return Response({
                "success":False,
                "message":"Failed to terminated other sessions"
            },status=400)
        
class CustomRefreshView(APIView):
    permission_classes = [AllowAny]
    authentication_classes=[]

    def post(self, request):
        refresh_token=request.COOKIES.get("refresh_token")
        
        if not refresh_token:
            refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"error":"No refresh token provided"},status=401)
        try:
            
            refresh = RefreshToken(refresh_token)
            user_id=refresh["user_id"]
            user=User.objects.get(id=user_id)
            
            
            #invalidate the old session under the old tokens
            old_jti=str(refresh["jti"])
            terminate_session(old_jti)
            
            access=refresh.access_token
            new_jti = str(access["jti"])
            # create session record
            create_session(user, request, new_jti)
            is_mobile=request.headers.get("X-Client-Type")=="mobile"
            if is_mobile:
                
                response = Response({
                    "success":True,
                    "access_token":str(access),
                    "refresh_token":str(refresh),}, status=200)
            
            else:
                responseW=Response({ 
                "success": True,
                "client":"web"
                
            
                },status=200)
                response=  set_auth_cookies(responseW,request,refresh)
            return response 
        except Exception as e:
            return Response({"error": "Invalid or expired token."}, status=status.HTTP_401_UNAUTHORIZED)


#  Password Reset 
# 
class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]
    throttle_classes=[ForgotPasswordThrottle]
    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response({"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(email__iexact=email)
            with transaction.atomic():
                success, otp = Verification.generate_password_reset_otp(user.email)
                if success:
                    send_otp_email(user.email, otp, user.username)
                user.password_reset_otp = otp
                user.password_reset_otp_expiry = timezone.now() + timedelta(hours=1)
                user.save()
                
        except User.DoesNotExist:
            pass  
        return Response({"message": "If that email exists, a reset otp has been sent."}, status=status.HTTP_200_OK)


class ForgotPasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_classes=[ResetPasswordThrottle]
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            ResetPasswordThrottle().reset_on_success(request)
            user=serializer.save()
            response=Response({"valid": "True"}, status=status.HTTP_200_OK)
            refresh = RefreshToken.for_user(user)
            access = refresh.access_token
            is_mobile=request.headers.get("X-Client-Type")=="mobile"
            if is_mobile:
                
                response = Response({
                    "success":True,
                    "access_token":str(access),
                    "refresh_token":str(refresh),}, status=200)
            
            else:
                responseW=Response({ 
                "success": True,
                "message": "Login successful",
            
                },status=200)
                response=  set_auth_cookies(responseW,request,refresh)
            return response
        
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


#  Own Profile ─
class User2faStatusView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        try:
            user=request.user
            data=TwoFactorSettings.objects.get(user=user)
            is_enabled=data.is_enabled
            method=data.method
            return Response({
            "is_enabled":is_enabled,
            "method":method,
            },status.HTTP_200_OK)
        except Exception:
            return Response({
            "is_enabled":False,
            "method":"Email",
            },status.HTTP_200_OK)
class UserOwnView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        serializer = UpdateProfileSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            user = serializer.update_user()
            return Response(UserSerializer(user, context={"request": request}).data, status=status.HTTP_200_OK)
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        serializer = AccountDeletionSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.delete_account()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


#  Avatar 

class AvatarView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AvatarSerializer(data=request.FILES, context={"request": request})
        if serializer.is_valid():
            user = serializer.save_avatar()
            return Response({
                "avatar_url": request.build_absolute_uri(user.avatar.url)
            }, status=status.HTTP_200_OK)
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        user = request.user
        if user.avatar:
            user.avatar.delete(save=False)
            user.avatar = None
            user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


#  Account Actions ─
class DeactivateAccountView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        
        try:
            user = request.user
            user.is_deactivated = True
            user.save()
            posts=Post.objects.filter(owner=user).update(is_active=False)
            return Response({"message": "success"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error":"Requested process wasn't completed.please try again"}, status=status.HTTP_400_BAD_REQUEST)

#account deletion
class DeleteRequestAccountView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        
        try:
            user = request.user
            success,otp=Verification().generate_email_account_delete_otp(user.email)
            if success:
                send_otp_email(user.email, otp, user.username)
                return Response({"message": "success"}, status=status.HTTP_200_OK)
            return Response({"error":"Requested process wasn't completed.please try again"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response({"error":"Requested process wasn't completed.please try again"}, status=status.HTTP_400_BAD_REQUEST)

class DeleteConfirmAccountView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        
        try:
            serializer=AccountDeletionSerializer(data=request.data,context={"request": request})
            if serializer.is_valid:
                user=request.user
                send_account_delete_email(user.email, user.username)
                serializer.delete_account()
                return Response({"message": "success"}, status=status.HTTP_200_OK)
            return Response({"error":"Requested process wasn't completed.please try again"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error":"Requested process wasn't completed.please try again"}, status=status.HTTP_400_BAD_REQUEST)

#  Password Change ─

class ChangePasswordRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordRequestSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.send_otp()
            return Response({"success":True,"message": "OTP sent to your email."}, status=status.HTTP_200_OK)
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordConfirmView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordConfirmSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.apply_change()
            return Response({"message": "Password changed successfully."}, status=status.HTTP_200_OK)
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

class ChangeEmailRequestView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes=[CheckEmailThrottle]
    def post(self, request):
        serializer = ChangeEmailRequestSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            CheckEmailThrottle().reset_on_success(request)
            serializer.send_otp()
            return Response({"message": "OTP sent to your new email."}, status=status.HTTP_200_OK)
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class ChangeEmailConfirmView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangeEmailConfirmSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.apply_change()
            return Response({"message": "Email updated successfully."}, status=status.HTTP_200_OK)
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)




#check permissions to change usernem or email
class PermissionsCheckView(APIView):
    permission_classes = [AllowAny]
    def post (self ,request):
        user=request.user
        is_allowed_to_change_email=True
        is_allowed_to_change_username=True
        remaining_email_days=0
        remaining_username_days=0
        if user.last_email_change:
            days_since = (timezone.now() - user.last_email_change).days
            if days_since < 7:
                remaining_email_days= 7 - days_since
                is_allowed_to_change_email=False
        if user.last_username_change:
            days_since = (timezone.now() - user.last_email_change).days
            if days_since < 7:
                remaining_username_days = 7 - days_since
                is_allowed_to_change_username=False
        return Response({
            "is_allowed_to_change_email":is_allowed_to_change_email,
            "is_allowed_to_change_username":is_allowed_to_change_username,
            "remaining_email_days":remaining_email_days,
            "remaining_username_days":remaining_username_days,
            
        })
                
#  Other User Profile 
class OtherUserProfileView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, username):
        try:
            user = User.objects.get(username=username,is_deactivated=False)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        privacy = ProfilePrivacy.objects.get(user=user)
        is_following = False

        if request.user.is_authenticated:
            is_following = Follow.objects.filter(
                follower=request.user, 
                following=user
            ).exists()
            
        badge=user.verification_badge

        # build response respecting privacy settings
        data = {
            "id":user.id,
            "username": user.username,
            "name": user.name,
            "avatar": request.build_absolute_uri(user.avatar.url) if user.avatar else None,
            "role": user.role,
            "bio": user.bio,
            "total_posts": user.total_posts,
            "rating": user.rating,
            "reviews_count": user.reviews_count,
            "created_at": user.created_at,
            "is_following": is_following,
            "verification_level":user.verification_level,
            "verification_badge":{
                "label":badge.get("label"),
                "color":badge.get("color"),
                "icon":badge.get("icon")
            }}
        

        # gated fields
        if privacy.show_email:
            data["email"] = user.email

        if privacy.show_phone:
            data["phone"] = user.phone

        if privacy.show_location:
            data["location"] = user.location

        if privacy.show_followers:
            data["followers"] = user.followers

        if privacy.show_following:
            data["following"] = user.following

        if privacy.show_online_status:
            data["last_seen"] = user.last_seen  

        # who_can_follow enforcement — frontend uses this to show/hide follow button
        data["can_follow"] = (
            privacy.who_can_follow == "everyone" or
            (privacy.who_can_follow == "followers" and is_following)
        )

        # who_can_message enforcement
        data["can_message"] = (
            privacy.who_can_message == "everyone" or
            (privacy.who_can_message == "followers" and is_following)
        ) if request.user.is_authenticated else False
        return Response({
            "success": True,
            "data": data
        }, status=200)





#  Social Links 

class SocialLinkListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SocialLinkCreateSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            link = serializer.create_link()
            return Response(SocialLinkSerializer(link).data, status=status.HTTP_201_CREATED)
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class SocialLinkDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_link(self, pk, user):
        try:
            return SocialLink.objects.get(pk=pk, user=user)
        except SocialLink.DoesNotExist:
            return None

    def put(self, request, pk):
        link = self._get_link(pk, request.user)
        if not link:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = SocialLinkCreateSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            link.platform = serializer.validated_data['platform']
            link.name = serializer.validated_data['name']
            link.url = serializer.validated_data['url']
            link.save()
            return Response(SocialLinkSerializer(link).data, status=status.HTTP_200_OK)
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        link = self._get_link(pk, request.user)
        if not link:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        link.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


#  Mention Suggestions ─

class MentionSuggestionsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        q = request.query_params.get('q', '').strip()
        if not q:
            return Response({"results": []})
        users = User.objects.filter(
            username__istartswith=q, is_email_verified=True
        ).values('username', 'name')[:8]
        return Response({"results": list(users)}, status=status.HTTP_200_OK)


#  Email Check ─
class CheckEmailView(APIView):
    permission_classes = [AllowAny]

    BLOCKED_DOMAINS = {
        "tempmail.com", "mailinator.com", "10minutemail.com",
        "guerrillamail.com", "throwaway.email", "yopmail.com",
        "fakeinbox.com", "trashmail.com", "sharklasers.com",
    }

    def post(self, request):
        email = request.data.get("email", "")
        if not email:
            return Response({"valid": False, "reason": "Email is required."})
        domain = email.split("@")[-1].lower()
        if domain in self.BLOCKED_DOMAINS:
            return Response({"valid": False, "reason": "Disposable email addresses are not allowed."})
        return Response({"valid": True, "reason": ""})


#  Helper 




from django_ratelimit.exceptions import Ratelimited

def ratelimited_error(request,exception):
    return Response(
        {"error":"Too many attempts. Try again after sometime"
            
        },status=429
    )
    
    
class LoginActivityView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get current user's login history"""
        activities = LoginActivity.objects.filter(
            user=request.user
        ).order_by("-created_at")[:20]  # last 20 logins

        data = [{
            "id": str(a.id),
            "ip_address": a.ip_address,
            "device": a.device,
            "os": a.os,
            "browser": a.browser,
            "location": a.location,
            "was_suspicious": a.was_suspicious,
            "created_at": a.created_at
        } for a in activities]

        return Response({
            "success": True,
            "data": data
        }, status=200)

    def delete(self, request):
        """Clear login history"""
        LoginActivity.objects.filter(user=request.user).delete()
        return Response({
            "success": True,
            "message": "Login history cleared"
        }, status=200)
        
        








class PhoneAddView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Submit phone number → sends OTP"""
        serializer = PhoneAddSerializer(data=request.data,context={"request": request})
        if not serializer.is_valid():
            return Response({"error":serializer.errors}, status=400)

        phone = serializer.validated_data["phone"]  # already E.164
        otp =Verification().set_phone_otp(request.user, phone)

        # send OTP via Celery
        send_phone_otp_sms(phone, otp)

        return Response({
            "success": True,
            "message": f"OTP sent to {phone}",
        }, status=200)


class PhoneVerifyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Submit OTP → verifies phone"""
        serializer = PhoneVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        user = request.user
        otp = serializer.validated_data["otp"]

        # check OTP exists
        if not user.phone_otp:
            return Response({
                "error": "No OTP requested. Please request one first."
            }, status=400)

        # check expiry
        if timezone.now() > user.phone_otp_expiry:
          
            user.last_phone_change=timezone.now()
            user.save()
            return Response({"error": "OTP has expired. Please request a new one."}, status=400)

        # check match
        if user.phone_otp != otp:
           
            return Response({"error": "Invalid OTP"}, status=400)

        user.phone=user.new_phone
        user.last_phone_change=timezone.now()
        user.phone_verified = True
        user.phone_otp = None
        user.phone_otp_expiry = None
        user.save()

        return Response({
            "success": True,
            "message": "Phone number verified successfully"
        }, status=200)


class PhoneResendOTPView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        if not user.phone:
            return Response({
                "error": "No phone number on file. Please add one first."
            }, status=400)

        if user.phone_verified:
            return Response({
                "error": "Phone is already verified"
            }, status=400)

        # throttle resends — must wait 2 mins between requests
        if user.phone_otp_expiry:
            wait_until = user.phone_otp_expiry - timedelta(minutes=8)
            if timezone.now() < wait_until:
                return Response({
                    "error": "Please wait 2 minutes before requesting another OTP"
                }, status=429)

        otp = Verification().set_phone_otp(user, user.phone)
     
        send_phone_otp_sms(user.phone, otp)

        return Response({
            "success": True,
            "message": "OTP resent"
        }, status=200)
        


class VerificationSubmitView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """User checks their verification status"""
        try:
            vr = request.user.verification_request
            serializer = VerificationStatusSerializer(vr)
            return Response({
                "success": True,
                "verification_level": request.user.verification_level,
                "badge": request.user.verification_badge,
                "data": serializer.data
            }, status=200)
        except VerificationRequest.DoesNotExist:
            return Response({
                "success": True,
                "verification_level": request.user.verification_level,
                "badge": request.user.verification_badge,
                "data": None
            }, status=200)

    def post(self, request, section):
        """Submit identity or business verification"""

        if section == "identity":
            serializer = IdentityVerificationSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=400)

            d = serializer.validated_data
            result = submit_identity(
                user=request.user,
                id_type=d["id_type"],
                id_number=d["id_number"],
                id_front_url=d["id_front"],
                id_back_url=d.get("id_back"),
                selfie_url=d["selfie"],
                document_expiry_date=d.get("document_expiry_date"),
            )

        elif section == "business":
            serializer = BusinessVerificationSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=400)

            d = serializer.validated_data
            result = submit_business(
                user=request.user,
                business_name=d["business_name"],
                rc_number=d["rc_number"],
                business_address=d["business_address"],
                cac_document_url=d["cac_document"],
            )
        else:
            return Response({"error": "section must be identity or business"}, status=400)

        if not result["success"]:
            return Response({"error": result["error"]}, status=400)

        # notify staff via Celery
        notify_staff_new_verification.delay(
            request.user.username,
            section
        )

        return Response({
            "success": True,
            "message": "Verification submitted. Under review.",
            "attempts_remaining": result["attempts_remaining"]
        }, status=201)


class VerificationReviewView(APIView):
    permission_classes = [IsAdminOrStaff]

    def get(self, request):
        """Staff sees all pending verifications"""
        section = request.query_params.get("section", "identity")
        status = request.query_params.get("status", "pending")

        filter_kwargs = {}
        if section == "identity":
            filter_kwargs["identity_status"] = status
        elif section == "business":
            filter_kwargs["business_status"] = status

        vrs = VerificationRequest.objects.filter(
            **filter_kwargs
        ).select_related("user")

        paginator = CustomPagination()
        page = paginator.paginate_queryset(vrs, request)
        serializer = VerificationStatusSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request, user_id, section):
        """Staff approves or rejects a verification"""
        try:
            vr = VerificationRequest.objects.get(user__id=user_id)
        except VerificationRequest.DoesNotExist:
            return Response({"error": "Verification request not found"}, status=404)

        serializer = VerificationReviewSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        d = serializer.validated_data

        if section == "identity":
            result = review_identity(vr, d["action"], request.user, d.get("reason"))
        elif section == "business":
            result = review_business(vr, d["action"], request.user, d.get("reason"))
        else:
            return Response({"error": "section must be identity or business"}, status=400)

        if not result["success"]:
            return Response({"error": result["error"]}, status=400)

        # notify user via Celery
        notify_user_verification_result.delay(
            vr.user.email,
            vr.user.username,
            section,
            d["action"],
            d.get("reason")
        )

        return Response({
            "success": True,
            "message": f"{section} verification {d['action']}d"
        }, status=200)


class VerificationUnlockView(APIView):
    """Staff manually resets exhausted attempt counts"""
    permission_classes = [IsAdminOrStaff]

    def post(self, request, user_id, section):
        try:
            vr = VerificationRequest.objects.get(user__id=user_id)
        except VerificationRequest.DoesNotExist:
            return Response({"error": "Not found"}, status=404)

        result = unlock_attempts(vr, section)
        if not result["success"]:
            return Response({"error": result["error"]}, status=400)

        return Response(result, status=200)
    
    
    
class UserSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List all active sessions for current user"""
        current_jti = get_jti_from_request(request)
        sessions = request.user.sessions.all()

        data = [{
            "id": str(s.id),
            "device": s.device,
            "os": s.os,
            "browser": s.browser,
            "ip_address": s.ip_address,
            "location": s.location,
            "last_active": s.last_active,
            "created_at": s.created_at,
            "is_current": s.jti == current_jti,  # flags current device
        } for s in sessions]

        return Response({
            "success": True,
            "count": len(data),
            "data": data
        }, status=200)

    def delete(self, request, session_id):
        """Terminate a specific session"""
        try:
            session = UserSession.objects.get(
                id=session_id,
                user=request.user  # user can only delete their own sessions
            )
        except UserSession.DoesNotExist:
            return Response({"error": "Session not found"}, status=404)

        # prevent deleting current session from this endpoint
        current_jti = get_jti_from_request(request)
        if session.jti == current_jti:
            return Response({
                "error": "Use /logout/ to end your current session"
            }, status=400)

        session.delete()
        return Response({
            "success": True,
            "message": "Session terminated"
        }, status=200)
        
        

        
        

class TwoFactorSetupView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Step 1 — choose method and initiate setup"""
        method = request.data.get("method")
        
        if method not in ("email", "sms", "totp"):
            return Response({
                "error": "method must be email, sms or totp"
            }, status=400)

        result = initiate_setup(request.user, method)
        if not result["success"]:
            return Response({"error": result["error"]}, status=400)

        # for email/sms — send a setup confirmation OTP
        if method in ("email", "sms"):
           
            code = generate_2fa_otp()
            create_2fa_challenge(str(request.user.id), code, method)

            if method == "email":
                send_2fa_otp_email(
                    request.user.email,
                    request.user.username,
                    code
                )
            else:
                send_2fa_otp_sms(request.user.phone, code)

        return Response(result, status=200)


class TwoFactorConfirmSetupView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Step 2 — confirm setup with first code"""
        code = request.data.get("code")
        if not code:
            return Response({"error": "code is required"}, status=400)

        result = confirm_setup(request.user, code)
        
        if not result["success"]:
            return Response({"error": result["error"]}, status=400)

        return Response(result, status=200)


class TwoFactorDisableView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        code = request.data.get("code")
        if not code:
            return Response({"error": "Current 2FA code is required to disable"}, status=400)

        result = disable_2fa(request.user, code)
        if not result["success"]:
            return Response({"error": result["error"]}, status=400)

        return Response(result, status=200)


class TwoFactorVerifyView(APIView):
    """Called during login — user submits their 2FA code"""
    permission_classes = [AllowAny]

    def post(self, request):
        temp_token = request.data.get("temp_token")
        code = request.data.get("code")
        trust_device = request.data.get("trust_device", False)
        if not temp_token or not code:
            return Response({
                "error": "temp_token and code are required"
            }, status=400)

        result = verify_login_challenge(temp_token, code, request, trust_device)
        if not result["success"]:
            return Response({"error": result["error"]}, status=400)

        user = result["user"]

        # now create the full session — same as normal login
        from rest_framework_simplejwt.tokens import RefreshToken
        from .session_service import create_session

        refresh = RefreshToken.for_user(user)
        access = refresh.access_token
        jti = str(access["jti"])
        create_session(user, request, jti)
        
        response_data = {
            "success": True,
            "message": "Login successful",
            
        }

        if result["used_backup_code"]:
            response_data["warning"] = (
                f"Backup code used. {result['backup_codes_remaining']} remaining. "
                "Regenerate your codes soon."
            )
        is_mobile=request.headers.get("X-Client-Type")=="mobile"
        if is_mobile:
            
            response = Response({
                "success":True,
                    "message": "Login successful",
                    "access_token":str(access),
                    "refresh_token":str(refresh),}, status=200)
            
        else:
            responseW=Response({ 
            "success": True,
            "message": "Login successful",
            
        },status=200)
            response=  set_auth_cookies(responseW,request,refresh)
        return response


class TwoFactorResendView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        temp_token = request.data.get("temp_token")
       
        if not temp_token:
            return Response({"error": "temp_token is required"}, status=400)

        result = resend_challenge(temp_token)
        if not result["success"]:
            
            return Response({"error": result["error"]}, status=400)

        return Response(result, status=200)


class BackupCodesView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        """Regenerate backup codes — requires current 2FA code"""
        code = request.data.get("code")
        if not code:
            return Response({"error": "Current 2FA code is required"}, status=400)
        result = view_backup_codes(request.user, code)
        if not result["success"]:
            return Response({"error": result["error"]}, status=400)
        return Response(result, status=200)


class TrustedDeviceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List trusted devices"""
        devices = request.user.trusted_devices.filter(
            expires_at__gt=timezone.now()
        )
        data = [{
            "id": str(d.id),
            "device_label": d.device_label,
            "ip_address": d.ip_address,
            "location": d.location,
            "expires_at": d.expires_at,
            "created_at": d.created_at,
        } for d in devices]

        return Response({
            "success": True,
            "data": data
        }, status=200)

    def delete(self, request, device_id):
        """Remove a trusted device"""
        try:
            device = TrustedDevice.objects.get(
                id=device_id,
                user=request.user
            )
        except TrustedDevice.DoesNotExist:
            return Response({"error": "Device not found"}, status=404)

        device.delete()
        return Response({
            "success": True,
            "message": "Device removed. 2FA will be required on next login from this device."
        }, status=200)
        
        
 #register FCM token for notifications
class FCMTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.data.get("fcm_token")
        if not token:
            return Response({"error": "fcm_token is required"}, status=400)

        request.user.fcm_token = token
        request.user.fcm_token_updated_at = timezone.now()
        request.user.save()

        return Response({"success": True, "message": "Push token registered"}, status=200)
        




#report
class ProfileReporFromIdView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        try:
            target = User.objects.get(id=id)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)
        serializer = ProfileReportSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        result = submit_report(
            reporter=request.user,
            target=target,
            reason=serializer.validated_data["reason"],
            description=serializer.validated_data.get("description")
        )

        if not result["success"]:
            return Response({"error": result["error"]}, status=400)

        return Response(result, status=201)
class ProfileReportView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, username):
        try:
            target = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)
        serializer = ProfileReportSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        result = submit_report(
            reporter=request.user,
            target=target,
            reason=serializer.validated_data["reason"],
            description=serializer.validated_data.get("description")
        )

        if not result["success"]:
            return Response({"error": result["error"]}, status=400)

        return Response(result, status=201)
class ProfileBlockView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        try:
            target = User.objects.get(id=id)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)
        reason=request.data.get("reason")
        
        description=request.data.get("description")
        if reason and reason== "Other" and not description:
            return Response({"error":"Description is required when reason is 'other'"}, status=400)
        
        existing=ProfileBlock.objects.filter(
            target=target,
            blocker=request.user,
        ).first()
        if existing:
            if existing.is_invalidated==False:
                return Response({
                "error":"You have already blocked the user"}, status=400)
            existing.is_invalidated=False
            existing.save()
            return Response({
            "message":"success"}, status=201)

        if not existing:
            block=ProfileBlock.objects.create(
            target=target,
            blocker=request.user,
            reason=sanitize_plain(reason),
            description=sanitize_plain(description),
            blocked_at=timezone.now()
        )
        
        
        
        return Response({
            "message":"success"}, status=201)

    def delete(self,request,id):
        try:
            target = User.objects.get(id=id)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)
       
        block=ProfileBlock.objects.get(
            target=target,
            blocker=request.user,
        )
        if not block:
            return Response({
            "error":"You have not blocked the user"}, status=400)
        block.is_invalidated=True
        block.unblocked_at=timezone.now()
        block.save()
       
        return Response({
            "message":"success"}, status=201)
class AdminReportView(APIView):
    permission_classes = [IsAdminOrStaff]

    def get(self, request):
        status_filter = request.query_params.get("status", "pending")
        reports = ProfileReport.objects.filter(
            status=status_filter
        ).select_related("reporter", "target", "reviewed_by")

        paginator = CustomPagination()
        page = paginator.paginate_queryset(reports, request)
        serializer = ProfileReportSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request, report_id):
        try:
            report = ProfileReport.objects.get(id=report_id)
        except ProfileReport.DoesNotExist:
            return Response({"error": "Report not found"}, status=404)

        serializer = ReportReviewSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        action = serializer.validated_data["action"]

        if action == "dismiss":
            result = dismiss_report(report, request.user)
        else:
            result = review_report(report, action, request.user)

        if not result["success"]:
            return Response({"error": result["error"]}, status=400)

        return Response(result, status=200)


class AppealView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, report_id):
        try:
            report = ProfileReport.objects.get(id=report_id)
        except ProfileReport.DoesNotExist:
            return Response({"error": "Report not found"}, status=404)

        serializer = ReportAppealSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        result = submit_appeal(
            user=request.user,
            report=report,
            message=serializer.validated_data["message"]
        )

        if not result["success"]:
            return Response({"error": result["error"]}, status=400)

        return Response(result, status=201)


class AdminAppealView(APIView):
    permission_classes = [IsAdminOrStaff]

    def get(self, request):
        appeals = ReportAppeal.objects.filter(
            status="pending"
        ).select_related("user", "report", "reviewed_by")

        paginator = CustomPagination()
        page = paginator.paginate_queryset(appeals, request)
        serializer = ReportAppealSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request, appeal_id):
        try:
            appeal = ReportAppeal.objects.get(id=appeal_id)
        except ReportAppeal.DoesNotExist:
            return Response({"error": "Appeal not found"}, status=404)

        serializer = AppealReviewSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        result = review_appeal(appeal, serializer.validated_data["action"], request.user)
        if not result["success"]:
            return Response({"error": result["error"]}, status=400)

        return Response(result, status=200)



#notifications
class NotificationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List notifications with unread count"""
        notifications = Notification.objects.filter(
            recipient=request.user
        )
        # filter by read status if requested
        is_read = request.query_params.get("is_read")
        if is_read is not None:
            notifications = notifications.filter(is_read=is_read == "true")

        paginator = CustomPagination()
        page = paginator.paginate_queryset(notifications, request)
        serializer = NotificationSerializer(page, many=True)

        response = paginator.get_paginated_response(serializer.data)
        response.data["unread_count"] = get_unread_count(request.user)
        return response

    def patch(self, request, notification_id=None):
        """Mark one or all as read"""
        if notification_id:
            result = mark_as_read(request.user, str(notification_id))
            if not result["success"]:
                return Response({"error": result["error"]}, status=404)
            return Response({"success": True}, status=200)

        mark_all_as_read(request.user)
        return Response({"success": True, "message": "All notifications marked as read"}, status=200)

    def delete(self, request, notification_id=None):
        """Delete one or all notifications"""
        if notification_id:
            try:
                Notification.objects.get(
                    id=notification_id,
                    recipient=request.user
                ).delete()
            except Notification.DoesNotExist:
                return Response({"error": "Notification not found"}, status=404)
            return Response({"success": True}, status=200)

        Notification.objects.filter(recipient=request.user).delete()
        return Response({"success": True, "message": "All notifications cleared"}, status=200)
        
        
        

        
 









from .upload import upload_verification_document, upload_selfie

class VerificationSubmitView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]  # accept file uploads

    def get(self, request):
        """User checks their verification status"""
        try:
            vr = request.user.verification_request
            serializer = VerificationStatusSerializer(vr)
            return Response({
                "success": True,
                "verification_level": request.user.verification_level,
                "badge": request.user.verification_badge,
                "data": serializer.data
            }, status=200)
        except VerificationRequest.DoesNotExist:
            return Response({
                "success": True,
                "verification_level": request.user.verification_level,
                "badge": request.user.verification_badge,
                "data": None
            }, status=200)

    def post(self, request, section):
        if section == "identity":
            serializer = IdentityVerificationSerializer(data=request.data)
            if not serializer.is_valid():
              
                return Response(serializer.errors, status=400)

            d = serializer.validated_data

            try:
                # upload files to Cloudinary server-side
                id_front_url = upload_verification_document(d["id_front"])
                selfie_url = upload_selfie(d["selfie"])
                id_back_url = None
                if d.get("id_back"):
                    id_back_url = upload_verification_document(d["id_back"])
            except Exception as e:
               
                return Response({
                    "error": "File upload failed. Please try again."
                }, status=500)
           
            result = submit_identity(
                user=request.user,
                id_type=d["id_type"],
                id_number=d["id_number"],
                id_front_url=id_front_url,
                id_back_url=id_back_url,
                selfie_url=selfie_url,
                document_expiry_date=d.get("document_expiry_date"),
            )

        elif section == "business":
            serializer = BusinessVerificationSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=400)

            d = serializer.validated_data

            try:
                cac_url = upload_verification_document(
                    d["cac_document"],
                    folder="marketplace/verification/business"
                )
            except Exception:
                return Response({
                    "error": "File upload failed. Please try again."
                }, status=500)

            result = submit_business(
                user=request.user,
                business_name=d["business_name"],
                rc_number=d["rc_number"],
                business_address=d["business_address"],
                cac_document_url=cac_url,
            )
        else:
            return Response({"error": "section must be identity or business"}, status=400)

        if not result["success"]:
            return Response({"error": result["error"]}, status=400)

        notify_staff_new_verification(
            request.user.username,
            section
        )

        return Response({
            "success": True,
            "message": "Verification submitted successfully. Under review.",
            "attempts_remaining": result["attempts_remaining"]
        }, status=201)
        
        
        
        
        
        
class NotificationUnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
        return Response({"unread_count": count}, status=200)
        
        


# allowed MIME types — same rules as before
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024   # 5MB

import uuid
class UploadGroupAvatar(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]  # accept file uploads
    def post(self,request):
        """
    Generic image upload endpoint.
    Accepts a multipart file, validates it, saves it via DEFAULT_FILE_STORAGE,
    and returns the full URL.

    DEFAULT_FILE_STORAGE in settings.py handles where the file actually goes —
    Cloudinary, S3, local media — 

    
    """
        file = request.FILES.get("file")

        if not file:
            return Response(
            {"detail": "No file provided."},
            status=status.HTTP_400_BAD_REQUEST
        )

    #  validate content type ─
        if file.content_type not in ALLOWED_TYPES:
            return Response(
            {"detail": f"File type '{file.content_type}' not allowed. Use JPEG, PNG, or WebP."},
            status=status.HTTP_400_BAD_REQUEST
        )

    #  validate file size 
        if file.size > MAX_FILE_SIZE:
            return Response(
            {"detail": f"File too large. Maximum is 5MB, received {file.size / 1024 / 1024:.1f}MB."},
            status=status.HTTP_400_BAD_REQUEST
        )

    #  validate actual file bytes (magic bytes check) 
    # Read the first 12 bytes to verify the file signature
        header = file.read(12)
        file.seek(0)   # reset so DEFAULT_FILE_STORAGE reads the full file

        if not _is_valid_image_bytes(header):
            return Response(
            {"detail": "File content does not match a valid image format."},
            status=status.HTTP_400_BAD_REQUEST
        )

    #  save via DEFAULT_FILE_STORAGE ─
    # Use a UUID filename to avoid collisions and prevent filename enumeration.
    # default_storage.save() routes to whatever backend is configured:
    #   Cloudinary → uploads to Cloudinary, stores public_id
    #   S3         → uploads to S3 bucket, stores key
    #   Local      → saves to MEDIA_ROOT, stores relative path
        extension = _get_extension(file.content_type)
        filename = f"messaging/{uuid.uuid4().hex}{extension}"

        saved_path = default_storage.save(filename, ContentFile(file.read()))

    # .url() converts the stored path to a full accessible URL —
    # this is the same mechanism that user avatar .url uses
        full_url = default_storage.url(saved_path)

        return Response({"url": full_url}, status=status.HTTP_201_CREATED)


#  helpers ─

def _is_valid_image_bytes(header: bytes) -> bool:
    """Check file magic bytes to verify it's actually an image."""
    if header[:3] == b"\xff\xd8\xff":
        return True   # JPEG
    if header[:8] == b"\x89PNG\r\n\x1a\n":
        return True   # PNG
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return True   # WebP
    return False


def _get_extension(content_type: str) -> str:
    """Map MIME type to file extension."""
    return {
        "image/jpeg": ".jpg",
        "image/png":  ".png",
        "image/webp": ".webp",
    }.get(content_type, ".jpg")
    
class NotificationPreferencesView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        user=request.user
        preference=NotificationPreferences.objects.filter(user=user).first()
        if not preference:
            preference=NotificationPreferences.objects.create(user=user)
        serializer=NotificationPreferencesSerializer(preference)
        return Response(serializer.data,status=200)
    def patch(self,request):
        preference=NotificationPreferences.objects.get(user=request.user)
        serializer=NotificationPreferencesSerializer(preference,data=request.data,partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data,status=200)
        return Response(serializer.errors,status=400)

class HelpCenterView(APIView):
    permission_classes = [IsAuthenticated]
    def post (self,request):
        description=request.data.get("description")
        try:
            HelpCenter.objects.create(user=request.user,description=description)
            return Response(status=200)
        except Exception:
            return Response(status=400)