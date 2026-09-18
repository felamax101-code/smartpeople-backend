from django.http import JsonResponse
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError
from .session_service import is_valid_session, refresh_session
import re 
from django.urls import resolve,Resolver404
# paths that don't need session validation
EXEMPT_PATHS = {
    "/api/categories/",
    "/api/feed/",
    "/api/login/",
    "/api/register/",
    "/api/token/refresh/",
    "/api/password/reset/",
    "/api/verify-email/",
    "/api/2fa/verify/",
    "/api/2fa/resend/",
    "/api/verify-email/",
    "/api/resend-verification/",
}

class SessionValidationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # skip exempt paths
        self.admin_pattern=re.compile(r"^/admin/")
        self.media_pattern=re.compile(r"/media/")
        match=resolve(request.path)
        self.skip_auth_paths=[
            "/post/<slug:slug>/","/post/<str:slug>/comments/"
        ]
        if request.method=="GET" and match.url_name in ("lget-reviews","create-comment","get-create/edit/delete-post","other-profile","view-replies"):
            return self.get_response(request)
        if request.path in EXEMPT_PATHS or self.admin_pattern.match(request.path) or  self.media_pattern.match(request.path):
            return self.get_response(request)

        access_token = request.COOKIES.get('access_token')
        if not access_token:
            auth_header=request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer"):
                access_token=auth_header.split(" ")[1]

                if access_token:
                    try:
                        decoded = AccessToken(access_token)
                        jti = str(decoded["jti"])

                # session deleted? → reject immediately
                        if not is_valid_session(jti):
                            return JsonResponse(
                        {"error": "Session expired. Please log in again. tttttt"},
                        status=401
                    )

                # valid → refresh last_active timestamp
                        refresh_session(jti)

                    except TokenError:
                        pass  # let DRF handle invalid tokens normally

        return self.get_response(request)