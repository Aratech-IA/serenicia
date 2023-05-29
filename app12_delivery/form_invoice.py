from django import forms
from django.forms import modelformset_factory

from app12_delivery.models import InvoiceHomePlus, DesignationInvoice, InfoCustomerInvoice, NumberDesignationPerInvoice
from django.utils.translation import gettext_lazy as _


class InvoiceHomePlusForm(forms.ModelForm):
    number = forms.CharField(label=_('Name Invoice'), disabled=True)
    amount_without_vat = forms.CharField(label=_('Price Invoice'), disabled=True)
    info_client_invoice = forms.ModelChoiceField(queryset=InfoCustomerInvoice.objects.all(),
                                                 label=_('Customer to Invoicing'),
                                                 widget=forms.Select(attrs={
                                                     'class': 'form-control',
                                                     'placeholder': _('Select a customer')
                                                 }))

    class Meta:
        model = InvoiceHomePlus
        fields = '__all__'
        exclude = ("invoice",)


DesignationInvoiceFormset = modelformset_factory(
    NumberDesignationPerInvoice,
    fields=('designation_invoice', 'number_benefit', 'invoice_home_plus'),
    extra=1,
    widgets={'designation_invoice': forms.Select(attrs={
        'class': 'form-control',
        'placeholder': _('Select a provide')
    }),
        'number_benefit': forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': _('Give a quantity')
        }),
        'invoice_home_plus': forms.HiddenInput()
    }
)


class CreateBenefitForm(forms.ModelForm):
    class Meta:
        model = DesignationInvoice
        fields = '__all__'


class FeedInfoUserForm(forms.ModelForm):
    birth_day = forms.DateField(required=True, widget=forms.DateInput(format=('%d-%m-%Y'),
                                                                      attrs={'class': 'datepicker',
                                                                             'placeholder': 'Select a date',
                                                                             'type': 'date'}))
    profile = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = InfoCustomerInvoice
        fields = '__all__'
