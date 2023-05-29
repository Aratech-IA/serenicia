from django import template
from app8_survey.models import Survey, SurveyResponse, Comment

register = template.Library()


@register.filter
def display_target(target):
    for choice in Survey.TARGET_CHOICES:
        if choice[0] == target:
            return choice[1]


@register.filter
def display_type(value):
    for choice in Survey.TYPE_CHOICES:
        if choice[0] == value:
            return choice[1]


@register.simple_tag
def answer_count(survey, chapter, question, notation):
    result = SurveyResponse.objects.filter(survey=survey, notation__chapter=chapter, notation__question=question,
                                           notation__notation=notation, filling_date__isnull=False).count()
    if result > 0:
        return result
    else:
        return ''


@register.simple_tag
def get_comment(chapter):
    return Comment.objects.filter(chapter=chapter)
