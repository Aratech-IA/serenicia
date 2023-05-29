from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from app4_ehpad_base.models import ProfileSerenicia

from app15_calendar.models import PlanningEvent, Event, Location, DAY_CHOICES


def get_order():
    question = Question.objects.order_by('order').last()
    if question:
        return question.order + 1
    else:
        return 1


class Question(models.Model):
    SUBJECT_CHOICES = (('location', _('Place')),
                       ('organizer', _('Organizer')),
                       ('contents', _('Contents')))
    text = models.CharField(max_length=150, verbose_name=_('Text'))
    order = models.PositiveIntegerField(unique=True, default=get_order, verbose_name=_('Order'))
    is_active = models.BooleanField(default=True, verbose_name=_('Active'))
    subject = models.CharField(choices=SUBJECT_CHOICES, max_length=10, verbose_name=_('Subject'))

    class Meta:
        ordering = ('order',)
        verbose_name = _('Question')
        verbose_name_plural = _('Questions')

    def __str__(self):
        return f'{self.order} {self.subject} - {self.text} (active: {self.is_active})'


class Evaluation(models.Model):
    NOTE_CHOICES = ((1, 'very bad'),
                    (2, 'bad'),
                    (3, 'good'),
                    (4, 'very_good'))
    activity_new = models.ForeignKey(PlanningEvent, on_delete=models.CASCADE, null=True)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    note = models.IntegerField(choices=NOTE_CHOICES, null=True)
    voter = models.ForeignKey(ProfileSerenicia, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.question.text} : {self.note}'


def get_activity_photos_path(activity):
    result = f'activities/{activity.event.organizer.folder}/{activity.start.strftime("%Y-%m-%d")}_{activity.event.id}/'
    result = result.replace(' ', '_')
    return result


def upload_photo(instance, filename):
    upload_to = get_activity_photos_path(instance.activity_new)
    upload_to += filename
    return upload_to


class Photo(models.Model):
    activity_new = models.ForeignKey(PlanningEvent, on_delete=models.CASCADE, null=True)
    img = models.ImageField(upload_to=upload_photo)
    identified = models.ManyToManyField(ProfileSerenicia, blank=True, related_name='identified')


def get_current_year():
    return timezone.localdate().year


class Report(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, limit_choices_to=Q(is_activity=True),
                              verbose_name=_('Activity'))
    year = models.PositiveSmallIntegerField(default=get_current_year, verbose_name=_('Year'))
    result = models.TextField(blank=True, null=True, help_text=_('For the current year'), verbose_name=_('Results'))
    project = models.TextField(blank=True, null=True, help_text=_('For the following year'), verbose_name=_('Project'))
    objectives = models.TextField(blank=True, null=True, help_text=_('Objectives to date'),
                                  verbose_name=_('Objectives'))
    animator = models.ForeignKey(ProfileSerenicia, on_delete=models.SET_NULL, null=True, blank=True,
                                 verbose_name=_('Animator'))
    location = models.ForeignKey(Location, models.SET_NULL, null=True, blank=True, verbose_name=_('Location'))
    start_time = models.TimeField(verbose_name=_('Start time'), null=True, blank=True)
    end_time = models.TimeField(verbose_name=_('End time'), null=True, blank=True)
    day = models.IntegerField(choices=DAY_CHOICES, verbose_name=_('Day'), null=True, blank=True)

    def save(self, **kwargs):
        if self.event and self._state.adding:
            self.objectives = self.event.objective
            self.animator = self.event.organizer
            self.location = self.event.location
            if hasattr(self.event, 'recurrence'):
                self.start_time = self.event.recurrence.start_time
                self.end_time = self.event.recurrence.end_time
                self.day = self.event.recurrence.day
        return super(Report, self).save(**kwargs)

    def __str__(self):
        return f'{self.event} - {self.year}'

    class Meta:
        verbose_name = _('Report')
        unique_together = (('event', 'year'),)
