from django import forms
from django.contrib import admin

from django.utils.translation import gettext_lazy as _

from app8_survey.models import Survey, Chapter, Question, NotationChoices


@admin.action(description=_('Duplicate selected surveys'))
def duplicate_survey(modeladmin, request, queryset):
    for survey in queryset:
        chapters = survey.chapters.all()
        survey.pk = None
        survey._state.adding = True
        survey.title = survey.title + ' (' + _('copy') + ')'
        survey.save()
        survey.chapters.set(chapters)


@admin.action(description=_('Deactivate selected surveys'))
def deactivate_survey(modeladmin, request, queryset):
    queryset.update(is_active=False)


@admin.action(description=_('Activate selected surveys'))
def activate_survey(modeladmin, request, queryset):
    queryset.update(is_active=True)


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


class ChapterTabular(admin.TabularInline):
    model = Survey.chapters.through
    extra = 0


class SurveyAdmin(admin.ModelAdmin):
    model = Survey
    actions = [duplicate_survey, deactivate_survey, activate_survey]
    list_display = ['title', 'year', 'created_by', 'target', 'is_active']
    list_filter = ['year', 'created_by', 'target', 'is_active']
    ordering = ['-year']
    exclude = ['chapters', 'is_support_project']
    inlines = [ChapterTabular]

    def get_form(self, request, obj=None, change=False, **kwargs):
        kwargs['widgets'] = {'intro': forms.Textarea}
        return super(SurveyAdmin, self).get_form(request, obj, change, **kwargs)


admin.site.register(Survey, SurveyAdmin)
admin.site.register(Chapter, ChapterAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(NotationChoices, NotationAdmin)
