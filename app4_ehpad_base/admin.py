import logging
import calendar

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth.models import User, Permission, ContentType
from django.contrib.admin.models import LogEntry

from django import forms
from django.db.models import Q

from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from django.urls import reverse
from django.dispatch import receiver
from django.db.models.signals import m2m_changed, post_save, pre_delete

from django.forms.models import ModelMultipleChoiceField

from app6_care.models import Nappy, SectorNappy, UserNappy, TaskLevel1, TaskLevel2, TaskLevel3, TaskLevel4, Intervention, \
    InterventionDetail, TreatmentsPlan, TaskInTreatmentPlan

from .admin_administrative import CardAdmin, InvoiceAdmin, DocumentAdmin, MutualDocumentAdmin, PersonalizedDocAdmin, \
    KitAdmin, DietAdmin

from .models import WeekRoutine, \
    MotDirection, MotPoleSoins, MotHotelResto, MotCVS, Pic, ProfileSerenicia, TypeRoutine, UserListIntermediate, \
    ProfileEhpad, AdministrativeDocument, Invoice, Card, WordToRecord, IntonationToRecord, MutualDocument, \
    PresentationType, PayRoll, PersonalizedDocument, KitInventory, Diet


from app1_base.log import Logger
from app1_base.models import Client, SubSector, Profile, ProfileSecurity, Camera, Sector, CameraSetup, MachineID, Preferences
from app4_ehpad_base.models import EmptyRoomCleaned, MealBooking
from app1_base.admin import ClientAdmin, MyUserAdmin, AlwaysChangedModelForm, CameraAdmin, ProfileInline, AlertTypeInline, \
    CameraInline, ProfileSecurityInline2, CameraSetupAdmin, MachineIdAdmin

from app4_ehpad_base.notifs import send_welcome_email
from app3_messaging.models import Notification


# ----------------------------------------------------------------------------------------------------------------------
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>    ADMIN FOR CAMERA    <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# ----------------------------------------------------------------------------------------------------------------------


class CameraAdmin2(CameraAdmin):
    def has_change_permission(self, request, obj=None):
        return super(CameraAdmin, self).has_change_permission(request)

    def get_queryset(self, request):
        return super(CameraAdmin, self).get_queryset(request)


# ----------------------------------------------------------------------------------------------------------------------
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>    ADMIN FOR USER    <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# ----------------------------------------------------------------------------------------------------------------------

@receiver(post_save, sender=MealBooking)
def send_notif_cre(sender, instance, created, **kwargs):
    month = instance.date.month
    month_name = calendar.month_name[month]
    month_name = _(month_name)

    if created:
        if instance.lunch and instance.dinner:
            meal = _('meal')
        else:
            if instance.lunch:
                meal = _('lunch')
            else:
                meal = _('dinner')
        notif = Notification(
            subject= _("A") + " " + meal + " " + _("has been booked"),
            content= _("A") + " " + meal + " " + _("for") + " " + f"{instance.date.day}" + " " + month_name + " " + _("has been booked by") + " " + f"{instance.owner.user.first_name}" + " " + f"{instance.owner.user.last_name}"
        )
        notif.save()
        [notif.recipients.add(user) for user in User.objects.filter(
            Q(groups__permissions__codename='view_ash') | Q(groups__permissions__codename='view_cuisine')).distinct()]


@receiver(pre_delete, sender=MealBooking)
def send_notif_del(sender, instance, using, **kwargs):
    month = instance.date.month
    month_name = calendar.month_name[month]
    month_name = _(month_name)

    if instance.lunch and instance.dinner:
        meal = _('meal')
    else:
        if instance.lunch:
            meal = _('lunch')
        else:
            meal = _('dinner')
    notif = Notification(
        subject= _("A") + " " + meal + " " + _("has been deleted"),
        content= _("A") + " " + meal + " " + _("booked for") + " " + f"{instance.date.day}" + " " + _("by") + " " + f"{instance.owner.user.first_name}" + " " + f"{instance.owner.user.last_name}" + " " + _("has been canceled")
    )
    notif.save()
    [notif.recipients.add(user) for user in User.objects.filter(
        Q(groups__permissions__codename='view_ash') | Q(groups__permissions__codename='view_cuisine')).distinct()]


@receiver(m2m_changed, sender=User.groups.through)
def send_welcome_group(sender, instance, action, pk_set, **kwargs):
    if 'log_admin_mail' not in globals():
        global log_admin_mail
        log_admin_mail = Logger('admin_mail', level=logging.ERROR, file=False).run()
    # print(f'parameter : pk_set :{pk_set}, sender :{sender}, instance :{instance}, kwargs :{kwargs}, action: {action}')
    if action == 'post_add':
        log_admin_mail.info(f'user selected : {pk_set}')
        for pk in pk_set:
            log_admin_mail.info(f'loop pk user : {pk}')
            if isinstance(instance, User):
                user = instance
            else:
                user = User.objects.get(pk=pk)
            try:
                if not user.profile.welcoming_sent and user.email:
                    if user.has_perms(["access.view_as", "access.view_ash", "access.view_ide"]):
                        log_admin_mail.info(f'send mail to : {user}')
                        try:
                            preferences = user.profile.preferences
                            preferences.notif_all_new_msg = False
                            preferences.save()
                        except Preferences.DoesNotExist:
                            pass
                        send_welcome_email(instance)
                        profile = user.profile
                        profile.welcoming_sent = True
                        profile.save()
            except Profile.DoesNotExist:
                pass


class ManyFieldsUser(ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.user.last_name} {obj.user.first_name}"


class ProfileSereniciaInline(admin.StackedInline):
    if 'log_admin' not in globals():
        global log_admin
        log_admin = Logger('admin', level=logging.ERROR, file=False).run()
    fk_name = 'user'
    model = ProfileSerenicia
    form = AlwaysChangedModelForm
    can_delete = False
    verbose_name_plural = 'profiles Serenicia'
    exclude = ('external_key', 'service_account_file', 'titan_key', 'user_waiting', 'passphrase')
    readonly_fields = ('pics_total', 'pics_last', 'date_status_deceased')

    def get_exclude(self, request, obj=None):
        excluded = super().get_exclude(request, obj) or []  # get overall excluded fields
        if not request.user.is_superuser:
            excluded += ('folder', 'token_video_call', 'uri_netsoins', 'cal_id',)
        return excluded

    def get_readonly_fields(self, request, obj=None):
        fields = self.readonly_fields
        if request.user.is_superuser:
            return fields + ('folder', 'token_video_call', 'uri_netsoins', 'cal_id')
        fields += ('homepage',)
        return fields

    # get list of active resident's user only
    def formfield_for_manytomany(self, db_field, request, **kwargs):

        if db_field.name == 'user_list':
            kwargs['queryset'] = Profile.objects.filter(
                user__groups__permissions__codename__in=['view_residentehpad', 'view_residentrss', ],
                user__is_active=True).order_by('user__last_name').exclude(user__profileserenicia__status='deceased')
            kwargs['widget'] = FilteredSelectMultiple(db_field.verbose_name, is_stacked=False)
            kwargs['required'] = False
            log_admin.debug(f'kwargs is {kwargs}')
            log_admin.debug(f'db_field is {db_field}')
            form_field = ManyFieldsUser(**kwargs)
            log_admin.debug(f'form_field is {form_field}')
            return form_field
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    # def save_related(self, request, form, formsets, change):
    #     super(ProfileSereniciaInline, self).save_related(request, form, formsets, change)


class ProfileInlineSerenicia(ProfileInline):
    readonly_fields = ('created_by', 'telegram_token')
    exclude = ('alert', 'reboot_protecia_box',
               'email_2', 'email_3', 'email_4',
               'email_5', 'email_6', 'email_7',
               'email_8', 'email_9', 'phone_number_2',
               'phone_number_3', 'phone_number_4', 'phone_number_5',
               'phone_number_6', 'phone_number_7', 'phone_number_8',
               'phone_number_9', 'tracking_number', 'tracking_site',
               )
    model = Profile
    form = AlwaysChangedModelForm
    can_delete = False
    verbose_name_plural = 'profiles'
    fk_name = 'user'

    def get_readonly_fields(self, request, obj=None):
        fields = self.readonly_fields
        if request.user.is_superuser:
            fields += ('send_mail_url',)
            if obj:
                fields += ('created_by',)
        else:
            fields += ('client',)
        return fields


class SecurityProfileInline(admin.StackedInline):
    model = ProfileSecurity
    fk_name = 'user'
    verbose_name_plural = 'security profiles'


# The connected user must be in a group with the access view_manager to manage the user_list from admin
class Userapp4_ehpad_baseAdmin(MyUserAdmin):
    # readonly_fields = ('groups',)
    search_fields = ('last_name', 'first_name', 'username', 'groups__name', 'profile__client__room_number', 'email')
    list_display = ('username', 'email', 'first_name', 'last_name', 'last_login', 'date_joined')
    list_filter = ('is_active', 'groups', 'profileserenicia__status', 'profileserenicia__UP_volunteer')
    inlines = [ProfileSereniciaInline, ProfileInlineSerenicia, SecurityProfileInline, ]

    def delete_queryset(self, request, queryset):
        for u in queryset:
            u.delete()

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets

        if request.user.is_superuser:
            perm_fields = ('is_active', 'is_staff', 'is_superuser',
                           'groups', 'user_permissions')
        else:
            perm_fields = ('is_active',)
        fieldsets = [(None, {'fields': ('username', 'password')}),
                     (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
                     (_('Important dates'), {'fields': ('last_login', 'date_joined')})]
        if perm_fields:
            fieldsets.append((_('Permissions'), {'fields': perm_fields}))
        return fieldsets

    def get_queryset(self, request):
        return super(UserAdmin, self).get_queryset(request).exclude(
            groups__permissions__codename__in=['view_prospect', ])

    def save_related(self, request, form, formsets, change):
        after_list = []  # |
        for idd in request.POST.getlist('profileserenicia-0-user_list'):  # | getting all "new" relations
            after_list.append(Profile.objects.get(pk=idd))  # |
        for formset in formsets:
            if formset.model == ProfileSerenicia:
                instances = formset.save(commit=False)
                for instance in instances:  # |
                    before_list = []  # |getting all "old"
                    try:
                        for profile in instance.user_list.all():  # |relations
                            before_list.append(profile)  # |
                    except ValueError:
                        pass
                    instance.save()
                    for profile in list(set(after_list).difference(before_list)):  # retain only truly new relations
                        instance.user_list.add(profile)  # | create the relation
                        userlistintermediate = UserListIntermediate.objects.get(profile=profile.id,
                                                                                profileserenicia=instance.id)  # get the through of the relation we just set up
                        userlistintermediate.was_manual = True  # register this through as manual
                        userlistintermediate.save()  # save our modification
                    instance.save()  # save the instance (profileserenicia)
                formset.save_m2m()  # if I understood correctly it should not do anything anymore
                # but I won't try to take it out now that it work
        super().save_related(request, form, formsets, change)


# https://stackoverflow.com/questions/8294889/override-save-on-django-inlinemodeladmin
# https://stackoverflow.com/questions/36926718/django-admin-how-can-i-use-save-related-to-parse-data-from-inline-forms


class UserListIntermediateInLine(admin.StackedInline):
    model = ProfileSerenicia.user_list.through
    readonly_fields = ('profile',)
    extra = 0


class UserLinkAdmin(admin.ModelAdmin):
    exclude = ['userlistintermediate', 'pic', 'visitor', 'residentinformation', 'surveyresponse',
               'profileprocaregiver', 'id', 'user', 'folder', 'homepage', 'status', 'external_key',
               'birth_city', 'birth_date', 'entry_date', 'cal_id', 'titan_key', 'pics_total', 'pics_last',
               'token_video_call', 'uri_netsoins', 'service_account_file', 'gcp_project', 'has_active_service_account',
               'active_since', 'sa_email', 'has_active_subcalendar', 'bacterium', 'user_list', 'user_waiting']
    inlines = [UserListIntermediateInLine, ]


# @receiver(post_save, sender=Photos)
# def signal_photos(sender, instance, created, raw, using, update_fields, **kwargs):
#     print("sender:", sender)
#     print("instance:", instance)
#     print("raw:", raw)


# ----------------------------------------------------------------------------------------------------------------------
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>    ADMIN FOR RESIDENT/ADRESS <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# ----------------------------------------------------------------------------------------------------------------------

class SearchAdminField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return "{} {}".format(obj.last_name, obj.first_name)


class ProfileInline2(admin.TabularInline):
    model = Profile
    fk_name = 'client'
    extra = 0
    readonly_fields = ('telegram_token', 'created_by')
    exclude = ('reboot_protecia_box', 'email_1', 'email_0',
               'email_2', 'email_3', 'email_4',
               'email_5', 'email_6', 'email_7',
               'email_8', 'email_9', 'phone_number_2', 'phone_number_0', 'phone_number_1',
               'phone_number_3', 'phone_number_4', 'phone_number_5',
               'phone_number_6', 'phone_number_7', 'phone_number_8',
               'phone_number_9', 'tracking_number', 'tracking_site',
               )

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'user':
            return SearchAdminField(
                queryset=User.objects.filter(
                    groups__permissions__codename__in=['view_residentehpad', 'view_residentrss', ], is_active=True
                ).order_by('last_name')
            )
        return super(ProfileInline2, self).formfield_for_foreignkey(db_field, request, **kwargs)


class CameraInline2(CameraInline):
    # noinspection PyMethodMayBeStatic
    def change_camera(self, obj):
        href = reverse('admin:app1_camera_change', args=(obj.id,), current_app='admin_serenicia')
        return mark_safe(f'<a href="{href}">Change camera {obj.id}</a>')


class Clientapp4_ehpad_baseAdmin(ClientAdmin):  # base on the admin in app1_base with addons about Serenicia particularity.
    search_fields = ('sector__name', 'room_number', 'city', 'cp', 'adress')
    exclude = ('rec', 'change', 'update_camera', 'stop_thread', 'connected', 'ping',
               'folder', 'external_key', 'logo_perso')
    list_display = ('room_number', 'sector', 'adress_lieu', 'cp', 'city', 'resident')
    list_filter = ('sector', 'actif', 'helper', 'shower', 'type')
    ordering = ('room_number',)
    list_display_links = ('sector', 'room_number', 'adress_lieu')
    inlines = [ProfileInline2, AlertTypeInline, CameraInline2, ProfileSecurityInline2]

    # # noinspection PyMethodMayBeStatic
    # def change_camera(self, obj):
    #     # return obj.profilesecurity.user
    #     href = reverse('admin_app4_ehpad_base:app1_camera_change', args=(obj.id,))
    #     return mark_safe(f'<a href="{href}">{obj.id}</a>')

    def get_exclude(self, request, obj=None):
        excluded = super().get_exclude(request, obj) or []  # get overall excluded fields
        if not request.user.is_superuser:
            excluded += ('adress_lieu', 'wait_before_detection', 'dataset_test', 'space_allowed',
                         'image_panel_max_width', 'image_panel_max_hight', 'timestamp', 'token_video_time',
                         'machine_id', 'scan_camera', 'type', 'key', 'token_video', 'scan', 'actif', 'time_zone')
        return excluded

    def get_search_fields(self, request):
        fields = self.search_fields
        if request.user.is_superuser:
            return fields + ('tunnel_port',)
        return fields

    def get_readonly_fields(self, request, obj=None):
        fields = self.readonly_fields
        if request.user.is_superuser:
            return fields
        return 'tunnel_port', 'alexa_device_id', 'docker_version'

    def resident(self, obj):
        user = User.objects.filter(
            profile__client=obj, groups__permissions__codename__in=['view_residentehpad', 'view_residentrss', ])
        if len(user) == 0:
            return _('Empty')
        if len(user) == 1:
            return user[0].last_name + ' ' + user[0].first_name
        return _('Multiple affectation')

    def has_module_permission(self, request):
        return super(ClientAdmin, self).has_module_permission(request)

    def has_add_permission(self, request):
        return super(ClientAdmin, self).has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        return super(ClientAdmin, self).has_change_permission(request)

    def has_delete_permission(self, request, obj=None):
        return super(ClientAdmin, self).has_delete_permission(request)

    def get_queryset(self, request):
        return super(ClientAdmin, self).get_queryset(request)


# ----------------------------------------------------------------------------------------------------------------------
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>    Related to App6 <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# ----------------------------------------------------------------------------------------------------------------------
class SectorNappyInline(admin.TabularInline):
    model = SectorNappy
    extra = 0


class UserNappyInline(admin.TabularInline):
    model = UserNappy
    extra = 0


class UserNappyAdmin(admin.ModelAdmin):
    search_fields = ['user__last_name', 'user__first_name']
    ordering = ['user__last_name']
    list_filter = ('nappy__name', 'quantity')

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'user':
            return SearchAdminField(
                queryset=User.objects.filter(groups__permissions__codename__in=['view_residentehpad', ], is_active=True
                                             ).order_by('last_name'))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class NappyAdmin(admin.ModelAdmin):
    inlines = [UserNappyInline]


class SectorNappyAdmin(admin.ModelAdmin):
    list_filter = ('sector', 'nappy')


class TaskLevel1Admin(admin.ModelAdmin):
    list_filter = ('profession', 'specific_to_a_resident')
    search_fields = ['name']
    ordering = ['name']
    filter_horizontal = ['details', 'nappy']

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "details":
            kwargs["queryset"] = TaskLevel2.objects.all().order_by('name')
        return super().formfield_for_manytomany(db_field, request, **kwargs)


class TaskLevel2Admin(admin.ModelAdmin):
    search_fields = ['name']
    ordering = ['name']
    filter_horizontal = ['details', 'nappy']

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "details":
            kwargs["queryset"] = TaskLevel3.objects.all().order_by('name')
        return super().formfield_for_manytomany(db_field, request, **kwargs)


class TaskLevel3Admin(admin.ModelAdmin):
    search_fields = ['name']
    ordering = ['name']
    filter_horizontal = ['details', 'nappy']

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "details":
            kwargs["queryset"] = TaskLevel4.objects.all().order_by('name')
        return super().formfield_for_manytomany(db_field, request, **kwargs)


class TaskLevel4Admin(admin.ModelAdmin):
    search_fields = ['name']
    ordering = ['name']


class TreatmentsPlanAdmin(admin.ModelAdmin):
    search_fields = ['patient__last_name', 'patient__first_name']
    ordering = ['patient__last_name']

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'patient':
            return SearchAdminField(
                queryset=User.objects.filter(groups__permissions__codename='view_residentehpad', is_active=True
                                             ).order_by('last_name'))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# ----------------------------------------------------------------------------------------------------------------------
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>    Related to Payroll <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# ----------------------------------------------------------------------------------------------------------------------
class PayRollAdmin(admin.ModelAdmin):
    list_display = ("employees", "date_of_payslip", "pk")
    search_fields = ['employees__first_name', "employees__last_name"]
    ordering = ['pk']
    list_filter = ["date_of_payslip"]

# ----------------------------------------------------------------------------------------------------------------------


# ---------------------------------------------------------------------------------------------------------------------
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>  Admin for log <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# --------------------------------------------------------------------------------------------------------------------
class LogEntryAdmin(admin.ModelAdmin):
    date_hierarchy = 'action_time'

    list_filter = [
        'content_type',
        'action_flag'
    ]

    search_fields = [
        'object_repr',
        'change_message',
        'content_type'
    ]

    list_display = [
        'action_time',
        'user',
        'content_type',
        'action_flag',
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser
# ----------------------------------------------------------------------------------------------------------------------

# class AdminSerenicia(admin.AdminSite):
#     site_header = "Serenicia ADMIN"


# Here is the administration for Serenicia   maybe register with admin.app4_ehpad_base.register could be better
#  admin_app4_ehpad_base = AdminSerenicia(name="admin_serenicia")

admin.site.unregister(User)
admin.site.register(Client, Clientapp4_ehpad_baseAdmin)
admin.site.register(User, Userapp4_ehpad_baseAdmin)
admin.site.register(MotDirection)
admin.site.register(MotPoleSoins)
admin.site.register(MotHotelResto)
admin.site.register(MotCVS)
admin.site.register(SubSector)
admin.site.register(Permission)
admin.site.register(ContentType)
admin.site.register(Pic)
admin.site.register(TypeRoutine)
admin.site.register(Camera, CameraAdmin2)
admin.site.register(WeekRoutine)
admin.site.register(Sector)
admin.site.register(CameraSetup, CameraSetupAdmin)
admin.site.register(WordToRecord)
admin.site.register(IntonationToRecord)
admin.site.register(ProfileEhpad)
admin.site.register(PresentationType)
admin.site.register(PayRoll, PayRollAdmin)
admin.site.register(EmptyRoomCleaned)


# related to app6_care
admin.site.register(Nappy)
admin.site.register(SectorNappy, SectorNappyAdmin)
admin.site.register(UserNappy, UserNappyAdmin)
admin.site.register(TaskLevel1, TaskLevel1Admin)
admin.site.register(TaskLevel2, TaskLevel2Admin)
admin.site.register(TaskLevel3, TaskLevel3Admin)
admin.site.register(TaskLevel4, TaskLevel4Admin)
admin.site.register(Intervention)
admin.site.register(InterventionDetail)
admin.site.register(TreatmentsPlan, TreatmentsPlanAdmin)
admin.site.register(TaskInTreatmentPlan)


# Document admin
admin.site.register(Card, CardAdmin)
admin.site.register(Invoice, InvoiceAdmin)
admin.site.register(MutualDocument, MutualDocumentAdmin)
admin.site.register(AdministrativeDocument, DocumentAdmin)
admin.site.register(PersonalizedDocument, PersonalizedDocAdmin)
admin.site.register(KitInventory, KitAdmin)
admin.site.register(Diet, DietAdmin)

# For jetson management
admin.site.register(MachineID, MachineIdAdmin)

admin.site.register(ProfileSerenicia, UserLinkAdmin)

admin.site.register(LogEntry, LogEntryAdmin)
