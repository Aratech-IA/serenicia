from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseRedirect, FileResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from app4_ehpad_base.models import ProfileSerenicia
from app8_survey.forms import NotationForm, CommentForm
from app8_survey.models import Survey, SurveyResponse, Question, Comment
from app8_survey.report_factory import build_report


@login_required
@permission_required('app0_access.view_monavis')
def index(request):
    try:
        request.session.pop('resident_id')
    except KeyError:
        pass
    if request.method == 'POST':
        return redirect('survey answering', survey_id=request.POST.get('survey'))
    if request.user.has_perm('app0_access.view_family'):
        target = ['family']
    else:
        target = ['employees', 'referents']
    if Survey.objects.filter(is_active=True, target__in=target).count() < 1:
        msg = str(_("No survey available"))
        return HttpResponseRedirect('/error/' + msg)
    context = {'listsurvey': [{'survey': survey,
                               'answer': SurveyResponse.objects.filter(survey=survey,
                                                                       interviewee=ProfileSerenicia.objects.get(
                                                                           user=request.user)).first()}
                              for survey in Survey.objects.filter(is_active=True, target__in=target)]}
    return render(request, 'app8_survey/index.html', context)


@login_required
@permission_required('app0_access.view_monavis')
def survey_answering(request, survey_id):
    context = {}
    try:
        survey = Survey.objects.get(id=survey_id)
    except ObjectDoesNotExist:
        msg = str(_("No survey available"))
        return HttpResponseRedirect('/error/' + msg)
    surveyresponse, is_created = SurveyResponse.objects.get_or_create(survey=survey,
                                                                      interviewee=ProfileSerenicia.objects.get(
                                                                          user=request.user))
    answer = surveyresponse.notation
    if request.method == 'POST':
        chapter = None
        if request.POST.get('comment'):
            chapter = request.POST.get('chapter')
            comment_form = CommentForm({'text': request.POST.get('comment'), 'chapter': chapter,
                                        'surveyresponse': surveyresponse})
            if comment_form.is_valid():
                comment_form.save()
            elif not comment_form.validate_unique():
                Comment.objects.filter(chapter=chapter,
                                       surveyresponse=surveyresponse).update(text=request.POST.get('comment'))
        elif request.POST.get('choice'):
            chapter = (request.POST.get('choice').split('.'))[0]
            choices = {'chapter': chapter,
                       'question': (request.POST.get('choice').split('.'))[1],
                       'notation': (request.POST.get('choice').split('.'))[2]}
            form = NotationForm(choices)

            if form.is_valid():
                answer = form.save(answer)
                surveyresponse.last_update = timezone.localtime()
                if (surveyresponse.notation.count() == Question.objects.filter(
                        chapter__survey=survey).count()) and not surveyresponse.filling_date:
                    surveyresponse.filling_date = timezone.localtime().date()
                surveyresponse.save()
        context['last_chapter'] = chapter
    if surveyresponse.filling_date:
        context['readonly'] = True
    else:
        context['readonly'] = False
    context['answer'] = [f'{notation.chapter.id}.{notation.question.id}.{notation.notation.id}' for notation in
                         answer.all()]
    context['comment'] = [{'text': com.text, 'chapter': com.chapter.id} for com in
                          Comment.objects.filter(surveyresponse=surveyresponse)]
    context['survey'] = survey
    context['date'] = {'filled': surveyresponse.filling_date, 'update': surveyresponse.last_update}
    return render(request, 'app8_survey/survey.html', context)


@login_required
@permission_required('app0_access.view_monavis')
def satisfaction_survey_resident(request):
    context = {}
    # get or create survey for the resident, prefetch the ManyToMany fields to prevent other request on the db
    survey = Survey.objects.prefetch_related('chapters', 'chapters__questions',
                                             'chapters__questions__notation_choices'). \
        filter(type='satisfaction', target='resident').last()
    if not survey:
        msg = str(_("No survey available"))
        return HttpResponseRedirect('/error/' + msg)
    surveyresponse, is_created = SurveyResponse.objects.prefetch_related('notation'). \
        get_or_create(survey=survey, interviewee=ProfileSerenicia.objects.get(user__id=request.session['resident_id']))
    answer = surveyresponse.notation
    if request.method == 'POST':
        chapter = None
        if request.POST.get('comment'):
            chapter = request.POST.get('chapter')
            comment_form = CommentForm({'text': request.POST.get('comment'), 'chapter': chapter,
                                        'surveyresponse': surveyresponse})
            if comment_form.is_valid():
                comment_form.save()
            elif not comment_form.validate_unique():
                Comment.objects.filter(chapter=chapter,
                                       surveyresponse=surveyresponse).update(text=request.POST.get('comment'))
        elif request.POST.get('choice'):
            chapter = (request.POST.get('choice').split('.'))[0]
            choices = {'chapter': chapter,
                       'question': (request.POST.get('choice').split('.'))[1],
                       'notation': (request.POST.get('choice').split('.'))[2]}
            form = NotationForm(choices)

            if form.is_valid():
                answer = form.save(answer)
                surveyresponse.last_update = timezone.localtime()
                if (surveyresponse.notation.count() == Question.objects.filter(
                        chapter__survey=survey).count()) and not surveyresponse.filling_date:
                    surveyresponse.filling_date = timezone.localtime().date()
                surveyresponse.save()
        context['last_chapter'] = chapter
    if request.user.has_perm('app0_access.view_family') or surveyresponse.filling_date:
        context['readonly'] = True
    else:
        context['readonly'] = False
    context['answer'] = [f'{notation.chapter.id}.{notation.question.id}.{notation.notation.id}' for notation in
                         answer.all()]
    context['comment'] = [{'text': com.text, 'chapter': com.chapter.id} for com in
                          Comment.objects.filter(surveyresponse=surveyresponse)]
    context['survey'] = survey
    context['date'] = {'filled': surveyresponse.filling_date, 'update': surveyresponse.last_update}
    return render(request, 'app8_survey/survey.html', context)


@login_required
@permission_required(('app0_access.view_monavis', 'app8_survey.view_survey'))
def dashboard(request):
    try:
        request.session.pop('resident_id')
    except KeyError:
        pass
    list_survey = Survey.objects.order_by('year', 'title')
    context = {'active': list_survey.filter(is_active=True), 'inactive': list_survey.filter(is_active=False)}
    return render(request, 'app8_survey/dashboard.html', context)


@login_required
@permission_required(('app0_access.view_monavis', 'app8_survey.view_survey'))
def details(request, survey_id):
    try:
        survey = Survey.objects.get(id=survey_id)
    except ObjectDoesNotExist:
        return redirect('app8_survey dashboard')
    return render(request, 'app8_survey/details.html',
                  {'survey': survey,
                   'answers_count': SurveyResponse.objects.filter(survey=survey, filling_date__isnull=False).count()})


def download_report(request, survey_id):
    try:
        survey = Survey.objects.get(id=survey_id)
        if not SurveyResponse.objects.filter(survey=survey, filling_date__isnull=False).exists():
            raise ObjectDoesNotExist
    except ObjectDoesNotExist:
        return redirect(request.META.get('HTTP_REFERER'))
    result = build_report(survey)
    return FileResponse(result['file'], as_attachment=True, filename=result['name'])
