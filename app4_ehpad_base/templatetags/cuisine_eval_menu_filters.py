from django import template

register = template.Library()


@register.filter
def get_item(data, key):
    # print(data)
    # print(key)
    # return True
    return data.get(key)
