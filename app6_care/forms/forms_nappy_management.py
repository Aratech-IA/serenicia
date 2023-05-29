from django import forms


class OrderForm(forms.Form):
    id = forms.IntegerField(disabled=True, widget=forms.HiddenInput())
    name = forms.CharField(disabled=True)
    total_stock = forms.IntegerField(disabled=True)
    consumption_past_7_days = forms.IntegerField(disabled=True)
    consumption_next_7_days = forms.IntegerField(disabled=True)
    order = forms.IntegerField(min_value=0)

    name.widget.attrs.update({'class': 'app6_care-input app6_care-input-name'})
    total_stock.widget.attrs.update({'class': 'app6_care-input'})
    consumption_past_7_days.widget.attrs.update({'class': 'app6_care-input'})
    consumption_next_7_days.widget.attrs.update({'class': 'app6_care-input'})
    order.widget.attrs.update({'class': 'app6_care-input app6_care-user-input'})


class DeliveryForm(forms.Form):
    id = forms.IntegerField(disabled=True, widget=forms.HiddenInput())
    name = forms.CharField(disabled=True)
    boxes = forms.IntegerField(min_value=0)

    name.widget.attrs.update({'class': 'app6_care-input app6_care-input-name'})
    boxes.widget.attrs.update({'class': 'app6_care-input app6_care-user-input'})


class SectorInventoryForm(forms.Form):
    id = forms.IntegerField(disabled=True, widget=forms.HiddenInput())
    name = forms.CharField(disabled=True)
    stock = forms.IntegerField(disabled=True)
    real_stock = forms.IntegerField()

    name.widget.attrs.update({'class': 'app6_care-input app6_care-input-name'})
    stock.widget.attrs.update({'class': 'app6_care-input'})
    real_stock.widget.attrs.update({'class': 'app6_care-input app6_care-user-input'})


class StorehouseInventoryForm(forms.Form):
    id = forms.IntegerField(disabled=True, widget=forms.HiddenInput())
    name = forms.CharField(disabled=True)
    stock = forms.IntegerField(disabled=True)
    real_stock = forms.IntegerField(min_value=0)

    name.widget.attrs.update({'class': 'app6_care-input app6_care-input-name'})
    stock.widget.attrs.update({'class': 'app6_care-input'})
    real_stock.widget.attrs.update({'class': 'app6_care-input app6_care-user-input'})


class ReStockForm(forms.Form):
    id = forms.IntegerField(disabled=True, widget=forms.HiddenInput())
    name = forms.CharField(disabled=True)
    actual_stock = forms.IntegerField(disabled=True)
    consumption_next_7_days = forms.IntegerField(disabled=True)
    restock = forms.IntegerField(min_value=0)

    name.widget.attrs.update({'class': 'app6_care-input app6_care-input-name'})
    actual_stock.widget.attrs.update({'class': 'app6_care-input'})
    consumption_next_7_days.widget.attrs.update({'class': 'app6_care-input'})
    restock.widget.attrs.update({'class': 'app6_care-input app6_care-user-input'})
