from django import forms

from app12_delivery.models import DeliveryDay


class DeliveryDayForm(forms.ModelForm):
    class Meta:
        model = DeliveryDay
        fields = '__all__'
