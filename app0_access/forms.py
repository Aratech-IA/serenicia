from django import forms
from django.utils.translation import gettext_lazy as _

from app0_access.models import USER_TYPE


def get_choices():
    user_type = USER_TYPE.copy()
    user_type.pop('view_prospect')
    result = [(k, v) for k, v in user_type.items()]
    result = sorted(result, key=lambda key: key[0])
    result.insert(0, ('', _('Not defined')))
    return result


class UserTypeForm(forms.Form):
    user_type = forms.ChoiceField(choices=get_choices(), label='', required=False)
