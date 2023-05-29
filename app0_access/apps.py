from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class App0Config(AppConfig):
    name = 'app0_access'
    verbose_name = _("App access Config")

    def ready(self):
        import app0_access.signals
