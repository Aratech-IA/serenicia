from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class PortalConfig(AppConfig):
    name = 'app16_portal'
    verbose_name = _('Login portal')

    def ready(self):
        import app16_portal.signals