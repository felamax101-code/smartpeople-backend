from django.apps import AppConfig


class RealestateConfig(AppConfig):
    name = 'realestate'

    def ready(self):
        import realestate.signals