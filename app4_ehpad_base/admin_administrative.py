from app1_base.models import User
from app4_ehpad_base.models import Invoice

from django import forms

from django.contrib import admin


# ----- INVOICE --------------------------------------------------------------------------------------------------------


class SearchAdminField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return "{} {}".format(obj.last_name, obj.first_name)


class InvoiceAdmin(admin.ModelAdmin):
    search_fields = [
        'user_resident__last_name', 'user_resident__first_name', 'name',
    ]
    list_display = [
        'name', 'user_resident', 'pub_date',
        'room', 'pk', 'added_by',
    ]
    list_filter = ('type',)
    radio_fields = {'type': admin.HORIZONTAL}
    exclude = ('added_by',)

    def room(self, obj=None):
        if obj.user_resident.profile.client:
            room_nb = obj.user_resident.profile.client.room_number
        else:
            room_nb = 0
        return f"{room_nb}"

    def save_model(self, request, obj, form, change):
        if not change:
            obj.added_by = request.user
            obj.save()

    def get_queryset(self, request):
        if request.user.is_superuser or request.user.has_perm('app0_access.view_manager'):
            return super(InvoiceAdmin, self).get_queryset(request)
        else:
            invoices = Invoice.objects.filter(added_by=request.user)
        return invoices

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'user_resident':
            return SearchAdminField(
                queryset=User.objects.filter(
                    groups__permissions__codename__in=['view_residentehpad', 'view_residentrss', ],
                    is_active=True).order_by('last_name')
            )
        return super(InvoiceAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)


# ----- DOCUMENTS ------------------------------------------------------------------------------------------------------


class DocumentAdmin(admin.ModelAdmin):
    search_fields = ['user_resident__last_name', 'user_resident__first_name']
    fieldsets = (
        (';)',
         {'fields': ('user_resident', 'document_type', 'file',)}
         ),
        ('Signer information if online signing is used:',
         {'fields': ('user_family', 'signature_date', 'signer_user_id',)}
         ),
        ('Document information if online signing is used:',
         {'fields': ('envelope_id', 'doc_id',)}
         ),
    )
    readonly_fields = [
        'envelope_id', 'doc_id',
        'signature_date', 'signer_user_id', 'user_family',
    ]
    list_display = ('user_resident', 'document_type', 'user_family',)
    list_filter = ('document_type',)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'user_resident':
            return SearchAdminField(
                queryset=User.objects.filter(
                    groups__permissions__codename__in=['view_residentehpad', 'view_residentrss', ]
                    , is_active=True).order_by('last_name')
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# ----- MUTUAL DOCUMENTS -----------------------------------------------------------------------------------------------


class MutualDocumentAdmin(admin.ModelAdmin):
    list_display = ['document_type']
    fieldsets = (
        ('Add document for all user',
         {'fields': ('file', 'document_type', 'added_date',)}
         ),
    )


# ----- MUTUAL DOCUMENTS -----------------------------------------------------------------------------------------------


class PersonalizedDocAdmin(admin.ModelAdmin):
    list_display = ['user', 'document_type']
    search_fields = ['document_type', 'user', ]
    fieldsets = (
        ('Personalized document',
         {'fields': ('file', 'document_type', 'user',)}
         ),
    )
    readonly_fields = ['file', 'document_type', 'user', ]


# ----- CARDS ----------------------------------------------------------------------------------------------------------


class CardAdmin(admin.ModelAdmin):
    search_fields = (
        'user_resident__last_name', 'user_resident__first_name',
        'user_resident__profile__client__room_number'
    )
    list_display = ('resident',)
    ordering = ('user_resident__last_name',)

    def resident(self, obj=None):
        if obj.user_resident.profile.client:
            room_nb = obj.user_resident.profile.client.room_number
        else:
            room_nb = 0
        return "{} {} ({})".format(
            obj.user_resident.last_name,
            obj.user_resident.first_name,
            room_nb
        )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'user_resident':
            return SearchAdminField(
                queryset=User.objects.filter(
                    groups__permissions__codename__in=['view_residentehpad', 'view_residentrss', ]
                    , is_active=True).order_by('last_name')
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# ----------------------------------------------------------------------------------------------------------------------


class KitAdmin(admin.ModelAdmin):
    list_display = ('user_resident',)
    fieldsets = (
        ('~(^-^)~',
         {'fields': ('user_resident', 'nurses', 'creation_date')}
         ),
        ('Laundry Information',
         {'fields': ('laundry_labeled', 'laundry_washed',)}
         ),
        ('Equipment',
         {'fields': ('dental_equipment', 'hearing_equipment', 'cane',
                     'walker', 'glasses', 'wheelchair',)}
         ),
        ('Clothes',
         {'fields': ('pull', 'jacket', 'sweater_long',
                     'sweater_short', 'pants',
                     'socks', 'slipper', 'summer_shoe',
                     'winter_shoe', 'bra', 'underwear',
                     'nightdress', 'dressing_gown', )}
         ),
    )
    readonly_fields = ['user_resident', 'nurses',]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'user_resident':
            return SearchAdminField(
                queryset=User.objects.filter(
                    groups__permissions__codename__in=['view_residentehpad', 'view_residentrss', ]
                    , is_active=True).order_by('last_name')
            )
        return super(KitAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)


class DietAdmin(admin.ModelAdmin):
    list_display = ('user_resident',)
    readonly_fields = ['user_resident', 'type_diet', 'food_option', 'allergies']
