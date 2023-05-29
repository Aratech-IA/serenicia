# -*- coding: utf-8 -*-
"""
Created on Tue Mar 13 12:32:32 2018

@author: julien
"""

from django import forms
from .models import Alert, Camera, DAY_CHOICES, Client, ProfileSecurity, Preferences, AlertStuffsChoice
from django.utils.translation import gettext_lazy as _
from datetime import datetime, timedelta
import pytz


class AlertForm(forms.ModelForm):

    camera = forms.ModelMultipleChoiceField(queryset=None, widget=forms.CheckboxSelectMultiple, required=False)
    stuffs_char_foreign = forms.ModelChoiceField(queryset=None, required=True)

    def __init__(self, *args, **kwargs):
        client = kwargs.pop('client')
        super().__init__(*args, **kwargs)
        self.fields['camera'].queryset = Camera.objects.filter(client=client, active=True, active_automatic=True)
        self.fields['stuffs_char_foreign'].queryset = AlertStuffsChoice.objects.filter(client=client)

    class Meta:
        model = Alert
        fields = ['camera', 'stuffs_char_foreign', 'actions_char', 'sms', 'telegram', 'call', 'alarm', 'mail', 'mass_alarm']
        widgets = {
            'actions_char': forms.RadioSelect(), }


class FilterForm(AlertForm):
    stuffs_char_foreign = forms.ModelChoiceField(queryset=None, required=False)


HOUR_CHOICES = [(i, str(i)) for i in range(24)]

MIN_CHOICES = ((0, '0'), 
               (5, '5'),
               (10, '10'),
               (15, '15'),
               (20, '20'),
               (25, '25'),
               (30, '30'),
               (35, '35'),
               (40, '40'),
               (45, '45'),
               (50, '50'),
               (55, '55'),
               )
ACTION_CHOICES = (('start', _('Start')),
                  ('stop', _('Stop')),
                  )


class AutomatForm(forms.Form):
    day = forms.ChoiceField(choices=DAY_CHOICES)
    hour = forms.ChoiceField(choices=HOUR_CHOICES)
    minute = forms.ChoiceField(choices=MIN_CHOICES)
    action = forms.ChoiceField(choices=ACTION_CHOICES)


class ArchiveForm(forms.Form):
    
    camera = forms.ModelChoiceField(queryset=None, required=True, initial=0)

    def __init__(self, request, *args, **kwargs):
        super(ArchiveForm, self).__init__(*args, **kwargs)
        self.fields['hour'] = forms.ChoiceField(label='Archive', choices=self.list_hours(request))
        self.fields['minute'] = forms.ChoiceField(label='Minute', choices=self.list_minutes())
        self.fields['camera'].queryset = Camera.objects.filter(client=request.session.get('client'), active=True,
                                                               active_automatic=True)

    def list_hours(self, request):
        hours_back = [datetime.now(pytz.utc) - timedelta(hours=i) for i in range(48)]
        hours_back_local = [(t.strftime("%d:%m:%H"), t.astimezone(pytz.timezone(
            request.session.get('django_timezone'))).strftime("%d-%m-%Y  %H ")+'h') for t in hours_back]
        return hours_back_local

    def list_minutes(self):
        return [(i, i) for i in range(60)]

    class Meta:
        fields = ['camera']


class ResidenceForm(forms.Form):
    residence = forms.ModelChoiceField(queryset=None, required=True, initial=0)

    def __init__(self, request, *args, **kwargs):
        super(ResidenceForm, self).__init__(*args, **kwargs)
        queryset = Client.objects.filter(profilesecurity__in=ProfileSecurity.objects.filter(user=request.user))
        self.fields['residence'].queryset = queryset
        try:
            self.fields['residence'].initial = request.session['client']
        except KeyError:
            pass
        self.len = len(queryset)


class PreferencesForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(PreferencesForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            if visible.field.widget.input_type == 'checkbox':
                visible.field.widget.attrs['class'] = 'form-check-input'

    class Meta:
        model = Preferences
        exclude = ['profile']
