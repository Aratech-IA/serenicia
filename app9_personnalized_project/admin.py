from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth.models import Group
from django.db.models.functions import Lower
from django.forms import ModelMultipleChoiceField
from django.utils import timezone

from django.utils.translation import gettext_lazy as _

from app4_ehpad_base.models import ProfileSerenicia
from app9_personnalized_project.models import NotationChoices, Question, Chapter, Survey, AppointmentSlot, Unavailability, StoryLifeTitle, \
    ImportedProject


@admin.action(description=_('Duplicate selected projects'))
def duplicate_survey(modeladmin, request, queryset):
    for survey in queryset:
        chapters = survey.chapters.all()
        survey.pk = None
        survey._state.adding = True
        survey.title = survey.title + ' (' + _('copy') + ')'
        survey.filling_date = None
        survey.date = timezone.localdate()
        survey.save()
        survey.chapters.set(chapters)


@admin.action(description=_('Deactivate selected projects'))
def deactivate_survey(modeladmin, request, queryset):
    queryset.update(is_active=False)


@admin.action(description=_('Activate selected projects'))
def activate_survey(modeladmin, request, queryset):
    queryset.update(is_active=True)


@admin.action(description=_('Duplicate selected projects for each resident'))
def duplicate_survey_for_each(modeladmin, request, queryset):
    for survey in queryset:
        list_resident = ProfileSerenicia.objects.filter(user__groups__permissions__codename='view_residentehpad',
                                                        user__is_active='True').exclude(id=survey.target.id)
        for resident in list_resident:
            if not Survey.objects.filter(target=resident, title=survey.title, date=survey.date).exists():
                chapters = survey.chapters.all()
                survey.pk = None
                survey._state.adding = True
                survey.target = resident
                survey.save()
                survey.chapters.set(chapters)


class NotationAdmin(admin.ModelAdmin):
    model = NotationChoices
    list_display = ['text', 'value']
    list_display_links = ['value', 'text']
    list_filter = ['value']


class NotationTabular(admin.TabularInline):
    model = Question.notation_choices.through
    extra = 0


class QuestionAdmin(admin.ModelAdmin):
    def notation_count(self, obj):
        return obj.notation_choices.count()

    notation_count.short_description = _('Number of possible responses')
    model = Question
    exclude = ['notation_choices']
    inlines = [NotationTabular]
    list_display = ['number', 'text', 'notation_count']
    list_display_links = ['number', 'text']
    list_filter = ['number']


class QuestionTabular(admin.TabularInline):
    model = Chapter.questions.through
    extra = 0


class ManyFieldsGroup(ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return obj.name


class ChapterAdmin(admin.ModelAdmin):
    def questions_count(self, obj):
        return obj.questions.count()

    questions_count.short_description = _('Number of question')
    model = Chapter
    exclude = ['questions']
    inlines = [QuestionTabular]
    list_display = ['number', 'title', 'can_comment', 'questions_count']
    list_display_links = ['number', 'title']
    list_filter = ['can_comment']

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'referees':
            kwargs['queryset'] = Group.objects.order_by(Lower('name'))
            kwargs['widget'] = FilteredSelectMultiple(db_field.verbose_name, is_stacked=False)
            kwargs['required'] = False
            kwargs['label'] = _('Referees')
            form_field = ManyFieldsGroup(**kwargs)
            return form_field
        return super().formfield_for_manytomany(db_field, request, **kwargs)


class ChapterTabular(admin.TabularInline):
    model = Survey.chapters.through
    extra = 0


class SurveyAdmin(admin.ModelAdmin):
    model = Survey
    actions = [duplicate_survey, deactivate_survey, activate_survey, duplicate_survey_for_each]
    list_display = ['title', 'target', 'is_active', 'is_public', 'date', 'filling_date']
    list_filter = ['created_by', 'is_active', 'is_public']
    search_fields = ['title', 'target__user__last_name', 'target__user__first_name']
    readonly_fields = ['filling_date',]
    exclude = ['chapters', 'is_support_project']
    inlines = [ChapterTabular]
    ordering = ['target__user__last_name', '-filling_date']

    def get_form(self, request, obj=None, change=False, **kwargs):
        kwargs['widgets'] = {'intro': forms.Textarea}
        return super(SurveyAdmin, self).get_form(request, obj, change, **kwargs)


class AppointmentAdmin(admin.ModelAdmin):
    model = AppointmentSlot
    list_display = ['day', 'start', 'end']
    list_filter = ['type', 'day']
    ordering = ['day', 'start']


class UnavailabilityAdmin(admin.ModelAdmin):
    model = Unavailability
    list_display = ['type', 'start', 'end']
    list_filter = ['type']

    def get_queryset(self, request):
        return super(UnavailabilityAdmin, self).get_queryset(request).filter(start__gte=timezone.localtime())


admin.site.register(Survey, SurveyAdmin)
admin.site.register(Chapter, ChapterAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(NotationChoices, NotationAdmin)
admin.site.register(AppointmentSlot, AppointmentAdmin)
admin.site.register(Unavailability, UnavailabilityAdmin)
admin.site.register(StoryLifeTitle)
admin.site.register(ImportedProject)
