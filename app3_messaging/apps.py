from django.apps import AppConfig


class App3Config(AppConfig):
    name = 'app3_messaging'

    def ready(self):
        import app3_messaging.signals