from io import BytesIO

from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image

from app11_quality.models_qualite import Critere, ChampApplicationPublic, Elementsevaluation, Response

styles = getSampleStyleSheet()
spacer = Spacer(0, 3 * mm)


def get_trad_from_choices(value, choices):
    for choice in choices:
        if choice[0] == value:
            return choice[1]
    return ''


def build_assessment_items(items):
    eval_faces = {1: settings.STATIC_ROOT + '/app4_ehpad_base/img/visage_rouge_132x132.png',
                  2: settings.STATIC_ROOT + '/app4_ehpad_base/img/visage_orange_132x132.png',
                  3: settings.STATIC_ROOT + '/app4_ehpad_base/img/visage_orange_132x132.png',
                  4: settings.STATIC_ROOT + '/app4_ehpad_base/img/visage_vert_fonce_132x132.png',
                  5: settings.STATIC_ROOT + '/app4_ehpad_base/img/etoile.png'}
    result = []
    for title in Elementsevaluation.ELEMENT_CHOICES:
        if items.filter(element=title[0]).exists():
            result.append(Paragraph(get_trad_from_choices(title[0], Elementsevaluation.ELEMENT_CHOICES), styles['h4']))
            for item in items.filter(element=title[0]):
                detail = Paragraph(f' • {item.detail}', styles['Normal'])
                image = Image(eval_faces[item.evaluation], 10 * mm, 10 * mm,
                              hAlign='LEFT')
                result.extend([detail, image, spacer])
    return result


def build_comments(items, criterion):
    result = [Paragraph(_('Responses'), styles['Title']), criterion]
    for response in items.filter(protocols__isnull=True):
        date = Paragraph(f' • {response.date.strftime("%d")} {_(response.date.strftime("%B"))} {response.date.strftime("%Y")}',
                         styles['Normal'])
        text = Paragraph(response.text, styles['Normal'])
        result.extend([date, text, spacer])
    result.append(Paragraph(_('Annexes'), styles['h3']))
    for annexe in items.filter(protocols__isnull=False):
        for protocol in annexe.protocols.all():
            result.append(Paragraph(f' • {protocol.name}', styles['Normal']))
    return result


def build_ordered_criterion(crit, date_value):
    extract_style = styles['Italic']
    extract_style.alignment = 2
    extract_trad = _("Extract the")
    extract = Paragraph(f'{extract_trad} : {date_value.strftime("%d")} {_(date_value.strftime("%B"))} {date_value.strftime("%Y")}', extract_style)
    thematic = Paragraph(f'{_("Thematic")} {crit.thematique.title}', styles['h2'])
    goal = Paragraph(f'{_("GOAL")} {crit.chapitre.number}.{crit.objectif.number} - {crit.objectif.title}', styles['h2'])
    criterion = Paragraph(
        f'{_("CRITERION")} {crit.chapitre.number}.{crit.objectif.number}.{crit.number} - {crit.title}', styles['h2'])
    requirement = Paragraph(
        f'{_("Requirement level")} : {get_trad_from_choices(crit.exigence, Critere.EXIGENCE_CHOICES)}',
        styles['Normal'])
    scope_str = f'{_("Scope")} : {get_trad_from_choices(crit.essms, Critere.ESSMS_CHOICES)} - {get_trad_from_choices(crit.structure, Critere.STRUCTURE_CHOICES)} - '
    last_loop = crit.public.count() - 1
    for index, value in enumerate(crit.public.all()):
        scope_str += get_trad_from_choices(value.public, ChampApplicationPublic.PUBLIC_CHOICES)
        if index < last_loop:
            scope_str += ' / '
    scope = Paragraph(scope_str, styles['Normal'])
    items_title = Paragraph(_("Assessment items"), styles['Title'])
    ordered_criterion = [extract, thematic, goal, criterion, spacer, requirement, spacer, scope, spacer, items_title]
    ordered_criterion.extend(build_assessment_items(Elementsevaluation.objects.filter(critere=crit, evaluation__gt=0)))
    ordered_criterion.extend(build_comments(Response.objects.filter(critere=crit).order_by('-date'), criterion))
    return ordered_criterion


def build_criteria_assessment_pdf(user):
    criteria = Critere.objects.filter(elementsevaluation__evaluation__gt=0).distinct('id')
    today = timezone.now()
    title_str = _('Criteria assessment') + ' ' + _(today.strftime("%B")) + ' ' + today.strftime("%Y")
    # buffered document
    pdf_buffer = BytesIO()
    report = SimpleDocTemplate(pdf_buffer, title=title_str, author=user.get_full_name())
    document = []
    for crit in criteria:
        document.extend(build_ordered_criterion(crit, today))
        document.append(PageBreak())
    report.build(document)
    pdf_buffer.seek(0)  # save buffer
    return {'data': pdf_buffer, 'name': title_str.replace(' ', '_').lower() + '.pdf'}
