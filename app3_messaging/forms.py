from django import forms
from app3_messaging.models import CreateEmail, IntraEmail, Campaign, CustomGroup
from app3_messaging.validators import validate_image
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


class CreateEmailForm(forms.ModelForm):
    class Meta:
        model = CreateEmail
        fields = ("nom_du_mail_type",)
        widgets = {
            'nom_du_mail_type': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '30'})
        }
        labels = {'nom_du_mail_type': _('Name of the preset')}


class CreateCampaignForm(forms.ModelForm):
    class Meta:
        model = Campaign
        fields = ("nom_de_la_campagne",)
        widgets = {
            'nom_de_la_campagne': forms.TextInput(attrs={'class': 'form-control',
                                                         'id': 'campagne_name',
                                                         'maxlength': '120'})
        }
        labels = {'nom_de_la_campagne': _('Name of the campaign')}


class IntraEmailAttachmentForm(forms.ModelForm):
    class Meta:
        model = IntraEmail
        fields = ("attachment",)

    attachment = forms.FileField(
        validators=[validate_image],
        label='',
        widget=forms.ClearableFileInput(attrs={'class': 'FileInputField d-none', 'multiple': True, 'id': 'fileUpload'}),
        required=False,
    )


class SignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True, help_text='', widget=forms.TextInput(
        attrs={'class': 'CharInput form-control',
               'id': 'firstName'}))
    last_name = forms.CharField(max_length=30, required=True, help_text='', widget=forms.TextInput(
        attrs={'class': 'CharInput form-control',
               'id': 'lastName'}))
    email = forms.EmailField(max_length=254, required=True, help_text='', widget=forms.TextInput(
        attrs={'class': 'CharInput form-control',
               'id': 'email'}))
    password1 = forms.CharField(label=_('Password') + ":", required=True,
                                help_text=_('at least 8 characters, including a minimum of 1 letter and 1 number '),
                                widget=forms.PasswordInput(
                                    attrs={'class': 'input-text with-border form-control',
                                           'id': 'password1',
                                           'placeholder': ''}))
    password2 = forms.CharField(label=_('Confirm password') + ":", required=True,
                                help_text='',
                                widget=forms.PasswordInput(
                                    attrs={'class': 'input-text with-border form-control',
                                           'id': 'password2',
                                           'placeholder': ''}))

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'password1', 'password2',)


class CustomGroupCreation(forms.ModelForm):
    name = forms.CharField(label='', required=True, help_text='',
                           widget=forms.TextInput(attrs={'placeholder': _('New group name')}))

    class Meta:
        model = CustomGroup
        fields = ('name',)
