##    --------------------- !!!!!!!!!!!!!!!!!!! -----------------------------
# THIS FILE IS UNUSED BUT KEEP FOR TRACE OF HOW TO BUILD REVERSE URL IN ADMIN
# reverse('proteciaAdmin:app1_customuser_change',)
# THIS PART IS REALLY BAD SUPPORT ON DOCUMENTATION

from django.forms.models import ModelForm
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.admin import UserAdmin
from django.contrib import admin
from django.contrib.auth.models import User, Group, Permission
from django.utils.html import format_html
from app4_ehpad_base.models import  ProfileSerenicia
from app1_base.models import Client, CustomUser, Profile
from django.utils.translation import gettext_lazy as _

from .models import Client, Camera, Result, Object, Profile, Alert, Alert_when, Alert_type, Telegram


from django.utils.safestring import mark_safe
from django.urls import reverse

# --------------------------------------------------------------------------------------
# <<<<<<<<<<<<<<<<<< ADMIN FOR THE SUPERADMINISTRATEUR  >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# --------------------------------------------------------------------------------------




class AlwaysChangedModelForm(ModelForm):
    def has_changed(self, *args, **kwargs):
        if self.instance.pk is None:
            return True
        return super(AlwaysChangedModelForm, self).has_changed(*args, **kwargs)


@receiver(post_save, sender=User)
def add_group_permission(sender, instance, created, **kwargs):
    if created:
        g = Group.objects.get(name='normal')
        g.user_set.add(instance)


class ProfileInline(admin.StackedInline):
    # add_fieldsets = ((None, {'fields': ('client','phone_number', 'language'),}),)
    readonly_fields = ('telegram_token', 'reboot_protecia_box')
    exclude = ('alert',)
    model = Profile
    form = AlwaysChangedModelForm
    can_delete = False
    # filter_horizontal = ['phone_number',]  # example: ['tlf', 'country',...]
    verbose_name_plural = 'profiles'
    fk_name = 'user'

    def get_readonly_fields(self, request, obj=None):
        fields = self.readonly_fields
        if request.user.is_superuser:
            fields += ('send_mail_url',)
            if obj:
                fields += ('client', 'created_by')
        else:
            fields += ('client',)
        return fields

    def get_fieldsets(self, request, obj=None):
        if not obj:
            if request.user.is_superuser:
                self.add_fieldsets = ((None, {'fields': ('client', 'phone_number', 'language', 'tracking_number',
                                                         'tracking_site'), }),)
                return self.add_fieldsets
            else:
                self.add_fieldsets = ((None, {'fields': ('phone_number', 'language'), }),)
                return self.add_fieldsets
        else:
            return super(ProfileInline, self).get_fieldsets(request, obj=None)

    def get_exclude(self, request, obj=None):
        excluded = super().get_exclude(request, obj) or []  # get overall excluded fields

        if not request.user.is_superuser:  # if user is not a superuser
            return excluded + ('tracking_number', 'tracking_site', 'created_by')

        return excluded  # otherwise return the default excluded fields if any

    def send_mail_url(self, obj):
        return format_html("<a href='{url}'>SEND RESET PASSWORD MAIL</a>", url="/mail/reset/" + str(obj.id))

    def reboot_protecia_box(self, obj):
        return format_html("<a href='{url}'>REBOOT PROTECIA BOX</a>", url="/reboot/" + str(obj.id))


class ProfileSereniciaInline(admin.StackedInline):
    model = ProfileSerenicia
    form = AlwaysChangedModelForm
    can_delete = False
    verbose_name_plural = 'profiles Serenicia'
    #fk_name = 'profile'


class SuperUserAdmin(UserAdmin):
    search_fields = ('last_name', 'first_name', 'username')
    list_display = ('username', 'email', 'first_name', 'last_name',)
    list_filter = ('is_active', 'is_staff', 'groups')
    ordering = ('last_name',)
    add_fieldsets = ((None, {'fields': ('username', 'password1', 'password2', 'first_name', 'last_name', 'email'), }),)
    inlines = [ProfileInline, ProfileSereniciaInline ]

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets

        if request.user.is_superuser:
            perm_fields = ('is_active', 'is_staff', 'is_superuser',
                           'groups', 'user_permissions')
        else:
            # modify these to suit the fields you want your
            # staff user to be able to edit
            perm_fields = ('is_active',)

        return [(None, {'fields': ('username', 'password')}),
                (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
                (_('Permissions'), {'fields': perm_fields}),
                (_('Important dates'), {'fields': ('last_login', 'date_joined')})]

    def get_readonly_fields(self, request, obj=None):
        fields = self.readonly_fields
        if not request.user.is_superuser:
            fields += ('last_login', 'date_joined',)
        return fields

    def get_queryset(self, request):
        qs = super(UserAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(profile__client=Profile.objects.get(user=request.user).client)

    def save_formset(self, request, form, formset, change):
        if not request.user.is_superuser:
            instances = formset.save(commit=False)
            for instance in instances:
                instance.client = Profile.objects.get(user=request.user).client
                instance.created_by = 'user'
                instance.save()
            formset.save_m2m()
        else:
            super(SuperUserAdmin, self).save_formset(request, form, formset, change)


class UserInline(admin.StackedInline):
    model = User
    # fk_name = 'user'
    # form = AlwaysChangedModelForm
    # can_delete = False
    # verbose_name_plural = 'profiles Serenicia'


class ProfileAdmin(admin.ModelAdmin):
    readonly_fields = ('email_0',)
    # inlines = [UserInline, ]


class AlertTypeInline(admin.TabularInline):
    model = Alert_type

class ProfileInline2(admin.TabularInline):
    model = Profile
    extra = 0
    readonly_fields = ('telegram_token', 'user', 'change_user')
    fk_name = 'client'
    exclude = ('email_0', 'email_1', 'email_2', 'email_3', 'email_4', 'email_5', 'email_6', 'email_7',
               'email_8', 'email_9', 'phone_number_0', 'phone_number_1', 'phone_number_2', 'phone_number_3',
               'phone_number_4', 'phone_number_5', 'phone_number_6', 'phone_number_7',
               'phone_number_8', 'phone_number_9')

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def change_user(self, obj):
        return mark_safe('<a href="%s">Change User</a>' %
                         reverse('proteciaAdmin:app1_customuser_change',
                                 args=(obj.user.id,)
                                 )
                         )


class CameraInline(admin.TabularInline):
    model = Camera
    extra = 0
    readonly_fields = ('name', 'active', 'ip', 'username', 'password', 'threshold', 'gap', 'change_camera')
    exclude = ('wait_for_set', 'update', 'from_client', 'stream', 'on_camera_LD', 'on_camera_HD',
               'max_width_rtime', 'max_width_rtime_HD', 'reso', 'width', 'height', 'pos_sensivity',
               'max_object_area_detection', 'port_onvif', 'url', 'auth_type', 'rtsp', 'brand', 'model')

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def change_camera(self, obj):
        return mark_safe('<a href="%s">Change Camera</a>' %
                         reverse('admin:app1_camera_change',
                                 args=(obj.id,)
                                 )
                         )

class ClientAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'name', 'adress', 'cp', 'city')
    search_fields = ('first_name', 'name', 'city',)
    readonly_fields = ('key', 'folder', 'token_video')
    exclude = ('rec', 'change', 'update_camera', 'stop_thread', 'connected')
    inlines = [AlertTypeInline, ProfileInline2, CameraInline]

    def get_model_perms(self, request):
        if not request.user.is_superuser:
            return {}
        else:
            return super().get_model_perms(request)

    def has_add_permission(self, request):
        if request.user.is_superuser:
            return True
        else:
            return False

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        else:
            return False

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        else:
            return False



class ProteciaAdminSite(admin.AdminSite):
    site_header = "Serenicia ADMIN"


def has_superuser_permission(request):
    return request.user.is_active and request.user.is_superuser


admin_protecia2 = ProteciaAdminSite(name='proteciaAdmin')
admin_protecia2.has_permission = has_superuser_permission
admin_protecia2.register(Client, ClientAdmin)
admin_protecia2.register(CustomUser, SuperUserAdmin)

