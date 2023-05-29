from app1_base.models import Profile
from app4_ehpad_base.models import ProfileSerenicia

from django import forms
from django.contrib.auth.models import User


# USER FORM ------------------------------------------------------------------------------------------------------------


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'email', 'username',
            'first_name', 'last_name'
        ]


class ProfileSereniciaForm(forms.ModelForm):
    class Meta:
        model = ProfileSerenicia
        fields = [
            'birth_date', 'birth_city', 'family_bond'
        ]


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            'photo', 'phone_number', 'adress',
            'cp', 'civility', 'city'
        ]
