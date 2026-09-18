from django.apps import AppConfig


class FeedConfig(AppConfig):
    default_auto_fields="django.db.models.BigAutoFields"
    name = 'feed'
    def ready(self):
        import feed.signals
