from django.utils import timezone
from app3_messaging.models import Intermediate, Notification
from datetime import timedelta
from django.utils.decorators import async_only_middleware
from asgiref.sync import sync_to_async


def _middelware(request):  # sync code
    request.session["urgent_msg"] = False
    unopened_messages = Intermediate.objects.filter(recipient=request.user.id).filter(date_opened__isnull=True).exclude(
        user_type='sender').values_list('message', flat=True)
    old_message = Intermediate.objects.filter(message__in=unopened_messages,user_type='sender',
                                              recipient__groups__permissions__codename='view_family',
                                              message__date_sent__lt=timezone.now()-timedelta(days=1))
    request.session["urgent_msg"] = old_message.count() > 0
    request.session["unopened_messages"] = unopened_messages.count()
    unopened_notifs = Notification.objects.filter(recipients=request.user.id).exclude(list_opened=request.user.id)
    request.session["unopened_notifs"] = unopened_notifs.count()
    return request


@async_only_middleware
def middleware_msg_notif(get_response):
    # One-time configuration and initialization goes here.
    async def middleware(request):
        request = await sync_to_async(_middelware)(request)
        response = await get_response(request)
        return response
    return middleware

# middleware_msg_notif(f) retourne une fonction qui prend en paramètre request et qui retourne l'évaluation de
# middelware f(request).   le code dans middelware est donc exécuté et le retour est le résultat de f(request).
