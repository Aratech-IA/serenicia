from django import template
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _

from app9_personnalized_project.models import Appointment

register = template.Library()


@register.filter
def get_item(value, arg):
    return value.get(arg)


@register.filter
def show_by_default(chapter, connected_user):
    return chapter.referees.filter(id__in=connected_user.groups.all()).exists()


@register.filter
def get_list_appointments(value, connected):
    return Appointment.objects.filter(planning_event=value.planning_event).exclude(profileserenicia=connected)\
        .order_by(Lower('profileserenicia__user__last_name'), Lower('profileserenicia__user__first_name'))


@register.filter
def relation_type_trad(rel_type):
    choices = {'parent': _('parent'), 'partner': _('partner'), 'ex_partner': _('ex partner'), 'spouse': _('spouse'),
               'ex_spouse': _('ex spouse')}
    return choices[rel_type]
