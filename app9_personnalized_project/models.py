from django.conf import settings
from django.contrib.auth.models import Group
from django.db import models
from django.db.models import Q
from django.utils import timezone

from django.utils.translation import gettext_lazy as _

from app4_ehpad_base.models import ProfileSerenicia
from app15_calendar.models import PlanningEvent
from app4_ehpad_base.validators import validate_file_extension


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
    UNIQUE_BOOL_CHOICES = ((None, _('No')),
                           (True, _('Yes')))
    number = models.IntegerField(verbose_name=_('Order'))
    title = models.CharField(max_length=200)
    referees = models.ManyToManyField(Group, blank=True, verbose_name=_('Concerned referees'))
    questions = models.ManyToManyField(Question, blank=True, verbose_name=_('Questions'))
    can_comment = models.BooleanField(default=True, verbose_name=_('Can add comment'))
    comment_title = models.CharField(max_length=200, blank=True, null=True, verbose_name=_('Comment title'))
    select_meal_type = models.BooleanField(default=None, unique=True, null=True, blank=True,
                                           choices=UNIQUE_BOOL_CHOICES,
                                           help_text=_('Allows you to select the type of meal in this chapter'),
                                           verbose_name=_('Meal presentation'))

    def __str__(self):
        question_trad = _('questions')
        return f'{self.number} - {self.title} ({self.questions.count()} {question_trad})'

    class Meta:
        verbose_name = _('Chapter')
        ordering = ['number']


def get_localtime():
    return timezone.localtime()


class Survey(models.Model):
    target = models.ForeignKey(ProfileSerenicia, on_delete=models.CASCADE, verbose_name=_('Resident concerned'),
                               limit_choices_to=Q(user__groups__permissions__codename='view_residentehpad',
                                                  user__is_active=True), related_name='target_app8_sp')
    created_by = models.ForeignKey(ProfileSerenicia, on_delete=models.CASCADE, verbose_name=_('Created by'),
                                   limit_choices_to=Q(user__groups__permissions__codename='view_supportproject',
                                                      user__is_staff=True, user__is_active=True),
                                   related_name='created_by_app8_sp')
    title = models.CharField(max_length=200, blank=True, null=True, verbose_name=_('Title'))
    date = models.DateField(verbose_name=_('Date'), default=get_localtime)
    intro = models.CharField(max_length=1000, blank=True, null=True, verbose_name=_('Introduction'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is active'))
    is_public = models.BooleanField(default=True, verbose_name=_('Visible to the family'))
    chapters = models.ManyToManyField(Chapter, blank=True, verbose_name=_('Chapters'))
    filling_date = models.DateField(blank=True, null=True, verbose_name=_('Completed on'))

    class Meta:
        verbose_name = _('Survey')

    def __str__(self):
        chapter_trad = _('chapters')
        return f'{self.title} ({self.chapters.count()} {chapter_trad})'


class Notation(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    notation = models.ForeignKey(NotationChoices, on_delete=models.CASCADE)
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE)

    def __str__(self):
        return f'chapter : {self.chapter.number}, {self.question.text} : {self.notation.text}'


class SurveyResponse(models.Model):
    survey = models.ForeignKey(Survey, blank=True, on_delete=models.CASCADE)
    last_update = models.DateTimeField(auto_now=True, null=True)
    interviewee = models.ForeignKey(ProfileSerenicia, blank=True, on_delete=models.CASCADE,
                                    related_name='interviewee_app8_sp')
    notation = models.ManyToManyField(Notation, blank=True)


class ImportedProject(models.Model):
    target = models.OneToOneField(ProfileSerenicia, on_delete=models.CASCADE, verbose_name=_('Resident concerned'),
                                  limit_choices_to=Q(user__groups__permissions__codename='view_residentehpad',
                                                     user__is_active=True))
    date = models.DateField(verbose_name=_('Date'), help_text=_('Original creation date'))
    file = models.FileField(verbose_name=_('File'), upload_to='imported_SP/', validators=[validate_file_extension],
                            help_text=_('PDF file only'))

    def __str__(self):
        return f'{self.target} - {self.date}'

    class Meta:
        verbose_name = _('Project importation')


class Comment(models.Model):
    text = models.CharField(max_length=2500, blank=True, null=True)
    chapter = models.ForeignKey(Chapter, blank=True, null=True, on_delete=models.CASCADE)
    surveyresponse = models.ForeignKey(SurveyResponse, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('chapter', 'surveyresponse')


APPOINTMENT_TYPE_CHOICES = (('support_project', _('Support project')),
                            ('demo', _('Demonstration')))


class AppointmentSlot(models.Model):
    DAY_CHOICES = (
        (0, _('Monday')),
        (1, _('Tuesday')),
        (2, _('Wednesday')),
        (3, _('Thursday')),
        (4, _('Friday')),
        (5, _('Saturday')),
        (6, _('Sunday'))
    )
    type = models.CharField(choices=APPOINTMENT_TYPE_CHOICES, max_length=20)
    day = models.IntegerField(choices=DAY_CHOICES, verbose_name=_('Weekday'))
    start = models.TimeField(verbose_name=_('Start time'))
    end = models.TimeField(verbose_name=_('End time'))

    class Meta:
        verbose_name = _('Appointment slot')
        verbose_name_plural = _('Appointment slots')

    def __str__(self):
        return f'{self.DAY_CHOICES[self.day][1]} / {self.start} - {self.end}'


class Appointment(models.Model):
    profileserenicia = models.ForeignKey(ProfileSerenicia, on_delete=models.CASCADE)
    planning_event = models.ForeignKey(PlanningEvent, on_delete=models.CASCADE, null=True)
    by_video = models.BooleanField(default=False)
    confirmed = models.BooleanField(default=False)
    rejected = models.BooleanField(default=False)
    owner = models.BooleanField(default=False)


class Unavailability(models.Model):
    type = models.CharField(choices=APPOINTMENT_TYPE_CHOICES, max_length=20)
    start = models.DateField(verbose_name=_('Start day'))
    end = models.DateField(verbose_name=_('End day'))

    class Meta:
        verbose_name = _('Unavailability')
        ordering = ('start', 'end')

    def __str__(self):
        return f'{self.start} - {self.end}'


class StoryLifeTitle(models.Model):
    title = models.CharField(max_length=200, verbose_name=_('Title'))
    example = models.TextField(blank=True, null=True, verbose_name=_('Example'))

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = _('Life story')
        verbose_name_plural = _('Life stories')


class StoryLife(models.Model):
    resident = models.ForeignKey(ProfileSerenicia, on_delete=models.CASCADE)
    title = models.ForeignKey(StoryLifeTitle, on_delete=models.CASCADE)
    text = models.TextField(blank=True, null=True)
    cannot_answer = models.BooleanField(default=False)


class Person(models.Model):
    GENDER_CHOICES = ((0, _('Male')),
                      (1, _('Feminine')))
    photo = models.ImageField(upload_to='app9_personnalized_project/genosociagram/', blank=True)
    level_y = models.SmallIntegerField(null=True, default=0)
    level_x = models.SmallIntegerField(null=True, default=0)
    family = models.ForeignKey(ProfileSerenicia, on_delete=models.CASCADE)
    last_name = models.CharField(max_length=50, null=True, blank=True, verbose_name=_('Last name'))
    first_name = models.CharField(max_length=50, null=True, blank=True, verbose_name=_('First name'))
    gender = models.PositiveSmallIntegerField(choices=GENDER_CHOICES, verbose_name=_('Gender'))
    birth = models.DateField(null=True, blank=True)
    death = models.DateField(null=True, blank=True)
    deceased = models.BooleanField(default=False, verbose_name=_('Deceased'))
    comment = models.TextField(null=True, blank=True)

    def get_full_name(self):
        return f'{self.first_name} {self.last_name}'

    def get_photo_url(self):
        if not self.photo:
            return settings.STATIC_URL + 'app1_base/img/bi/person-circle.svg'
        else:
            return self.photo.url

    def save(self, *args, **kwargs):
        if self.death:
            self.deceased = True
        super(Person, self).save(*args, **kwargs)

    def __str__(self):
        return f'{self.first_name} {self.last_name}'


class Relation(models.Model):
    TYPE_CHOICES = (('parent', _('Parent')),
                    ('child', _('Child')),
                    ('partner', _('Partner')),
                    ('spouse', _('Spouse')),
                    ('ex_partner', _('Ex partner')),
                    ('ex_spouse', _('Ex spouse')))
    QUALITY_CHOICES = (('normal', _('Good')),
                       ('good', _('Fusional')),
                       ('bad', _('Conflicting')))
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='parent')
    from_person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='from_person')
    to_person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='to_person')
    quality = models.CharField(max_length=20, choices=QUALITY_CHOICES, default='normal')
    other = models.BooleanField(default=False)

    class Meta:
        unique_together = ('from_person', 'to_person', 'other')

    def __str__(self):
        return f'from {self.from_person} to {self.to_person} : {self.type}'
