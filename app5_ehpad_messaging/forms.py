from django import forms
from django.db.models.functions import Lower

from django.db.models import Q
from app1_base.models import Profile
from app4_ehpad_base.models import ProfileSerenicia, ProfileEhpad

from django.contrib.auth.models import User, Group
from django.contrib.auth.forms import UserCreationForm

from django.utils.translation import gettext_lazy as _


class SignUpFormResident(UserCreationForm):

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name',
            'email'
        ]

    first_name = forms.CharField(
        label=_("First Name"),
        widget=forms.TextInput(
            attrs={
                'class': 'CharInput form-control mt-0',
            }
        )
    )

    last_name = forms.CharField(
        label=_("Last Name"),
        widget=forms.TextInput(
            attrs={
                'class': 'CharInput form-control mt-0',
            }
        )
    )

    email = forms.EmailField(
        label=_("Email"),
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'CharInput form-control',
                'type': 'email',
            }
        )
    )


class SignUpFormFamily(UserCreationForm):

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name',
            'email', 'password1', 'password2'
        ]

    first_name = forms.CharField(
        label=_("First Name"),
        widget=forms.TextInput(
            attrs={
                'class': 'CharInput form-control mt-0',
            }
        )
    )

    last_name = forms.CharField(
        label=_("Last Name"),
        widget=forms.TextInput(
            attrs={
                'class': 'CharInput form-control mt-0',
            }
        )
    )

    email = forms.EmailField(
        label=_("Email"),
        widget=forms.TextInput(
            attrs={
                'class': 'CharInput form-control mt-0',
                'type': 'email',
            }
        )
    )

    password1 = forms.CharField(
        label=_('Password'),
        help_text=_('at least 8 characters, including a minimum of 1 letter and 1 number'),
        widget=forms.PasswordInput(
            attrs={
                'class': 'input-text with-border form-control mt-0',
            }
        )
    )

    password2 = forms.CharField(
        label=_('Password Confirmation'),
        widget=forms.PasswordInput(
            attrs={
                'class': 'input-text with-border form-control mt-0',
            }
        )
    )


class SignUpFormEmployee(UserCreationForm):

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name',
            'email', 'password1', 'password2', 'group'
        ]

    first_name = forms.CharField(
        label=_("First Name"),
        widget=forms.TextInput(
            attrs={
                'class': 'CharInput form-control mt-0',
            }
        )
    )

    last_name = forms.CharField(
        label=_("Last Name"),
        widget=forms.TextInput(
            attrs={
                'class': 'CharInput form-control mt-0',
            }
        )
    )

    email = forms.EmailField(
        label=_("Email"),
        widget=forms.TextInput(
            attrs={
                'class': 'CharInput form-control mt-0',
                'type': 'email',
            }
        )
    )

    password1 = forms.CharField(
        label=_('Password'),
        help_text=_('at least 8 characters, including a minimum of 1 letter and 1 number'),
        widget=forms.PasswordInput(
            attrs={
                'class': 'input-text with-border form-control mt-0',
            }
        )
    )

    password2 = forms.CharField(
        label=_('Password Confirmation'),
        widget=forms.PasswordInput(
            attrs={
                'class': 'input-text with-border form-control mt-0',
            }
        )
    )

    group = forms.ModelChoiceField(
        label=_('Group choice'),
        required=True,
        queryset=Group.objects.filter(permissions__codename__in=['view_as', 'view_ash', 'view_ide', 'view_otheremployee', 'view_otherextern', 'view_praticians', 'view_manager']).order_by(Lower('name'))
    )


class ProfileSignUpForm(forms.ModelForm):

    class Meta:
        model = Profile
        fields = [
            "civility", "adress", "cp",
            "city", "phone_number"
        ]

    civility = forms.ChoiceField(
        label=_('Civility'),
        choices=Profile.CIVILITY_CHOICES,
        widget=forms.Select(
            attrs={
                'class': 'Select form-control',
            }
        )
    )

    adress = forms.CharField(
        label=_('Address'),
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'CharInput form-control mt-0',
            }
        )
    )

    cp = forms.CharField(
        label=_('Postal Code'),
        required=False,
        widget=forms.NumberInput(
            attrs={
                'class': 'NumberInput form-control mt-0',
            }
        )
    )

    city = forms.CharField(
        label=_('City'),
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'CharInput form-control mt-0',
            }
        )
    )

    phone_number = forms.CharField(
        label=_('Phone Number'),
        required=False,
        max_length=17,
        widget=forms.NumberInput(
            attrs={
                'class': 'NumberInput form-control mt-0',
                'type': 'tel',
            }
        )
    )


class ProfileSerenSignUpForm(forms.ModelForm):

    class Meta:
        model = ProfileSerenicia
        fields = ["birth_city", "birth_date", "family_bond"]

    birth_city = forms.CharField(
        label=_('City of Birth'),
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'CharInput form-control mt-0',
            }
        )
    )

    birth_date = forms.DateField(
        label=_('Date of Birth'),
        required=False,
        widget=forms.DateInput(
            format='%Y-%m-%d',
            attrs={
                'class': 'DateInput form-control mt-0',
                'type': 'date',
            }
        )
    )
    
    family_bond = forms.ChoiceField(
        label=_('Family bond'),
        required=False,
        choices=ProfileSerenicia.FAMILY_LINK_CHOICES,
        widget=forms.Select(
            attrs={
                'class': 'Select form-control',
            }
        )
    )


class ProfileEhpadForm(forms.ModelForm):
    """ Form for new user (family and employee), use the ProfileSerenicia table """

    class Meta:
        model = ProfileEhpad
        exclude = ['resident', ]

    wanted_placement = forms.ChoiceField(
        label=_('Wanted placement'),
        required=False,
        choices=ProfileEhpad.PLACEMENT_CHOICES,
        widget=forms.Select(
            attrs={
                'class': 'Select form-control',
            }
        )
    )

    wanted_entry_date = forms.DateField(
        label=_('Wanted entry date'),
        required=False,
        widget=forms.DateInput(
            format='%Y-%m-%d',
            attrs={
                'class': 'DateInput form-control mt-0',
                'type': 'date',
            }
        )
    )

    marital_status = forms.ChoiceField(
        label=_('Marital status'),
        choices=ProfileEhpad.SITUATION_CHOICES,
        widget=forms.Select(
            attrs={
                'class': 'Select form-control',
            }
        )
    )

    religion = forms.ChoiceField(
        choices=ProfileEhpad.RELIGION_CHOICES,
        widget=forms.Select(
            attrs={
                'class': 'Select form-control',
            }
        )
    )

    previous_profession = forms.CharField(
        label=_('Previous profession of resident'),
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'CharInput form-control mt-0',
            }
        )
    )


class ResidentDemandForm(forms.Form):
    last_name_of_resident = forms.CharField(
        label=_('Family name of your resident relative :'),
        widget=forms.TextInput(
            attrs={
                'class': 'CharInput form-control mt-0',
                'name': 'resident_last_name',
            }
        )
    )
    first_name_of_resident = forms.CharField(
        label=_('First Name of your resident relative :'),
        widget=forms.TextInput(
            attrs={
                'class': 'CharInput form-control mt-0',
                'name': 'resident_first_name',
            }
        )
    )


class ResidentForm(forms.ModelForm):
    """
    Creation of a new form for the registration of a resident. Must not be required username and email. Can't use
    NewUserForm(UserCreationForm)
    """

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name',
        ]

