from django.apps import AppConfig


class GroupsConfig(AppConfig):
    default_auto_fields="django.db.models.BigAutoFields"
    name = 'groups'

    def ready(self):
        import groups.signals