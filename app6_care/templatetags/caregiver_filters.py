from urllib.parse import unquote

from django import template
from django.db.models.functions import Lower
from datetime import datetime, timedelta

from django.urls import reverse
from django.utils import timezone

register = template.Library()


@register.filter
def get_keyvalue(dict, key):
    return dict.get(key)


@register.filter
def care_plan_only(queryset):
    return queryset.filter(care_plan=True).order_by(Lower('name'))


@register.filter
def is_now(date):
    now = timezone.now()
    date_to_compare = datetime.combine(date=now, time=date.time(), tzinfo=date.tzinfo)
    if date_to_compare <= now < date_to_compare + timedelta(minutes=30):
        return True


@register.filter
def btn_grp_id_concat(base, add):
    return f'{base}-{add}'


@register.filter
def unquote_raw(value):
    return unquote(value)
