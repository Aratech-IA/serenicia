from datetime import timedelta, datetime

from django.dispatch import receiver
from django.db.models.signals import post_save, m2m_changed, post_delete
from django.utils import timezone

from app4_ehpad_base.models import ProfileSerenicia
from app15_calendar.models import Recurrence, PlanningEvent


def creation_recurrence(instance, start, end):
    while start.date() < instance.end:
        PlanningEvent.objects.create(event=instance.event, start=start, end=end)
        start += timedelta(weeks=1)
        end += timedelta(weeks=1)


def update_recurrence(instance, start, end):
    PlanningEvent.objects.filter(event=instance.event, end__date__gte=instance.end).delete()
    planningevents = PlanningEvent.objects.filter(event=instance.event, start__date__gte=end.date()).order_by('start')
    for pl_event in planningevents:
        pl_event.start = start
        pl_event.end = end
        pl_event.save()
        start = start + timedelta(weeks=1)
        end = end + timedelta(weeks=1)
    if start.date() < instance.end:
        creation_recurrence(instance, start, end)


@receiver(post_save, sender=Recurrence)
def recurrence_management(instance, created, **kwargs):
    monday = timezone.localtime().date() - timedelta(days=timezone.localtime().weekday())
    next_occurence = monday + timedelta(days=instance.day)
    start = datetime(year=next_occurence.year, month=next_occurence.month, day=next_occurence.day,
                     hour=instance.start_time.hour, minute=instance.start_time.minute,
                     tzinfo=timezone.localtime().tzinfo)
    end = datetime(year=next_occurence.year, month=next_occurence.month, day=next_occurence.day,
                   hour=instance.end_time.hour, minute=instance.end_time.minute,
                   tzinfo=timezone.localtime().tzinfo)
    if created:
        creation_recurrence(instance, start, end)
    else:
        update_recurrence(instance, start, end)


@receiver(post_delete, sender=Recurrence)
def delete_recurrence(instance, **kwargs):
    PlanningEvent.objects.filter(event=instance.event, start__date__gt=timezone.localdate()).delete()


@receiver(m2m_changed, sender=PlanningEvent.participants.through)
def update_participants_future_activity(instance, action, pk_set, **kwargs):
    if isinstance(instance, PlanningEvent) and (action == 'post_add' or action == 'post_remove'):
        if instance.end > timezone.localtime():
            next_event = PlanningEvent.objects.filter(event=instance.event,
                                                      start__gt=instance.start).order_by('start').first()
            if next_event:
                if action == 'post_add':
                    for pk in pk_set:
                        next_event.participants.add(ProfileSerenicia.objects.get(pk=pk))
                elif action == 'post_remove':
                    for pk in pk_set:
                        next_event.participants.remove(ProfileSerenicia.objects.get(pk=pk))
