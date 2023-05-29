from django import template

from app16_portal.models import Key
from app16_portal.utils import sign_data, encode_data

register = template.Library()


@register.filter
def sign_encode(key):
    signed = sign_data({'token': key}, Key.objects.get(is_local=True, is_public=False).key_bytes())
    encoded = encode_data(signed)
    return encoded.decode('UTF-8')
