from django import forms
from django.core.exceptions import ObjectDoesNotExist

from app8_survey.models import Notation, Comment


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

