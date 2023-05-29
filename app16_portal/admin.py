from django.contrib import admin

from app16_portal.models import PortalProfile, Group, Site
from app1_base.admin import AlwaysChangedModelForm
from app1_base.models import Profile
from app4_ehpad_base.models import ProfileSerenicia


class ProfileAdmin(admin.StackedInline):
    model = Profile
    fields = ('phone_number', 'civility', 'photo', 'adress', 'cp', 'city')
    form = AlwaysChangedModelForm


class ProfileSereniciaAdmin(admin.StackedInline):
    model = ProfileSerenicia
    fields = ('birth_date',)
    form = AlwaysChangedModelForm


@admin.register(PortalProfile)
class PortalProfileAdmin(admin.ModelAdmin):
    fields = ('first_name', 'last_name', 'email', 'key', 'site_group', 'linked_sites')
    readonly_fields = ('groups', 'date_joined', 'site_group', 'key')
    list_display = ('last_name', 'first_name')
    inlines = [ProfileAdmin, ProfileSereniciaAdmin]


admin.site.register(Site)
admin.site.register(Group)
