from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError   
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings


class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        access_token = request.COOKIES.get('access_token')
        if not access_token:
            auth_header=request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer"):
                access_token=auth_header.split(" ")[1]
                print("access_token",access_token)
        if not access_token:
            return None
        try:
            validated = self.get_validated_token(access_token)
            return self.get_user(validated), validated
        except (InvalidToken, TokenError) as e:
            print(e)
            raise AuthenticationFailed(str(e))
        
        
        
        
        
