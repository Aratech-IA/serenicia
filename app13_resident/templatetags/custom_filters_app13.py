from django import template
from app1_base.models import Profile

register = template.Library()


@register.filter
def check_language(user):
    trad = Profile.objects.get(user=user)
    lang = trad.language
    return lang
