from django import template
from django.db.models.query import QuerySet

register = template.Library()


### Filters ###
@register.filter
def progress_percent(value, arg):
    if type(arg) == QuerySet or type(arg) == list:
        arg = len(arg)
    if type(value) == QuerySet or type(value) == list:
        value = len(value)
    try:
        computed = int(value / (arg/100))
    except ZeroDivisionError:
        computed = value
    return computed


@register.filter
def get_x_amount(value, arg):
    result = value[:arg]
    return result


@register.filter
def get_inter_of_x(value, arg):
    if value:
        if arg == 'sender':
            result = value.intermediate_set.get(user_type='sender').recipient
        else:
            result = value.intermediate_set.get(recipient=arg.id)
        return result


@register.filter
def get_ids(query):
    return list(query.values_list('id', flat=True))