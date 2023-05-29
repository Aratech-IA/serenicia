from django.contrib.admin import AdminSite

from .models import Image, Config

class MyAdminSite(AdminSite):
    site_header = 'training'

admin_site = MyAdminSite(name='myadmin')
admin_site.register(Image)
admin_site.register(Config)