from django.contrib.auth.models import User, Group
from django.db.models.signals import m2m_changed
from django.dispatch import receiver


@receiver(m2m_changed, sender=User.groups.through)
def group_check_is_staff_permission(instance, **kwargs):
    if isinstance(instance, User):
        User.objects.filter(pk=instance.pk).update(is_staff=instance.groups.filter(permissions__content_type__app_label='app0_access').exists())


@receiver(m2m_changed, sender=Group.permissions.through)
def permission_check_is_staff_permission(instance, **kwargs):
    if isinstance(instance, Group):
        User.objects.filter(groups=instance).update(is_staff=instance.permissions.exclude(content_type__app_label='app0_access').exists())
