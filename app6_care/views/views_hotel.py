import datetime
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone

from app1_base.models import User
from app4_ehpad_base.models import MealBooking
from app6_care.models import FreeComment, TaskLevel1
from app6_care.forms.forms_intervention import FreeCommentForm
from app6_care.views.intervention import intervention


def get_guests_details(date):
    listbooking = MealBooking.objects.filter(date=date).distinct('owner')
    return {'guests': listbooking.filter(owner__user__groups__permissions__codename='view_groupreservation',
                                         other_guests__gt=0),
            'families': listbooking.filter(guests__groups__permissions__codename='view_family')}


@login_required
def views_hotel(request):
    context = {}
    if request.POST.get('date_value'):
        date = datetime.datetime.strptime(request.POST.get('date_value'), "%Y-%m-%d")
        ctrl = request.POST.get('date_control')
        if ctrl == 'previous':
            date = date - timedelta(days=1)
        elif ctrl == 'next':
            date = date + timedelta(days=1)
    else:
        date = timezone.now()
        specific_to_a_resident = None
        if request.POST.get('free_comment'):
            return redirect('hotel_free_comment')

        elif request.POST.get('private_intervention'):
            specific_to_a_resident = True

        elif request.POST.get('public_intervention'):
            specific_to_a_resident = False

        elif 'specific_to_a_resident' in request.POST:
            if request.POST.get('specific_to_a_resident') == 'True':
                specific_to_a_resident = True
            elif request.POST.get('specific_to_a_resident') == 'False':
                specific_to_a_resident = False
        context = intervention(request, 'ASH', specific_to_a_resident)
    context['date_value'] = date
    context['bookings'] = get_guests_details(date)
    return render(request, 'app6_care/hotel/hotel.html', context)


@login_required
def views_hotel_free_comment(request):
    if request.method == 'POST':
        patient = User.objects.get(pk=request.session['resident_id']) if request.session['resident_id'] else None
        form = FreeCommentForm(request.POST)
        if form.is_valid():
            FreeComment.objects.create(patient=patient, content=form.cleaned_data['content'], nurse=request.user,
                                       profession='ASH')
            return redirect('hotel')

    else:
        form = FreeCommentForm()
    return render(request, 'app6_care/hotel/free_comment.html', {'form': form})


@login_required
def personal_index(request):
    specific_to_a_resident = True
    request.POST = {'task_level': 1}
    context = intervention(request, 'ASH', specific_to_a_resident)
    return render(request, 'app6_care/hotel/hotel.html', context)
