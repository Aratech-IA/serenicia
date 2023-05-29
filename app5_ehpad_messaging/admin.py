from django.contrib import admin
from app5_ehpad_messaging.models import TempAssignation


class TempAssignAdmin(admin.ModelAdmin):
    exclude = ('demander',)
    readonly_fields = ('The_demander', 'date_demand')

    def The_demander(self, obj):
        return f"{obj.demander.last_name} {obj.demander.first_name}"


admin.site.register(TempAssignation, TempAssignAdmin)
