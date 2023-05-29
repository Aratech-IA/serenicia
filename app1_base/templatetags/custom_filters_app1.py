from django import template

register = template.Library()


@register.filter
def sort_by_last_name(items, model_name):
    if model_name == 'profileserenicia':
        return sorted(items, key=lambda item: (item.user.last_name.lower(), item.user.first_name.lower()))
    elif model_name == 'user':
        return sorted(items, key=lambda item: (item.last_name.lower(), item.first_name.lower()))


@register.filter
def sort_groups_by_name(groups):
    return sorted(groups, key=lambda group: group.name.lower())
