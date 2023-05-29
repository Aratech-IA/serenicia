from django import template
from django.contrib import admin
from app1_base.forms import ResidenceForm

register = template.Library()


@register.simple_tag(takes_context=True)
def get_residence(context, **kwargs):
    residence_list = ResidenceForm(context['request'])
    return residence_list
