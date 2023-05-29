from django.db.models import Q
from django.utils import timezone

from app4_ehpad_base.models import ProfileSerenicia
from django.db import models
from django.utils.translation import gettext_lazy as _


class NotationChoices(models.Model):
    VALUE_CHOICE = (
        (0, 0),
        (1, 1),
        (2, 2),
        (3, 3),
        (4, 4),
        (5, 5),
        (6, 6),
        (7, 7),
        (8, 8),
        (9, 9),
        (10, 10)
    )
    value = models.IntegerField(choices=VALUE_CHOICE, verbose_name=_('Value'))
    text = models.CharField(max_length=50, verbose_name=_('Text'))

    class Meta:
        verbose_name = _('Notation')
        unique_together = ('value', 'text')
        ordering = ['value']

    def __str__(self):
        value_trad = _('value')
        return f'{self.text} - {value_trad} : {self.value}'


class Question(models.Model):
    number = models.IntegerField(verbose_name=_('Order'))
    text = models.CharField(max_length=200)
    notation_choices = models.ManyToManyField(NotationChoices, verbose_name=_('Possible answers'))

    def __str__(self):
        return f'{self.number} - {self.text}'

    class Meta:
        verbose_name = _('Question')
        ordering = ['number']


class Chapter(models.Model):
    number = models.IntegerField(verbose_name=_('Order'))
    title = models.CharField(max_length=200)
    questions = models.ManyToManyField(Question, blank=True, verbose_name=_('Questions'))
    can_comment = models.BooleanField(default=True, verbose_name=_('Can add comment'))
    comment_title = models.CharField(max_length=200, blank=True, null=True, verbose_name=_('Comment title'))

    def __str__(self):
        question_trad = _('questions')
        return f'{self.number} - {self.title} ({self.questions.count()} {question_trad})'

    class Meta:
        verbose_name = _('Chapter')
        ordering = ['number']


def get_year():
    return timezone.localtime().year


class Survey(models.Model):
    TYPE_CHOICES = (
        ('satisfaction', _('Satisfaction')),
        ('other', _('Other'))
    )
    TARGET_CHOICES = (
        ('family', _('Family')),
        ('resident', _('Resident')),
        ('employees', _('Employees')),
        ('referents', _('Referents'))
    )
    type = models.CharField(max_length=15, choices=TYPE_CHOICES, verbose_name=_('Survey type'))
    target = models.CharField(max_length=20, choices=TARGET_CHOICES, verbose_name=_('Target'))
    created_by = models.ForeignKey(ProfileSerenicia, on_delete=models.CASCADE, verbose_name=_('Created by'),
                                   limit_choices_to=Q(user__groups__permissions__codename='view_monavis',
                                                      user__is_active=True))
    title = models.CharField(max_length=200, blank=True, null=True, verbose_name=_('Title'))
    year = models.PositiveIntegerField(verbose_name=_('Year'), default=get_year)
    intro = models.CharField(max_length=1000, blank=True, null=True, verbose_name=_('Introduction'))
    chapters = models.ManyToManyField(Chapter, blank=True, verbose_name=_('Chapters'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is active'))

    def __str__(self):
        chapter_trad = _('chapters')
        return f'{self.title} ({self.chapters.count()} {chapter_trad})'

    class Meta:
        verbose_name = _('Survey')


class Notation(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    notation = models.ForeignKey(NotationChoices, on_delete=models.CASCADE)
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE)

    def __str__(self):
        return f'chapter : {self.chapter.number}, {self.question.text} : {self.notation.text}'


class SurveyResponse(models.Model):
    survey = models.ForeignKey(Survey, blank=True, on_delete=models.CASCADE)
    filling_date = models.DateField(blank=True, null=True)
    last_update = models.DateTimeField(blank=True, null=True)
    interviewee = models.ForeignKey(ProfileSerenicia, blank=True, on_delete=models.CASCADE)
    notation = models.ManyToManyField(Notation, blank=True)

    def __str__(self):
        filled_trad = _('filled')
        return f'{self.survey} - {filled_trad} : {self.filling_date}'


class Comment(models.Model):
    text = models.CharField(max_length=2000, blank=True, null=True)
    chapter = models.ForeignKey(Chapter, blank=True, null=True, on_delete=models.CASCADE)
    surveyresponse = models.ForeignKey(SurveyResponse, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('chapter', 'surveyresponse')
