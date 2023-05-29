from django.conf import settings
from app1_base.models import Client


def get_domain(request):
    return {'DOMAIN': settings.DOMAIN.lower(), 'NOM_EHPAD': settings.NOM_EHPAD, 'IMG_LOGO': settings.IMG_LOGO, 'FACEBOOK': settings.FACEBOOK, 'SITE_INTERNET': settings.SITE_INTERNET}


def get_facial_reco_ip(request):
    return {'FACIAL_RECO_IP': settings.FACIAL_RECO_IP}


def get_debug_state(request):
    return {'DEBUG': settings.DEBUG}


def checkalerts(request):
    return {'ALERT': Client.objects.filter(alert__active=True).exists()}


def get_face_reco_status(request):
    return {'FACE_RECO': settings.FACE_RECO}


