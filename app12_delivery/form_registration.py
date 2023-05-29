from django.contrib.auth.models import User

from django import forms
from django.utils.translation import gettext_lazy as _

from app1_base.models import Profile
from app4_ehpad_base.forms import create_username
from app12_delivery.models import ContractDelivery, DeliveryDay, CancelDelivery, WeekOfContract, MealsNumber


class UserRegisterDeliveryForm(forms.ModelForm):
    username = forms.CharField(widget=forms.HiddenInput(), required=False)
    password = forms.CharField(widget=forms.HiddenInput(), required=False)
    created_by = forms.CharField(widget=forms.HiddenInput(), required=False)
    first_name = forms.CharField(required=True, label=_("last name"), widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': _('Entry his last name')
    }))
    last_name = forms.CharField(required=True, label=_("first name"), widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': _('Entry his first name')
    }))
    email = forms.CharField(required=False, widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': _('Entry his mail')
    }))

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'username', 'password', 'created_by']

    def save(self):
        tmp_username = create_username(self.cleaned_data.get('first_name'), self.cleaned_data.get('last_name'))
        user, is_created = User.objects.get_or_create(username=tmp_username)
        if not is_created:
            return user, is_created
        user.set_password(user.username)
        user.first_name = self.cleaned_data.get('first_name')
        user.last_name = self.cleaned_data.get('last_name')
        user.email = self.cleaned_data.get('email')
        user.save()
        return user, is_created


class UserUpdateDeliveryForm(forms.ModelForm):
    username = forms.CharField(required=False, label=_("username"), widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': _('Entry his username')
    }))
    first_name = forms.CharField(required=True, label=_("last name"), widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': _('Entry his last name')
    }))
    last_name = forms.CharField(required=True, label=_("first name"), widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': _('Entry his first name')
    }))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': _('Entry his first name')
    }))

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'username']


class ProfileRegisterDeliveryForm(forms.ModelForm):
    # phone_regex = RegexValidator(regex=r'^[\+\d]\d{9,11}$',
    #                              message=_("Phone number must be entered in the format: \
    #                                            '+999999999'. Up to 15 digits allowed."))
    # validators=[phone_regex],
    phone_number = forms.CharField(max_length=17, label=_('Phone number'), widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': _('Entry his phone number')
    }))
    adress = forms.CharField(max_length=200, label=_('Address'), widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': _('Entry his address')
    }))
    cp = forms.CharField(max_length=200, label=_('postcode'), widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': _('Entry his postcode')
    }))
    city = forms.CharField(max_length=200, label=_('City'), widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': _('Entry his city')
    }))
    # adress_latitude = forms.CharField(widget=forms.HiddenInput(), required=False)
    # adress_longitude = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = Profile
        fields = ['phone_number', 'adress', 'cp', 'city']

    # def save(self, *args, **kargs):
    #     full_adress = self.cleaned_data['adress'] + "," + self.cleaned_data['city'] + "," + self.cleaned_data['cp']
    #     geolocator = Nominatim(user_agent="deliveryMeal")
    #     coordinates = geolocator.geocode(full_adress)
    #     self.adress_latitude = coordinates.latitude
    #     self.adress_longitude = coordinates.longitude
    #     super(ProfileRegisterDeliveryForm, self).save()


type_housing_choices = [
    ('house', 'Maison individuelle'),
    ('apartment', 'Appartement'),
]
payment_method_choices = [
    ('check', 'Chèque'),
    ('sampling', 'Prélèvement SEPA'),
]


# def validate_contract_date_is_external_other_contract(value):
#
#     if value % 2 != 0:
#         raise ValidationError(
#             _('contract exist in date %(value)'),
#             params={'value': value},
#         )

class ContractRegisterForm(forms.ModelForm):
    date_start_contract = forms.DateField(required=True, widget=forms.DateInput(format=('%d-%m-%Y'),
                                                                                attrs={
                                                                                    'class': 'datepicker form-control',
                                                                                    'placeholder': 'Select a date',
                                                                                    'type': 'date'}),
                                          )
    date_end_contract = forms.DateField(required=False, widget=forms.DateInput(format=('%d-%m-%Y'),
                                                                               attrs={
                                                                                   'class': 'datepicker form-control',
                                                                                   'placeholder': 'Select a date',
                                                                                   'type': 'date'}),
                                        )
    type_housing = forms.ChoiceField(required=True, choices=type_housing_choices, widget=forms.Select(attrs={
        'class': 'form-control',
        'placeholder': _('Entry his type house')
    }))
    comment_access = forms.CharField(required=False, max_length=256, widget=forms.Textarea(attrs={
        'class': 'form-control',
        'placeholder': _('Entry commentary')
    }))
    payment_method = forms.ChoiceField(required=True, choices=payment_method_choices, widget=forms.Select(attrs={
        'class': 'form-select ',
        'placeholder': _('Select his payment method')
    }))

    class Meta:
        model = ContractDelivery
        fields = ["date_start_contract", "date_end_contract", "type_housing", "comment_access", "payment_method",
                  ]


class ContractUpdateForm(forms.ModelForm):
    date_start_contract = forms.DateField(required=False, widget=forms.DateInput(format=('%Y-%m-%d'),
                                                                                 attrs={
                                                                                     'class': 'datepicker form-control',
                                                                                     'placeholder': 'Select a date',
                                                                                     'type': 'date'}),
                                          )
    date_end_contract = forms.DateField(required=False, widget=forms.DateInput(format=('%Y-%m-%d'),
                                                                               attrs={
                                                                                   'class': 'datepicker form-control',
                                                                                   'placeholder': 'Select a date',
                                                                                   'type': 'date'}),
                                        )
    type_housing = forms.ChoiceField(required=False, choices=type_housing_choices, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': _('Entry his type house')
    }))
    comment_access = forms.CharField(required=False, max_length=256, widget=forms.Textarea(attrs={
        'class': 'form-control',
        'placeholder': _('Entry commentary')
    }))
    payment_method = forms.ChoiceField(required=False, choices=payment_method_choices, widget=forms.Select(attrs={
        'class': 'form-select ',
        'placeholder': _('Select his payment method')
    }))

    class Meta:
        model = ContractDelivery
        fields = ["date_start_contract", "date_end_contract", "type_housing", "comment_access", "payment_method", ]


class MealsNumberForm(forms.ModelForm):
    meal_monday = forms.IntegerField(initial=0, required=False, widget=forms.NumberInput(attrs={
        'class': 'form-control',
    }))
    meal_tuesday = forms.IntegerField(initial=0, required=False, widget=forms.NumberInput(attrs={
        'class': 'form-control',
    }))
    meal_wednesday = forms.IntegerField(initial=0, required=False, widget=forms.NumberInput(attrs={
        'class': 'form-control',
    }))
    meal_thursday = forms.IntegerField(initial=0, required=False, widget=forms.NumberInput(attrs={
        'class': 'form-control',
    }))
    meal_friday = forms.IntegerField(initial=0, required=False, widget=forms.NumberInput(attrs={
        'class': 'form-control',
    }))
    meal_saturday = forms.IntegerField(initial=0, required=False, widget=forms.NumberInput(attrs={
        'class': 'form-control',
    }))
    meal_sunday = forms.IntegerField(initial=0, required=False, widget=forms.NumberInput(attrs={
        'class': 'form-control',
    }))

    class Meta:
        model = MealsNumber
        fields = '__all__'
        exclude = ['week_of_contract']

    def __init__(self, *args, **kwargs):
        super(MealsNumberForm, self).__init__(*args, **kwargs)
        d = DeliveryDay.objects.first()
        if not d.monday:
            self.fields['meal_monday'].widget = forms.HiddenInput()
        if not d.tuesday:
            self.fields['meal_tuesday'].widget = forms.HiddenInput()
        if not d.wednesday:
            self.fields['meal_wednesday'].widget = forms.HiddenInput()
        if not d.thursday:
            self.fields['meal_thursday'].widget = forms.HiddenInput()
        if not d.friday:
            self.fields['meal_friday'].widget = forms.HiddenInput()
        if not d.saturday:
            self.fields['meal_saturday'].widget = forms.HiddenInput()
        if not d.sunday:
            self.fields['meal_sunday'].widget = forms.HiddenInput()


class WeekOfContractUpdateForm(forms.ModelForm):
    class Meta:
        model = WeekOfContract
        fields = '__all__'
        exclude = ['contract_delivery']


class WeekOfContractForm(forms.Form):
    day_possibility = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check d-flex flex-row  justify-content-evenly'}))

    def __init__(self):
        super().__init__()
        d = DeliveryDay.objects.first()
        self.fields['day_possibility'].choices = d.get_day_valid_choices()


class CancelDeliveryForm(forms.ModelForm):
    date_cancel = forms.DateField(required=True, widget=forms.DateInput(format=('%d-%m-%Y'),
                                                                        attrs={'class': 'datepicker form-control',
                                                                               'placeholder': 'Select a date',
                                                                               'type': 'date'}),
                                  )
    commentary_cancel = forms.CharField(required=False, widget=forms.Textarea(attrs={
        'class': 'form-control',
        'placeholder': _('Entry commentary')
    }))

    class Meta:
        model = CancelDelivery
        fields = ["date_cancel", "commentary_cancel"]
