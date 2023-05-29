from math import floor

from django import template
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Avg

from app11_quality.models_qualite import Critere, Elementsevaluation, Thematique

register = template.Library()

EVAL_FACES = {1: settings.STATIC_URL + 'app4_ehpad_base/img/visage_rouge.svg',
              2: settings.STATIC_URL + 'app4_ehpad_base/img/visage_orange.svg',
              3: settings.STATIC_URL + 'app4_ehpad_base/img/visage_vert_clair.svg',
              4: settings.STATIC_URL + 'app4_ehpad_base/img/visage_vert_fonce.svg',
              5: 'optimized'}


@register.filter
def global_criterion(crit_id):
    try:
        crit = Critere.objects.get(id=crit_id)
        elem = Elementsevaluation.objects.filter(critere=crit)
        if elem.count() > elem.filter(evaluation__gt=0).count():
            return None
        avg = floor(elem.aggregate(Avg('evaluation'))['evaluation__avg'])
    except (ObjectDoesNotExist, TypeError):
        return None
    return EVAL_FACES[avg]


def percentage(part, whole):
    result = 100 * float(part)/float(whole)
    return f'{floor(result):.0f}%'


@register.filter
def completion_rate(them_id, chap_id):
    try:
        them = Thematique.objects.get(id=them_id)
        elem = Elementsevaluation.objects.filter(critere__thematique=them, critere__chapitre=chap_id)
        if not elem.exists():
            return ''
        else:
            return percentage(elem.filter(evaluation__gt=0).count(), elem.count())
    except ObjectDoesNotExist:
        return ''
