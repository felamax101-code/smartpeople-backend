
from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    default_auto_fields="django.db.models.BigAutoFields"
    name = 'authentication'
    def ready(self):
        import authentication.signals




