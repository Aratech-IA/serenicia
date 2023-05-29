from django.utils.translation import gettext_lazy as _

from django.contrib import admin

from app12_delivery.models import ContractDelivery, Referent, BillingPerson, Constraint, DeliveryWindow, \
    CancelDelivery, \
    TourDelivery, Delivery, DeliveryDay, BusinessDeliveryProfile, BusinessDeliveryUser, BusinessManProfile, \
    DeliveryManUser, InfoCustomerInvoice, DesignationInvoice, InvoiceHomePlus, NumberDesignationPerInvoice, \
    WeekOfContract, MealsNumber
from app4_ehpad_base.admin import ProfileSereniciaInline


class BusinessDeliveryProfileInline(admin.TabularInline):
    model = BusinessDeliveryProfile
    fieldsets = [(_('Adress'), {'fields': ('adress', 'cp', 'city')}),
                 (_('coordinates'), {'fields': ('adress_latitude', 'adress_longitude')})
                 ]


class BusinessDeliveryUserAdmin(admin.ModelAdmin):
    inlines = [
        BusinessDeliveryProfileInline,
        ProfileSereniciaInline,
    ]
    search_fields = ('last_name', 'first_name', 'username', 'groups__name', 'email')
    list_display = ('username', 'email', 'first_name', 'last_name', 'last_login')
    list_filter = ('groups',)
    fieldsets = [(None, {'fields': ('username', 'password',)}),
                 (_('Personal info'), {'fields': ('first_name', 'last_name', 'email',)}),
                 (_('Groups'), {'fields': ('groups',)})
                 ]

    def get_queryset(self, request):
        # Permission.
        return super(BusinessDeliveryUserAdmin, self).get_queryset(request).filter(
            groups__permissions__codename__in=['view_deliverybusiness', ])


class DeliveryManProfileInline(admin.TabularInline):
    model = BusinessManProfile
    # exclude = ["*"]


fieldsets = [(_('Adress'), {'fields': ('adress', 'cp', 'city')}),
             (_('coordinates'), {'fields': ('adress_latitude', 'adress_longitude')})
             ]


class DeliveryManUserAdmin(admin.ModelAdmin):
    inlines = [
        DeliveryManProfileInline,
        ProfileSereniciaInline,
    ]
    search_fields = ('last_name', 'first_name', 'username', 'groups__name', 'email')
    list_display = ('username', 'email', 'first_name', 'last_name', 'last_login')
    list_filter = ('groups',)
    fieldsets = [(None, {'fields': ('username', 'password',)}),
                 (_('Personal info'), {'fields': ('first_name', 'last_name', 'email',)}),
                 (_('Groups'), {'fields': ('groups',)})
                 ]

    def get_queryset(self, request):
        # Permission.
        return super(DeliveryManUserAdmin, self).get_queryset(request).filter(
            groups__permissions__codename__in=['view_delivery', ])


admin.site.register(DeliveryManUser, DeliveryManUserAdmin)
admin.site.register(BusinessDeliveryUser, BusinessDeliveryUserAdmin)
admin.site.register(Referent)
admin.site.register(WeekOfContract)
admin.site.register(BillingPerson)
admin.site.register(Constraint)
admin.site.register(DeliveryWindow)
admin.site.register(DeliveryDay)
admin.site.register(CancelDelivery)
admin.site.register(TourDelivery)
admin.site.register(Delivery)
admin.site.register(ContractDelivery)
admin.site.register(InfoCustomerInvoice)
admin.site.register(DesignationInvoice)
admin.site.register(InvoiceHomePlus)
admin.site.register(NumberDesignationPerInvoice)
admin.site.register(MealsNumber)
