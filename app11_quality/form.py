from app11_quality.models_qualite import ChampApplicationPublic, Critere, Response, Elementsevaluation
from app4_ehpad_base.models import ProfileSerenicia
from app11_quality.models import Protocol_list
from django import forms
from django.utils.translation import gettext_lazy as _


class FilterSelector(forms.Form):
    exigence = forms.ChoiceField(choices=(('', _('All exigences')),) + Critere.EXIGENCE_CHOICES, required=False,
                                 widget=forms.Select(
                                     attrs={"onchange": 'this.form.submit()', "class": 'btn btn-perso'}))
    essms = forms.ChoiceField(choices=Critere.ESSMS_CHOICES, required=False, widget=forms.Select(
        attrs={"onchange": 'this.form.submit()', "class": 'btn btn-perso'}))
    structure = forms.ChoiceField(choices=Critere.STRUCTURE_CHOICES, required=False, widget=forms.Select(
        attrs={"onchange": 'this.form.submit()', "class": 'btn btn-perso'}))
    public = forms.ModelChoiceField(queryset=ChampApplicationPublic.objects.all(), empty_label=_('All public'),
                                    required=False, widget=forms.Select(
            attrs={"onchange": 'this.form.submit()', "class": 'btn btn-perso'}))
    manager = forms.ChoiceField(choices=Critere.manager_choices, required=False, widget=forms.Select(
        attrs={"onchange": 'this.form.submit()', "class": 'btn btn-perso'}), label=_('Selection'))
    evaluation = forms.MultipleChoiceField(choices= Elementsevaluation.EVALUATION_CHOICES,
                                   required=False, widget=forms.CheckboxSelectMultiple(
        attrs={"onchange": 'this.form.submit()'}))


class FormResponse(forms.ModelForm):
    text = forms.CharField(widget=forms.Textarea(attrs={'rows': '10', 'cols': '0', 'class': 'w-100'}),
                           label=_('Your answer to this criterion'))

    class Meta:
        model = Response
        exclude = ['protocols', 'critere', 'created_by']
