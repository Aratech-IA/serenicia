import datetime

from django import forms
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

from app6_care.models import TaskInTreatmentPlan, TaskLevel2


class TaskCommentForm(forms.Form):
    content = forms.CharField(max_length=1500, required=False, label=False, widget=forms.Textarea(
        attrs={'placeholder': _('Tape here your comment.')}))

    content.widget.attrs.update({'class': 'w-75'})


class FreeCommentForm(forms.Form):
    content = forms.CharField(max_length=1500, label=False, widget=forms.Textarea(attrs={
        'placeholder': _('Tape here your comment.')
    }))

    content.widget.attrs.update({'class': 'w-75'})


class InterventionReportForm(forms.Form):
    resident = forms.ModelChoiceField(queryset=User.objects.filter(
        groups__permissions__codename='view_residentehpad', is_active=True).exclude(
        profileserenicia__status='deceased'), label=_('Resident'),
        widget=forms.Select(attrs={"onchange": 'this.form.submit()'}))
    nurse = forms.ModelChoiceField(
        queryset=User.objects.filter(groups__name='AS'), label=_('Nurse'), widget=forms.Select(
            attrs={"onchange": 'this.form.submit()'}))
    start_date = forms.DateField(initial=datetime.datetime.today, label=_('From'))
    # to check : end_date should be older than start_date
    end_date = forms.DateField(initial=datetime.datetime.today, label=_('Until'))


class PlanDeSoinForm(forms.ModelForm):
    class Meta:
        model = TaskInTreatmentPlan
        fields = ["task_level_2", "start_time", "day_in_cycle"]
        HOUR_CHOICES = [(datetime.time(hour=x), '{:02d}:00'.format(x)) for x in range(0, 24)]
        widgets = {'start_time': forms.Select(choices=HOUR_CHOICES), 'day_in_cycle': forms.HiddenInput()}

