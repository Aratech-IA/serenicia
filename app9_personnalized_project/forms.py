from django import forms
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q

from django.utils.translation import gettext_lazy as _

from app4_ehpad_base.models import ProfileSerenicia
from app9_personnalized_project.models import Notation, Comment, StoryLife, Relation, Person


class NotationForm(forms.ModelForm):
    class Meta:
        model = Notation
        fields = '__all__'

    def save(self, answer=None, commit=True):
        try:
            notation = answer.get(question=self.cleaned_data['question'], chapter=self.cleaned_data['chapter'])
            notation.notation = self.cleaned_data['notation']
            notation.save()
            answer.update()
        except ObjectDoesNotExist:
            notation = super().save(self)
            answer.add(notation)
        return answer


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = '__all__'


class StoryLifeForm(forms.ModelForm):
    text = forms.CharField(widget=forms.Textarea(attrs={'rows': '10', 'cols': '0', 'class': 'w-100', 'readonly': True}),
                           required=False)
    cannot_answer = forms.BooleanField(widget=forms.CheckboxInput(attrs={'onchange': 'this.form.submit()'}),
                                       required=False)

    def save(self, **kwargs):
        result = StoryLife.objects.get_or_create(resident=kwargs['resident'], title=kwargs['title'])[0]
        result.text = self.cleaned_data['text']
        if self.cleaned_data['text']:
            result.cannot_answer = False
        else:
            result.cannot_answer = self.cleaned_data['cannot_answer']
        result.save()

    class Meta:
        model = StoryLife
        fields = ['text', 'cannot_answer']


class AddingPerson(forms.ModelForm):
    photo = forms.ImageField(widget=forms.FileInput(attrs={'class': 'd-none', 'id': 'person_photo'}), required=False,
                             label=_('Photo'))
    birth = forms.DateField(widget=forms.DateInput(attrs={'onfocus': 'this.type="date"', 'onblur': 'this.type="text"',
                                                          'class': 'text-center date-field',
                                                          'placeholder': 'DD/MM/YYYY'}),
                            label=_('Birth date'), required=False)
    death = forms.DateField(widget=forms.DateInput(attrs={'onfocus': 'this.type="date"', 'onblur': 'this.type="text"',
                                                          'class': 'text-center date-field',
                                                          'placeholder': 'DD/MM/YYYY'}),
                            label=_('Date of death'), required=False)
    comment = forms.CharField(widget=forms.Textarea(attrs={'rows': '10', 'cols': '0', 'class': 'w-100'}),
                              required=False, label=_('Comment'))

    class Meta:
        model = Person
        fields = '__all__'
        exclude = ['family', 'level_y', 'level_x']


class AddingEntente(forms.ModelForm):
    def save(self, commit=False, **kwargs):
        initial_person = kwargs.pop('from_person')
        relation = super(AddingEntente, self).save(commit=commit)
        relation.from_person = initial_person
        relation.other = True
        if not relation.to_person.level_y:
            relation.to_person.level_y = relation.from_person.level_y
            relation.to_person.level_x = Person.objects.filter(family=initial_person.family, level_y=initial_person.level_y).count() + 1
            relation.to_person.save()
        relation.save()
        return relation

    def __init__(self, *args, **kwargs):
        from_person = kwargs.pop('person')
        super().__init__(*args, **kwargs)
        self.fields['to_person'].queryset = Person.objects.filter(family=from_person.family).exclude(id=from_person.id)

    class Meta:
        model = Relation
        fields = '__all__'
        exclude = ['type', 'from_person']


class AddingRelation(forms.ModelForm):
    def save(self, commit=False, **kwargs):
        initial_person = kwargs.pop('from_person')
        relation = super(AddingRelation, self).save(commit=commit)
        relation.from_person = initial_person
        if relation.type == 'child':
            from_person = relation.to_person
            relation.to_person = initial_person
            relation.from_person = from_person
            relation.type = 'parent'
            relation.from_person.level_y = initial_person.level_y - 1
            relation.from_person.level_x = initial_person.level_x
            relation.from_person.save()
        else:
            if relation.type == 'parent':
                relation.to_person.level_y = initial_person.level_y + 1
                level_x = initial_person.level_x
            else:
                relation.to_person.level_y = initial_person.level_y
                relation_count = Relation.objects.filter((Q(from_person=initial_person) | Q(to_person=initial_person))).exclude(type='parent').count()
                if relation_count % 2:
                    level_x = initial_person.level_x + 1
                else:
                    level_x = initial_person.level_x - 1
            relation.to_person.level_x = level_x
            relation.to_person.save()
        relation.save()
        return relation

    def __init__(self, *args, **kwargs):
        from_person = kwargs.pop('person')
        super().__init__(*args, **kwargs)
        self.fields['to_person'].queryset = Person.objects.filter(family=from_person.family).exclude(id=from_person.id)

    class Meta:
        model = Relation
        fields = '__all__'
        exclude = ['other', 'from_person', 'quality']


class ModifyRelation(forms.ModelForm):
    class Meta:
        model = Relation
        fields = ['quality']
        labels = {'quality': _('Entente')}
