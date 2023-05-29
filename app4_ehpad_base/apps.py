from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class App4Config(AppConfig):
    name = 'app4_ehpad_base'
    verbose_name = _("Serenicia Config")

    def ready(self):
        import app4_ehpad_base.signals
