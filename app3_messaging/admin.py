from app3_messaging.models import ProspectUser, DataEmail, Campaign, ProspectUserProfile, ProspectUserActive, CustomGroup
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from django.db.models import Count, Case, When, IntegerField, Q
from app1_base.admin import ProfileInline


class DataEmailInline(admin.TabularInline):
    model = DataEmail
    fk_name = 'user'
    extra = 0
    exclude = ('clef', 'email_adress_sender', 'content', 'date_creation', 'is_notif', )
    readonly_fields = ('date_sent', 'date_opened', 'date_clicked', 'date_unsubscribed', 'subject', 'campaign_of_mail')
    can_delete = False

    def get_queryset(self, request):
        return super().get_queryset(request).filter(Q(date_clicked__isnull=False) | Q(date_unsubscribed__isnull=False))


class ProfileInlineProspect(ProfileInline):
    exclude = ('alert', 'reboot_protecia_box', 'telegram_token', 'photo',
               'email_2', 'email_3', 'email_4',
               'email_5', 'email_6', 'email_7',
               'email_8', 'email_9', 'phone_number_2',
               'phone_number_3', 'phone_number_4', 'phone_number_5',
               'phone_number_6', 'phone_number_7', 'phone_number_8',
               'phone_number_9', 'tracking_number', 'tracking_site', 'phonetic_firstname', 'phonetic_lastname',
               'video_ready', 'welcoming_sent', 'display_adress', 'send_mail_url', 'client',
               )
    readonly_fields = ()

    def get_readonly_fields(self, request, obj=None):
        return super(ProfileInline, self).get_readonly_fields(request, obj)


class ProspectUserAdminActive(admin.ModelAdmin):
    search_fields = ('last_name', 'first_name', 'username', 'groups__name', 'email')
    list_display = ('username', 'nb_clicks', 'email', 'first_name', 'last_name', )
    inlines = [ProfileInlineProspect, DataEmailInline]
    fieldsets = (
        (None, {'fields': ('username',)}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    def nb_clicks(self, obj):
        return DataEmail.objects.filter(user=obj, date_clicked__isnull=False).count()

    def get_queryset(self, request):
        return super(ProspectUserAdminActive, self).get_queryset(request).filter(
            groups__permissions__codename='view_prospect').annotate(
            nb_clicks=Count(Case(When(dataemail__date_clicked__isnull=False, then=1),
                                 output_field=IntegerField(),))).filter(nb_clicks__gt=1).order_by('-nb_clicks')


class ProspectUserAdminUnsubscribe(admin.ModelAdmin):
    def get_queryset(self, request):
        return super(ProspectUserAdminUnsubscribe, self).get_queryset(request).filter(subscribe_emails=False)


class ProspectUserAdmin(UserAdmin):
    search_fields = ('last_name', 'first_name', 'username', 'groups__name', 'profile__client__room_number', 'email')
    list_display = ('username', 'email', 'first_name', 'last_name', 'last_login')
    list_filter = ('is_active', 'groups')
    inlines = [DataEmailInline, ProfileInlineProspect, ]
    fieldsets = [(None, {'fields': ('username',)}),
                 (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
                 (_('Important dates'), {'fields': ('last_login', 'date_joined')})]

    def get_queryset(self, request):
        return super(UserAdmin, self).get_queryset(request).filter(
            groups__permissions__codename__in=['view_prospect', ])

    def get_fieldsets(self, request, obj=None):

        if not obj:
            return self.add_fieldsets

        fieldsets = [(None, {'fields': ('username',)}),
                     (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
                     (_('Important dates'), {'fields': ('last_login', 'date_joined')})]

        if request.user.is_superuser:
            fieldsets.append((_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups',
                                                            'user_permissions')}))
        return fieldsets


class DataEmailAdmin(admin.ModelAdmin):
    search_fields = ('user__last_name', 'campaign_of_mail__nom_de_la_campagne')
    list_display = ('last_name', 'nom_de_la_campagne', 'date_creation', 'date_sent', 'date_opened', 'date_clicked')
    list_filter = ('date_creation', 'date_sent', 'date_opened', 'date_clicked')

    def last_name(self, obj):
        return obj.user.last_name
    last_name.admin_order_field = 'user'
    last_name.short_description = _('Last Name')

    # @admin.display(empty_value='unnamed')
    def nom_de_la_campagne(self, obj):
        if obj.campaign_of_mail:
            return obj.campaign_of_mail.nom_de_la_campagne
        else:
            return 'unamed'
    nom_de_la_campagne.admin_order_field = 'campaign_of_mail__nom_de_la_campagne'
    nom_de_la_campagne.short_description = _('Campaign Name')


class CustomGroupAdmin(admin.ModelAdmin):
    search_fields = ('members__username', 'name')
    list_display = ('name', )


admin.site.register(CustomGroup, CustomGroupAdmin)
admin.site.register(Campaign)
admin.site.register(DataEmail, DataEmailAdmin)
admin.site.register(ProspectUser, ProspectUserAdmin)
admin.site.register(ProspectUserProfile, ProspectUserAdminUnsubscribe)
admin.site.register(ProspectUserActive, ProspectUserAdminActive)

