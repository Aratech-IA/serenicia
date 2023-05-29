from django import forms
from django.forms import ModelForm

from app4_ehpad_base.models import Photos
from app15_calendar.models import PlanningEvent


class UploadPhoto(ModelForm):
    file = forms.ImageField(widget=forms.ClearableFileInput(attrs={'class': 'd-none',
                                                                   'onchange': 'this.form.submit()',
                                                                   'id': 'activity_photo_btn'}))

    class Meta:
        model = Photos
        fields = ['file']


class CommentForm(ModelForm):
    event_comment = forms.CharField(widget=forms.Textarea())

    class Meta:
        model = PlanningEvent
        fields = ['event_comment']
