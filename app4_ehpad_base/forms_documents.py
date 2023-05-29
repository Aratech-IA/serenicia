from django import forms
from django.forms import ModelForm

from .models import Card, KitInventory, User, Diet, Profile

# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------


class UploadCard(ModelForm):
    class Meta:
        model = Card
        fields = ['type_card', 'upload_card']
        upload_card = forms.FileField(
            widget=forms.ClearableFileInput(attrs={'multiple': False})
        )


class KitInventoryForm(ModelForm):
    class Meta:
        model = KitInventory
        fields = '__all__'
        exclude = ['user_resident', 'nurses', 'creation_date']


class ResidentForm(ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name']


class ProfileResidentForm(ModelForm):
    class Meta:
        model = Profile
        fields = ['photo', 'civility']


class DietForm(ModelForm):
    class Meta:
        model = Diet
        fields = '__all__'
        exclude = ['user_resident']
