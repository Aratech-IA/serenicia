from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class App10Config(AppConfig):
    name = 'app10_social_activities'
    verbose_name = _('Social life')

    def ready(self):
        import app10_social_activities.signals
