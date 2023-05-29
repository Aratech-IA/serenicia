from genericpath import exists
from django.shortcuts import render, redirect
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, FileResponse

from app4_ehpad_base.models import date_payroll, ProfileSerenicia
from app11_quality.models import Protocol_list
from app11_quality.models_qualite import Critere, ChampApplicationPublic, References, Elementsevaluation, Response
from .form import FilterSelector, FormResponse
from .pdf_report import build_criteria_assessment_pdf
from .excel_report import build_criteria_assessment_xls


def index_fiche_critere(request):
    try:
        request.session.pop('resident_id')
    except KeyError:
        pass
    # Gestion du form tri
    context = {}
    form = None
    if request.method == 'POST':
        formexigence = FilterSelector(request.POST)
        if formexigence.is_valid():
            form = formexigence.cleaned_data
    else:
        formexigence = FilterSelector()
    context['critere'] = formexigence

    # Recupération de tous les critères
    all_criteres = Critere.objects.all()

    # Filres pour recherche
    if form:
        if form.get('exigence'):
            all_criteres = all_criteres.filter(exigence=form.get('exigence'))
        if form.get('essms') != 'essms':
            all_criteres = all_criteres.filter(essms__in=[form.get('essms'), 'essms'])
        if form.get('structure') != 'structures':
            all_criteres = all_criteres.filter(structure__in=[form.get('structure'), 'structures'])
        if form.get('public'):
            all_criteres = all_criteres.filter(public=form.get('public'))
        if form.get('manager') == 'personals':
            all_criteres = all_criteres.filter(manager=request.user.profileserenicia)
        if form.get('evaluation'):
            all_criteres = all_criteres.filter(elementsevaluation__evaluation__in=form.get('evaluation')).distinct('id')
        elif form.get('manager') == 'all':
            all_criteres = all_criteres

    # Récupération des autres champs
    result = []
    for critere in all_criteres.distinct('chapitre'):
        tmp_data = {'chapitre': critere.chapitre, 'thematiques': []}
        for crit in all_criteres.filter(chapitre=critere.chapitre).distinct('thematique'):
            tmp_them = {'thematique': crit.thematique, 'objectifs': []}
            for cr in all_criteres.filter(chapitre=crit.chapitre, thematique=crit.thematique).distinct('objectif'):
                tmp_them['objectifs'].append({'objectif': cr.objectif,
                                              'criteres': all_criteres.filter(chapitre=cr.chapitre,
                                                                              thematique=cr.thematique,
                                                                              objectif=cr.objectif)})
            tmp_data['thematiques'].append(tmp_them)
        result.append(tmp_data)

    context['manuel'] = result

    return render(request, 'app11_quality/index-fiche-critere.html', context)


def fiche_critere(request, manual_id):
    try:
        # Récupération des infos utiles
        manual_page = Critere.objects.get(id=manual_id)

        # Récupération des valeurs public
        valeurpublic = []
        for public in manual_page.public.all():
            for publique in ChampApplicationPublic.PUBLIC_CHOICES:
                if publique[0] == public.public:
                    valeurpublic.append(publique[1])

        # Affichage de la valeur au lieu de la clé
        valeurexigence = None
        valeuressms = None
        valeurstructure = None
        for exigence in Critere.EXIGENCE_CHOICES:
            if exigence[0] == manual_page.exigence:
                valeurexigence = exigence[1]
        for essms in Critere.ESSMS_CHOICES:
            if essms[0] == manual_page.essms:
                valeuressms = essms[1]
        for structure in Critere.STRUCTURE_CHOICES:
            if structure[0] == manual_page.structure:
                valeurstructure = structure[1]
        valeur = {'valeurexigence': valeurexigence, 'valeuressms': valeuressms, 'valeurstructure': valeurstructure,
                  'valeurpublic': valeurpublic}

    except ObjectDoesNotExist:
        return redirect('app11_quality index-fiche-critere')

    context = {}
    formresponse = None
    if request.POST:
        if request.POST.get('eval'):
            Elementsevaluation.objects.filter(id=request.POST.get('eval-id')).update(evaluation=request.POST.get('eval'))
        else:
            formresponse = FormResponse(request.POST)
            if formresponse.is_valid():
                if request.POST.get('modif_rep'):
                    Response.objects.filter(id=request.POST.get('modif_rep')).update(text=request.POST.get('text'))
                else :
                    response = formresponse.save(commit=False)
                    response.critere = manual_page
                    response.created_by = request.user.profileserenicia
                    response.save()
            elif request.POST.get('modif_rep'):
                modif_rep = Response.objects.get(id=request.POST.get('modif_rep'))
                context['modif_rep'] = modif_rep.id
                formresponse = FormResponse(instance=modif_rep)
            elif request.POST.get('add_response'):
                context['add_response'] = True
                formresponse = FormResponse()
    else:
        formresponse = FormResponse()


    # Récupération des éléments d'évaluation
    all_elements = Elementsevaluation.objects.filter(critere=manual_page)
    element = {}
    valeurchoice = None
    for elem in all_elements:
        for choice in Elementsevaluation.ELEMENT_CHOICES:
            if choice[0] == elem.element:
                valeurchoice = choice[1]
        if not element.get(valeurchoice):
            element[valeurchoice] = [{'text': elem.detail, 'eval': elem.evaluation, 'id': elem.id}]
        else:
            element[valeurchoice].append({'text': elem.detail, 'eval': elem.evaluation, 'id': elem.id})

    # Récupération des références
    all_references = References.objects.filter(critere=manual_page)
    reference = {}
    valeurchoix = None
    for ref in all_references:
        for choix in References.REFERENCE_CHOICES:
            if choix[0] == ref.reference:
                valeurchoix = choix[1]
        if not reference.get(valeurchoix):
            reference[valeurchoix] = [{'detail': ref.detail, 'url': ref.reference_url}]
        else:
            reference[valeurchoix].append({'detail': ref.detail, 'url': ref.reference_url})

    # Récupération des réponses
    responses = Response.objects.filter(critere=manual_page).order_by('-date')
    criterion_id = manual_id

    # Suppression d'une réponse
    if request.method == 'POST':
        if request.POST.get('delete'):
            selected_response = Response.objects.get(id=request.POST.get('delete'))
            selected_response.delete()

    context.update({'manual_page': manual_page, 'valeur': valeur, 'element': element, 'reference': reference,
                   'form': formresponse, 'responses': responses, 'criterion_id': criterion_id})
    return render(request, 'app11_quality/fiche-critere.html', context)


def dlProtocol(request, protocol_id):
    protocol = Protocol_list.objects.get(id=protocol_id)
    return HttpResponse(protocol.file, content_type='application/pdf')


def download_pdf(request):
    file = build_criteria_assessment_pdf(request.user)
    if not file:
        return redirect('app11_quality index-fiche-critere')
    return FileResponse(file['data'], as_attachment=True, filename=file['name'])


def download_xls(request):
    file = build_criteria_assessment_xls(request.user)
    if not file:
        return redirect('app11_quality index-fiche-critere')
    return FileResponse(file['data'], as_attachment=True, filename=file['name'])


def select_manager(request, crit_id):
    if request.POST.get('profileserenicia'):
        Critere.objects.filter(id=crit_id).update(manager=ProfileSerenicia.objects.get(id=request.POST.get('profileserenicia')))
        return redirect('app11_quality fiche-critere', manual_id=crit_id)
    pjs = ProfileSerenicia.objects.filter(user__groups__permissions__codename='view_quality',
                                          user__is_active=True, user__profile__advanced_user=False).distinct('id')
    return render(request, 'app11_quality/select_manager.html', {'pjs': pjs})
