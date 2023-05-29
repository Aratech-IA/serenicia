from django import template
from app1_base.models import CLIENT_SHOWER, CLIENT_HELPER, BED_CHOICES

register = template.Library()


@register.filter
def showerdisplay(shower):
    for choice in CLIENT_SHOWER:
        if choice[0] == shower:
            return choice[1]


@register.filter
def aidedisplay(aid):
    for choice in CLIENT_HELPER:
        if choice[0] == aid:
            return choice[1]


@register.filter
def beddisplay(lit):
    for choice in BED_CHOICES:
        if choice[0] == lit:
            return choice[1]


@register.filter
def ws_url_client_in_alert(meta, host):
    return 'wss://' + host + ':' + meta.get('SERVER_PORT') + '/ws_client_in_alert/'
    
