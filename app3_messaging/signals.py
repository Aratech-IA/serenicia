from django.db.models.signals import post_save
from django.dispatch import receiver

from app3_messaging.models import Intermediate
from app3_messaging.notifs import notif_message


@receiver(post_save, sender=Intermediate)
def send_notif_new_internal_message(instance, created, **kwargs):
    if instance.user_type != 'sender' and instance.recipient.profile.preferences.notif_all_new_msg \
            and not instance.recipient.profile.mailer_daemon and created:
        sender = Intermediate.objects.get(message=instance.message, user_type='sender').recipient
        notif_message([instance.recipient.email], sender, instance.message, instance.user_type)
