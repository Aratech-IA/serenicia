from __future__ import unicode_literals

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class App1Config(AppConfig):
    name = 'app1_base'
    verbose_name = _("Base Config")

