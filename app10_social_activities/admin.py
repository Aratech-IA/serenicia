from datetime import timedelta

from django.contrib import admin
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.db.models.functions import Lower
from django.forms.models import ModelChoiceField
from django.utils import timezone

from app10_social_activities.models import Question, Report

from django.utils.translation import gettext_lazy as _

from app4_ehpad_base.admin import ManyFieldsUser
from app4_ehpad_base.models import ProfileSerenicia
from app15_calendar.models import PlanningEvent, Recurrence, Event, Location


class App10QuestionsAdmin(admin.ModelAdmin):
    model = Question
    list_display = ('order', 'text', 'subject', 'is_active')
    list_filter = ('subject', 'is_active')
    list_display_links = ('order', 'text')


class PlanningEventInline(admin.StackedInline):
    model = PlanningEvent
    exclude = ('gg_event_id', 'attendance', 'thumbnail_url', 'blog_post')
    verbose_name = _('Planning')
    verbose_name_plural = _('Planning')
    max_num = 3

    def get_queryset(self, request):
        event = request.resolver_match.kwargs.get('object_id')
        qs = super(PlanningEventInline, self).get_queryset(request=request).filter(start__date__gte=timezone.localdate(),
                                                                                   event=event)
        try:
            # affichage des 3 prochaine semaines
            third_instance = qs[2]
            return qs.filter(start__lte=third_instance.start)
        except IndexError:
            return qs

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'participants':
            kwargs['queryset'] = ProfileSerenicia.objects.filter(
                user__groups__permissions__codename__in=['view_residentehpad', ['view_residentrss'], ],
                user__is_active=True).order_by(Lower('user__last_name')).exclude(
                user__profileserenicia__status='deceased')
            kwargs['widget'] = FilteredSelectMultiple(db_field.verbose_name, is_stacked=False)
            kwargs['required'] = False
            form_field = ManyFieldsUser(**kwargs)
            return form_field
        return super().formfield_for_manytomany(db_field, request, **kwargs)


class RecurrenceInline(admin.TabularInline):
    model = Recurrence
    verbose_name = _('Recurrence')


class LabelFK(ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.user.last_name} {obj.user.first_name}"


class ActivityAdmin(admin.ModelAdmin):
    model = Event
    exclude = ('is_activity', 'is_visit', 'is_birthday')
    list_display = ('type', 'location', 'organizer', 'public')
    list_filter = ('public', 'location', 'organizer')
    list_display_links = ('type',)
    search_fields = ('type', 'location__name', 'planningevent__participants__user__last_name',
                     'planningevent__participants__user__first_name',
                     'planningevent__participants__user__profile__client__room_number')

    inlines = [RecurrenceInline, PlanningEventInline]

    def get_queryset(self, request):
        return super(ActivityAdmin, self).get_queryset(request).filter(is_activity=True)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'organizer':
            kwargs['queryset'] = ProfileSerenicia.objects.filter(user__is_active=True,
                                                                 user__groups__permissions__codename='view_animation',
                                                                 user__profile__advanced_user=False).order_by('user__last_name').distinct('user__last_name')
            form_field = LabelFK(**kwargs)
            return form_field
        return super(ActivityAdmin, self).formfield_for_foreignkey(db_field, request)

    def save_model(self, request, obj, form, change):
        obj.is_activity = True
        super(ActivityAdmin, self).save_model(request, obj, form, change)


class ReportAdmin(admin.ModelAdmin):
    model = Report
    list_display = ('event', 'year')
    list_filter = ('event', 'year')
    ordering = ('year', 'event')
    exclude = ('objectives', 'animator', 'location', 'day', 'start_time', 'end_time')


admin.site.register(Question, App10QuestionsAdmin)
admin.site.register(Event, ActivityAdmin)
admin.site.register(Location)
admin.site.register(Report, ReportAdmin)
