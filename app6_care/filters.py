import django_filters
from django.contrib.auth.models import User
from django.contrib.postgres.forms import RangeWidget
from django.forms import forms
from django_filters import DateFromToRangeFilter, ModelChoiceFilter, DateRangeFilter
from datetime import datetime, timedelta

from django.utils.translation import gettext_lazy as _

from app6_care.models import Intervention, TaskLevel1, TaskLevel2, TaskLevel4, InterventionDetail


class ASInterventionFilter(django_filters.FilterSet):

    nurse = ModelChoiceFilter(queryset=User.objects.filter(groups__permissions__codename='view_AS').order_by('username'), label=_('Caregiver'))
    patient = ModelChoiceFilter(queryset=User.objects.filter(groups__permissions__codename='view_residentehpad', is_active=True).exclude(profileserenicia__status='deceased').order_by('username'), label=_('Resident'))
    date_range = DateRangeFilter(field_name='end', label=_('Dates'))

    class Meta:
        model = Intervention
        fields = ['type', 'profession']


qs = Intervention.objects.all()
