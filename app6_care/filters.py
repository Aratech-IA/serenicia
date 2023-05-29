import django_filters
from django.contrib.auth.models import User
from django.contrib.postgres.forms import RangeWidget
from django.forms import forms
from django_filters import DateFromToRangeFilter, ModelChoiceFilter, DateRangeFilter
from datetime import datetime, timedelta

from django.utils.translation import gettext_lazy as _

from app6_care.models import Intervention, TaskLevel1, TaskLevel2, TaskLevel4, InterventionDetail


class ASInterventionFilter(django_filters.FilterSet):
    # type = ModelChoiceFilter(queryset=TaskLevel1.objects.filter(profession='AS'), label=_('level 1 AS'))
    # patient = ModelChoiceFilter(queryset=User.objects.filter(
    #     groups__permissions__codename='view_resident', is_active=True).exclude(
    #     profileserenicia__status='deceased').order_by('username'),
    #                             field_name='patient__last_name', to_field_name='last_name', label=_('resident'))
    # nurse = ModelChoiceFilter(queryset=User.objects.filter(groups__name='AS').order_by('last_name').values_list(
    #     'last_name', flat=True), label=_('nurse'))
    # date_range = DateRangeFilter(field_name='end', label=_('Dates'))

    # period = DateFromToRangeFilter(field_name='end', label=_('period'))
    # period = ModelChoiceFilter(**get_different_date(), label=_('date'))

    # class Meta:
    #     model = Intervention
    #     fields = ['type', 'patient', 'nurse']

    nurse = ModelChoiceFilter(queryset=User.objects.filter(groups__permissions__codename='view_AS').order_by('username')
                              , label=_('Caregiver'))
    patient = ModelChoiceFilter(queryset=User.objects.filter(groups__permissions__codename='view_residentehpad',
                                                             is_active=True).exclude(profileserenicia__status='deceased')
                                .order_by('username'), label=_('Resident'))
    date_range = DateRangeFilter(field_name='end', label=_('Dates'))

    class Meta:
        model = Intervention
        fields = ['type', 'profession']


qs = Intervention.objects.all()
