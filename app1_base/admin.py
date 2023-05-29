from django.contrib import admin
from django.forms.models import ModelForm

from django.db.models import Q

from django.contrib.auth.models import Group, User, Permission
from django.contrib.sites.models import Site
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.contrib import admin

from .models import Client, Camera, Profile, Alert_type, ProfileSecurity, CameraUri, MachineID, ProfileAlert
from .utils import niceMail
from django.forms import BaseInlineFormSet
from django.core.exceptions import ValidationError
from app1_base.log import Logger

import logging
from django.conf import settings
from django.utils import timezone

# log_admin_mail = Logger('app1_admin', level=logging.ERROR).run()

if 'log_admin_mail' not in globals():
    global log_admin_mail
    log_admin_mail = Logger('app1_admin', level=logging.ERROR).run()


# ----------------------------------------------------------------------------------------------------------------------
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>    ADMIN FOR CAMERA    <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# ---------------------------------------------------------------------------------------------------------------------
class FormSetOnlyOne(BaseInlineFormSet):
    def clean(self):
        """Checks that only one instance is current"""
        if any(self.errors):
            # Don't bother validating the formset unless each form is valid on its own
            return
        count = 0
        for form in self.forms:
            if form.cleaned_data['use']:
                count += 1
                if count > 1:
                    raise ValidationError("Only one item can be current")


class UriAdminInline(admin.TabularInline):
    model = CameraUri
    extra = 0
    formset = FormSetOnlyOne


class CameraAdmin(admin.ModelAdmin):
    exclude = ('update',  'on_camera_LD', 'on_camera_HD', 'on_rec', 'change')
    list_filter = ('active', 'from_client',)
    readonly_fields = ('wait_for_set', 'serial_number', 'from_client')
    inlines = [UriAdminInline, ]

    def delete_queryset(self, request, queryset):
        client = []
        for obj in queryset:
            client.append(obj.client)
        for c in set(client):
            c.update_camera = 1
            c.save(update_fields=['update_camera', ])
        queryset.delete()

    def delete_model(self, request, obj):
        obj.client.update_camera = 1
        obj.client.save(update_fields=['update_camera', ])
        obj.delete()

    def get_readonly_fields(self, request, obj=None):
        if 'log_admin' not in globals():
            global log_admin
            log_admin = Logger('admin', level=logging.ERROR).run()
        fields = self.readonly_fields
        # if security_box is multi client can change 'client' via admin to move camera between clients
        if obj and obj.from_client:
            fields += ('ip', 'port_onvif', 'auth_type', 'brand', 'model',)
            if not obj.client.machine_id.multi_client:
                fields += ('client', )

        if not request.user.is_superuser:
            fields += ('threshold', 'gap',
                       'pos_sensivity', 'reso', 'width', 'height', 'max_width_rtime', 'max_width_rtime_HD')
        else:
            fields += ('active_automatic',)
        return fields

    def save_model(self, request, obj, form, change):
        if getattr(obj, 'client', None) is None:
            # noinspection PyUnresolvedReferences
            obj.client = Profile.objects.get(user=request.user).client
        if 'on_camera_LD' not in form.changed_data and 'on_camera_HD' not in form.changed_data:
            obj.client.update_camera = 1
            obj.client.save(update_fields=['update_camera', ])
        obj.save()

    def save_related(self, request, form, formsets, change):
        log_admin.info(f'calling save_related uri')
        for form_set in formsets:
            if form_set.has_changed():
                # Call function to notify change
                camera = form_set.cleaned_data[0]['camera']
                client = camera.client
                log_admin.info(f'save_related formset : {client}')
                client.update_camera = 1
                client.save(update_fields=['update_camera', ])
        super().save_related(request, form, formsets, change)

    def get_queryset(self, request):
        qs = super(CameraAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        # noinspection PyUnresolvedReferences
        return qs.filter(Q(active_automatic=True) |
                         Q(wait_for_set=True), client=request.session['client'])

    def has_change_permission(self, request, obj=None):
        if not obj:
            return True
        # noinspection PyUnresolvedReferences
        return request.user.is_superuser or ProfileSecurity.objects.filter(client=obj.client).exists()

    def get_exclude(self, request, obj=None):
        excluded = super().get_exclude(request, obj) or ()  # get overall excluded fields

        if not request.user.is_superuser:  # if user is not a superuser
            # noinspection PyTypeChecker
            return excluded + ('client', 'active_automatic',)

        return excluded  # otherwise return the default excluded fields if any


class CameraSetupAdmin(admin.ModelAdmin):
    list_display = ['location', 'room', 'ip_identification', 'state']
    list_filter = ['location', 'state']
    search_fields = ['location', 'room', 'ip_identification', 'mac_identification', 'state', 'video_quality']

    def get_readonly_fields(self, request, obj=None):
        fields = self.readonly_fields
        if request.user.is_superuser:
            return fields
        return 'location', 'room', 'ip_identification', 'mac_identification', 'state', 'video_quality'


# ---------------------------------------------------------------------------------------------------------------------


# ----------------------------------------------------------------------------------------------------------------------
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>    ADMIN FOR USER    <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# ---------------------------------------------------------------------------------------------------------------------


# noinspection PyUnusedLocal,PyUnusedLocal
# @receiver(post_save, sender=User)
# def add_group_permission(sender, instance, created, **kwargs):
#     if created:
#         g = Group.objects.get(name='normal')
#         g.user_set.add(instance)

# @receiver(post_save, sender= Profile)
# def send_welcome(sender, instance, created, **kwargs):
#     if created:
#         first_name = instance.user.first_name
#         last_name = instance.user.last_name
#         username = instance.user.username
#         email = instance.user.email
#         adress = ' '.join([instance.client.adress, instance.client.cp, instance.client.city])
#         tracking = instance.tracking_number
#         tracking_site = instance.tracking_site
#         language = instance.language
#         password = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
#         instance.user.set_password(password)
#         instance.user.save()
#         message=niceMail(email, first_name, last_name, username, password,
#         language, adress, tracking=tracking, tracking_site = tracking_site)
#         #message.send_email()


class AlwaysChangedModelForm(ModelForm):
    # noinspection PyArgumentList
    def has_changed(self, *args, **kwargs):
        if self.instance.pk is None:
            return True
        # noinspection PyArgumentList
        return super(AlwaysChangedModelForm, self).has_changed(*args, **kwargs)


class ProfileSecurityInline(admin.StackedInline):
    model = ProfileSecurity
    fk_name = 'user'
    verbose_name_plural = 'security profiles'


class ProfileAlertInline(admin.StackedInline):
    model = ProfileAlert
    fk_name = 'user'
    verbose_name_plural = 'security warning'


class ProfileInline(admin.StackedInline):
    # add_fieldsets = ((None, {'fields': ('client','phone_number', 'language'),}),)
    readonly_fields = ('telegram_token', 'reboot_protecia_box')
    # exclude = ('alert',)
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
        if not obj:  # if user in creation
            if request.user.is_superuser:
                self.add_fieldsets = ((None, {'fields': ('phone_number', 'language',), }),)
                return self.add_fieldsets
            else:
                # noinspection PyAttributeOutsideInit
                self.add_fieldsets = ((None, {'fields': ('phone_number', 'language'), }),)
                return self.add_fieldsets
        else:
            return super(ProfileInline, self).get_fieldsets(request, obj=None)

    def get_exclude(self, request, obj=None):
        excluded = super().get_exclude(request, obj) or []  # get overall excluded fields

        if not request.user.is_superuser:  # if user is not a superuser
            # noinspection PyTypeChecker
            return excluded + ('tracking_number', 'tracking_site', 'created_by')

        return excluded  # otherwise return the default excluded fields if any

    # noinspection PyMethodMayBeStatic
    def send_mail_url(self, obj):
        return format_html("<a href='{url}'>SEND RESET PASSWORD MAIL</a>", url="/mail/reset/" + str(obj.id))

    # noinspection PyMethodMayBeStatic
    def reboot_protecia_box(self, obj):
        return format_html("<a href='{url}'>REBOOT PROTECIA BOX</a>", url="/reboot/" + str(obj.id))


class MyUserAdmin(UserAdmin):
    add_fieldsets = ((None, {'fields': ('username', 'password1', 'password2', 'first_name', 'last_name', 'email',
                                        'groups'), }),)
    inlines = [ProfileInline, ProfileSecurityInline, ProfileAlertInline]
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
    list_filter = ('is_staff', 'is_active')

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
        # noinspection PyUnresolvedReferences
        return qs.filter(profilesecurity__in=ProfileSecurity.objects.filter(user=request.user))

    def save_formset(self, request, form, formset, change):
        if not request.user.is_superuser:
            instances = formset.save(commit=False)
            for instance in instances:
                # noinspection PyUnresolvedReferences
                instance.client = Profile.objects.get(user=request.user).client
                instance.created_by = 'user'
                instance.save()
            formset.save_m2m()
        else:
            super(MyUserAdmin, self).save_formset(request, form, formset, change)


# ----------------------------------------------------------------------------------------------------------------------


# ----------------------------------------------------------------------------------------------------------------------
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>    ADMIN FOR RESIDENT/ADDRESS   <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# ---------------------------------------------------------------------------------------------------------------------
class ProfileSecurityInline2(admin.TabularInline):
    model = ProfileSecurity.client.through
    extra = 0
    readonly_fields = ('change_user',)
    exclude = ('profilesecurity',)

    #     fk_name = 'client'
    #     # exclude = ('email_0', 'email_1', 'email_2', 'email_3', 'email_4', 'email_5', 'email_6', 'email_7',
    #     #            'email_8', 'email_9', 'phone_number_0', 'phone_number_1', 'phone_number_2', 'phone_number_3',
    #     #            'phone_number_4', 'phone_number_5', 'phone_number_6', 'phone_number_7',
    #     #            'phone_number_8', 'phone_number_9', 'user')
    #
    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    # noinspection PyMethodMayBeStatic
    def change_user(self, obj):
        # return obj.profilesecurity.user
        href = reverse('admin:auth_user_change', args=(obj.profilesecurity.user.id,))
        return mark_safe(f'<a href="{href}">{obj.profilesecurity.user}</a>')


class AlertTypeInline(admin.TabularInline):
    model = Alert_type


class CameraInline(admin.TabularInline):
    if 'log_admin' not in globals():
        global log_admin
        log_admin = Logger('admin', level=logging.ERROR).run()
    model = Camera
    extra = 0
    readonly_fields = ('name', 'active_automatic', 'ip', 'username', 'password', 'threshold', 'gap', 'change_camera',
                       'serial_number',)
    exclude = ('wait_for_set', 'update', 'from_client', 'stream', 'on_camera_LD', 'on_camera_HD',
               'max_width_rtime', 'max_width_rtime_HD', 'reso', 'width', 'height', 'pos_sensivity',
               'max_object_area_detection', 'port_onvif', 'auth_type', 'brand', 'model', 'on_rec', 'change')

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    # noinspection PyMethodMayBeStatic
    def change_camera(self, obj):
        return mark_safe('<a href="%s">Change Camera</a>' %
                         reverse('admin:app1_camera_change',
                                 args=(obj.id,)
                                 )
                         )


class ClientAdmin(admin.ModelAdmin):
    list_display = ('adress', 'cp', 'city', 'user_residence_security')
    search_fields = ('city',)
    readonly_fields = ('key', 'folder', 'token_video')
    exclude = ('rec', 'change', 'update_camera', 'stop_thread', 'connected')
    inlines = [AlertTypeInline, CameraInline, ProfileSecurityInline2]

    def user_residence_security(self, obj):
        return "\n".join([c.user.last_name for c in ProfileSecurity.objects.filter(client=obj)])

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # noinspection PyUnresolvedReferences
        return qs.filter(pk=request.session['client'])

    # def get_model_perms(self, request):
    #     if not request.user.is_superuser:
    #         return {}
    #     else:
    #         return super().get_model_perms(request)

    def has_module_permission(self, request):
        if request.user.is_superuser:
            return True
        else:
            return super().has_module_permission(request)

    def has_add_permission(self, request):
        if request.user.is_superuser:
            return True
        else:
            return super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        else:
            return super().has_change_permission(request)

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        else:
            return super().has_delete_permission(request)

    def save_related(self, request, form, formsets, change):
        log_admin.info(f'calling save_related camera {formsets}')
        for form_set in formsets:
            if form_set.has_changed():
                # Call function to notify change
                client = form_set.cleaned_data[0]['client']
                log_admin.info(f'save_related formset : {client}')
                client.update_camera = 1
                client.save(update_fields=['update_camera', ])
        super().save_related(request, form, formsets, change)

    def save_model(self, request, obj, form, change):
        if change:
            obj.change = 1
        super(ClientAdmin, self).save_model(request, obj, form, change)


# ---------------------------------------------------------------------------------------------------------------------


class MachineIdAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'date', 'client_link', 'docker_version', 'residence')
    search_fields = ('uuid',)
    readonly_fields = ('uuid', 'date', 'timestamp')
    excluded = ('change',)

    @admin.display
    def client_link(self, obj):
        client = Client.objects.filter(machine_id=obj)
        if not client:
            return '>> box not affected <<'
        else:
            delta = timezone.now() - client.last().timestamp
            if delta.total_seconds() < 30:
                return 'alive'
            else:
                return 'dead'

    @admin.display(empty_value='no client')
    def residence(self, obj):
        client = Client.objects.filter(machine_id=obj)
        if not client:
            return '>> box not affected <<'
        else:
            return ' '.join([item for sublist in client.values_list('adress_lieu', 'adress', 'cp', 'city')
                             for item in sublist])

    def get_exclude(self, request, obj=None):
        excluded = self.excluded

        if not request.user.is_superuser:  # if user is not a superuser
            # noinspection PyTypeChecker
            return excluded + ('future_user', 'timestamp', 'tunnel_port', 'multi_client')

        else:
            return excluded

    def get_readonly_fields(self, request, obj=None):
        fields = self.readonly_fields
        if not request.user.is_superuser:
            fields += ('docker_version', )
        return fields

    def save_model(self, request, obj, form, change):
        if change:
            obj.change = 1
        super(MachineIdAdmin, self).save_model(request, obj, form, change)


# class ProteciaAdmin(admin.AdminSite):
#     site_header = "Protecia ADMIN"
#
#
# admin_protecia = ProteciaAdmin(name='proteciaAdmin')
# admin_protecia.register(Client, ClientAdmin)
# admin_protecia.register(Group)
# admin_protecia.register(Permission)
# admin_protecia.register(CustomUser, MyUserAdmin)
# admin_protecia.register(Camera, CameraAdmin)

if "protecia" in settings.DOMAIN.lower():
    admin.site.register(Client, ClientAdmin)
    admin.site.unregister(User)
    admin.site.unregister(Site)
    admin.site.register(User, MyUserAdmin)
    admin.site.register(Camera, CameraAdmin)
    admin.site.register(Permission)
    admin.site.register(MachineID, MachineIdAdmin)
