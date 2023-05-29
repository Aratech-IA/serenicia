from django.db import models
from django.db.models import Q

from django.utils.translation import gettext_lazy as _

from app4_ehpad_base.models import ProfileSerenicia, BlogPost, MealBooking, Photos


class Location(models.Model):
    name = models.CharField(max_length=150)
    photo = models.ImageField(blank=True)

    class Meta:
        verbose_name = _('Place')
        verbose_name_plural = _('Places')

    def __str__(self):
        return f"{self.name}"


class Event(models.Model):
    type = models.CharField(max_length=100, verbose_name=_('Entitled'))
    location = models.ForeignKey(Location, models.SET_NULL, verbose_name=_('Location'), null=True, blank=True)
    organizer = models.ForeignKey(ProfileSerenicia, models.CASCADE,
                                  limit_choices_to=Q(user__is_active=True,
                                                     user__groups__permissions__codename='view_animation'),
                                  verbose_name=_('Organizer'), related_name='event_organizer')
    public = models.BooleanField(default=False, verbose_name=_('Public'),
                                 help_text=_('Select if the activity can be visible to everyone'))
    is_activity = models.BooleanField(default=False)
    is_visit = models.BooleanField(default=False)
    is_birthday = models.BooleanField(default=False)
    objective = models.TextField(null=True, blank=True, verbose_name=_('Objectives'))
    protected_unit_only = models.BooleanField(default=False, verbose_name=_('Protected unit'),
                                              help_text=_('Check if this activity is intended for the protected unit'))

    def __str__(self):
        return f'{self.type}'

    class Meta:
        verbose_name = _('Activity')
        verbose_name_plural = _('Activities')


DAY_CHOICES = (
    (0, _('Monday')),
    (1, _('Tuesday')),
    (2, _('Wednesday')),
    (3, _('Thursday')),
    (4, _('Friday')),
    (5, _('Saturday')),
    (6, _('Sunday'))
)


class Recurrence(models.Model):
    event = models.OneToOneField(Event, on_delete=models.CASCADE)
    start = models.DateField(verbose_name=_('Recurrence start'), null=True, blank=True,
                             help_text=_('Choose a recurrence start date'))
    end = models.DateField(verbose_name=_('Recurrence end'), null=True, blank=True,
                           help_text=_('Choose a recurrence end date'))
    start_time = models.TimeField(verbose_name=_('Start time'), help_text=_('Start of activity'))
    end_time = models.TimeField(verbose_name=_('End time'), help_text=_('End of the activity'))
    day = models.IntegerField(choices=DAY_CHOICES, verbose_name=_('Day'), help_text=_('Activity day'))

    def __str__(self):
        return f"{_('Repeats every week')}"


class PlanningEvent(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, null=True)
    start = models.DateTimeField(verbose_name=_('Beginning'))
    end = models.DateTimeField(verbose_name=_('End'), null=True)
    event_comment = models.CharField(max_length=1000, blank=True, help_text=_('optionnal comment'),
                                     verbose_name=_('Comment'))
    gg_event_id = models.CharField(max_length=100, unique=True, null=True)
    thumbnail_url = models.CharField(null=True, blank=True, max_length=200)
    blog_post = models.ForeignKey(BlogPost, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='pl_ev_blog_post')
    participants = models.ManyToManyField(
        ProfileSerenicia, limit_choices_to=Q(
            user__groups__permissions__codename__in=['view_residentehpad', 'view_residentrss', ],
            status='home', user__is_active=True),
        related_name='pl_ev_participants', verbose_name=_('Participants'), blank=True)
    attendance = models.ManyToManyField(
        ProfileSerenicia, limit_choices_to=Q
        (user__groups__permissions__codename__in=['view_residentehpad', 'view_residentrss', ],
         status='home', user__is_active=True),
        related_name='pl_ev_attendance_list', blank=True)

    class Meta:
        ordering = ('start',)


class PlanningEventBooking(models.Model):
    booking = models.OneToOneField(MealBooking, on_delete=models.CASCADE)
    planning_event = models.ForeignKey(PlanningEvent, models.CASCADE)


class PlanningEventPhotos(models.Model):
    photos = models.OneToOneField(Photos, on_delete=models.CASCADE)
    planning_event = models.ForeignKey(PlanningEvent, models.CASCADE)
