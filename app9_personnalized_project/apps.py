from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class App9Config(AppConfig):
    name = 'app9_personnalized_project'
    verbose_name = _('Support project')

    def ready(self):
        import app9_personnalized_project.signals
