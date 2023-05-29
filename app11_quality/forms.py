from django import forms

from app11_quality.models import Protocol_list, Tag


class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ['name']


class ProtocolForm(forms.ModelForm):
    file = forms.FileField(
        widget=forms.ClearableFileInput(
            attrs={'class': "control-file", }))

    class Meta:
        model = Protocol_list
        fields = ['name', 'file']
