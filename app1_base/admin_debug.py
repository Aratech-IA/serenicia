from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.contrib import admin
from django.apps import apps

# --------------------------------------------------------------------------------------
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<< ADMIN FOR DEBUG  >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# --------------------------------------------------------------------------------------

models = apps.get_models()


class SereniciaAdminDebug(admin.AdminSite):
    site_header = "Serenicia DEBUG ADMIN"


def has_superuser_permission(request):
    return request.user.is_active and request.user.is_superuser


admin_debug = SereniciaAdminDebug(name='sereniciaDebug')
admin_debug.has_permission = has_superuser_permission
admin_debug.register(User, UserAdmin)


for model in models:
    try:
        admin_debug.register(model)
    except admin.sites.AlreadyRegistered:
        pass

