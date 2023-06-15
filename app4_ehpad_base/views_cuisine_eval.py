from io import BytesIO

from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

import calendar
from datetime import datetime, timedelta
from math import modf, ceil, floor

from django.contrib.auth.models import User
from django.db.models.functions import Lower
from django.http import HttpResponseRedirect, FileResponse
from django.shortcuts import render, redirect
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, Image, Spacer
from reportlab.lib.units import mm

from app1_base.models import Profile
from app4_ehpad_base.forms import NewMenuForm, NewEntreeForm, NewMainDishForm, NewAccompanimentForm, NewDessertForm, \
    BookingGroupForm, PhotoMealPresentation
from app4_ehpad_base.models import MenuEvaluation, Meal, Entree, MainDish, Accompaniment, Dessert, EvalMenuSetting, MealBooking, \
    PresentationType, MealPresentation
from app15_calendar.models import Event, PlanningEvent, PlanningEventBooking
from projet.settings import settings


def get_profile_pic_url(user):
    try:
        url = user.profile.photo.url
        return url
    except (AttributeError, ValueError):
        return None


def get_rounded_notation(note):
    if note < 1:
        return note
    result = note
    if not note.is_integer():
        frac, whole = modf(note)
        if frac >= 0.5:
            result = ceil(note)
        else:
            result = floor(note)
    return result


def get_evaluation(list_eval):
    notation = {'entry': 0, 'main_dish': 0, 'dessert': 0, 'service': 0}
    voter = {'entry': 0, 'main_dish': 0, 'dessert': 0, 'service': 0}
    if list_eval.count():
        for evaluation in list_eval:
            if evaluation.entry is not None and evaluation.entry > 0:
                notation['entry'] += evaluation.entry
                voter['entry'] += 1
            if evaluation.main_dish is not None and evaluation.main_dish > 0:
                notation['main_dish'] += evaluation.main_dish
                voter['main_dish'] += 1
            if evaluation.dessert is not None and evaluation.dessert > 0:
                notation['dessert'] += evaluation.dessert
                voter['dessert'] += 1
            if evaluation.service is not None and evaluation.service > 0:
                notation['service'] += evaluation.service
                voter['service'] += 1
        if voter['entry'] > 0:
            notation['entry'] = round(notation['entry'] / voter['entry'], 1)
        if voter['main_dish'] > 0:
            notation['main_dish'] = round(notation['main_dish'] / voter['main_dish'], 1)
        if voter['dessert'] > 0:
            notation['dessert'] = round(notation['dessert'] / voter['dessert'], 1)
        if notation['service'] > 0:
            notation['service'] = round(notation['service'] / voter['service'], 1)
    return {'notation': notation, 'voter': voter}


def get_global_notation_all(list_eval):
    evaluation = get_evaluation(list_eval)['notation']
    total = (evaluation['dessert'] + evaluation['main_dish'] + evaluation['dessert']) / 3
    return get_rounded_notation(total)


def get_global_notation_individual(menu, resident):
    try:
        evaluation = MenuEvaluation.objects.get(menu=menu, voter=resident)
    except ObjectDoesNotExist:
        return None
    result = 0
    operand = 0
    note_list = [evaluation.entry, evaluation.main_dish, evaluation.dessert]
    for note in note_list:
        if note:
            result += note
            operand += 1
    if result != 0:
        result = result / operand
        result = get_rounded_notation(result)
    return int(result)


def calculate_price_menu(menu):
    result = 0
    if menu.entree:
        result = menu.entree.price_cents
    if menu.main_dish:
        result += menu.main_dish.price_cents
    if menu.accompaniment:
        result += menu.accompaniment.price_cents
    if menu.dessert:
        result += menu.dessert.price_cents
    return result


def display_meal(resident_id):
    context = {'today': datetime.now().date()}
    meal_list = list(Meal.objects.order_by('-type').distinct('type').filter(date=context['today']))
    [Meal.objects.filter(id=meal.id).update(price_cents_to_date=calculate_price_menu(meal)) for meal in meal_list]
    meal_count = len(meal_list)
    if meal_count < 2:
        yesterday = context['today'] - timedelta(1)
        if meal_count == 1:
            try:
                # TODO prévoir si resident à eu un plat de substitution ou non dans les 2 requêtes ci-dessous
                if meal_list[0].type == 'noon':
                    meal_list.append(Meal.objects.get(type='evening', date=yesterday, substitution=False))
                else:
                    meal_list.insert(0, Meal.objects.get(type='noon', date=yesterday, substitution=False))
            except ObjectDoesNotExist:
                pass
        else:
            meal_list = list(Meal.objects.order_by('-type').distinct('type').filter(date=yesterday))
    notation = {}
    pics = {}
    first_photo = False
    for meal in meal_list:
        if meal.type == 'noon':
            notation['noon'] = get_global_notation_individual(meal, resident_id)
            notation['noon_global'] = get_global_notation_all(MenuEvaluation.objects.filter(menu=meal))
        else:
            notation['evening'] = get_global_notation_individual(meal, resident_id)
            notation['evening_global'] = get_global_notation_all(MenuEvaluation.objects.filter(menu=meal))
        # TODO gérer ici la sélection du type de restauration du résident
        pics[meal] = {mp.item: mp for mp in MealPresentation.objects.filter(meal=meal, presentation__default=True)}
        if not first_photo:
            for key in pics[meal].keys():
                pics[meal]['active'] = pics[meal][key]
                first_photo = True
                break
    context['notation'] = notation
    context['photo_meal'] = pics
    context['meal_list'] = meal_list
    return context


def get_meal_obj_or_none(dict_data):
    try:
        result = Meal.objects.get(date=dict_data.get('date'),
                                  type=dict_data.get('type'),
                                  substitution=dict_data.get('substitution'))
    except ObjectDoesNotExist:
        result = None
    return result


@login_required
@permission_required('app0_access.view_cuisine')
def new_menu(request):
    len_history = 20
    now = datetime.now()
    daytime_choices = {'AM': 'noon', 'PM': 'evening'}
    daytime = daytime_choices[now.strftime('%p')]
    context = {'menu_history': list(Meal.objects.order_by('-date', 'type', 'substitution')[:len_history])}
    menu_form, displayed = None, None
    if request.method == 'POST':
        if request.POST.get('history'):
            menu_form = NewMenuForm(instance=Meal.objects.get(id=request.POST.get('history')))
            displayed = request.POST.get('history')
        elif request.POST.get('save'):
            menu_form = NewMenuForm(request.POST)
            menu_form.is_valid()
            existing_menu = get_meal_obj_or_none(menu_form.cleaned_data)
            if existing_menu:
                menu_form = NewMenuForm(request.POST, instance=existing_menu)
            menu = menu_form.save()
            if menu:
                displayed = menu.id
                context['menu_history'] = Meal.objects.order_by('-date', 'type', 'substitution')[:len_history]
        else:
            menu_id = request.POST.get('displayed')
            if menu_id == 'None':
                menu_index = 0
            else:
                menu_index = context.get('menu_history').index(Meal.objects.get(id=menu_id))
                if request.POST.get('previous.x'):
                    menu_index += 1
                elif request.POST.get('next.x'):
                    menu_index -= 1
                if menu_index >= len_history:
                    menu_index = len_history - 1
            if menu_index >= 0:
                menu_form = NewMenuForm(instance=context.get('menu_history')[menu_index])
                displayed = context.get('menu_history')[menu_index].id
    if not menu_form:
        menu_form = NewMenuForm(initial={'type': daytime, 'date': now.date().isoformat()})
    context['menu_form'] = menu_form
    context['displayed'] = displayed
    return render(request, 'app4_ehpad_base/cuisine_new_menu.html', context)


def get_form_selected_dish(request, option):
    ret = None
    if option == '1':
        ret = NewEntreeForm(request.POST)
    elif option == '2':
        ret = NewMainDishForm(request.POST)
    elif option == '3':
        ret = NewAccompanimentForm(request.POST)
    elif option == '4':
        ret = NewDessertForm(request.POST)
    return ret


def get_new_form_dish(option, instance=None):
    ret = None
    if option == '1':
        ret = NewEntreeForm(instance=instance)
    elif option == '2':
        ret = NewMainDishForm(instance=instance)
    elif option == '3':
        ret = NewAccompanimentForm(instance=instance)
    elif option == '4':
        ret = NewDessertForm(instance=instance)
    return ret


def get_list_selected_dish(option, sorting):
    query = None
    if option == '1':
        query = Entree.objects.filter(active=True).order_by(Lower('name'))
    elif option == '2':
        query = MainDish.objects.filter(active=True).order_by(Lower('name'))
    elif option == '3':
        query = Accompaniment.objects.filter(active=True).order_by(Lower('name'))
    elif option == '4':
        query = Dessert.objects.filter(active=True).order_by(Lower('name'))
    sort_choices = {'0': query,
                    '1': query.reverse(),
                    '2': query.order_by('-price_cents', Lower('name')),
                    '3': query.order_by('price_cents', Lower('name'))}
    return sort_choices[sorting]


def get_selected_dish(option, dishid):
    if option == '1':
        return Entree.objects.get(pk=dishid)
    if option == '2':
        return MainDish.objects.get(pk=dishid)
    if option == '3':
        return Accompaniment.objects.get(pk=dishid)
    if option == '4':
        return Dessert.objects.get(pk=dishid)


def get_or_create_dish(option, name):
    if option == '1':
        return Entree.objects.get_or_create(name=name)
    if option == '2':
        return MainDish.objects.get_or_create(name=name)
    if option == '3':
        return Accompaniment.objects.get_or_create(name=name)
    if option == '4':
        return Dessert.objects.get_or_create(name=name)


@login_required
@permission_required('app0_access.view_cuisine')
def new_dish(request):
    sorting = '0'
    option = '0'
    dish_form = None
    known_dish = None
    msg = None
    if request.method == 'POST':  # filter selected in list
        option = request.POST.get('orderby')  # order by filter
        sorting = request.POST.get('sorting') or '0'
        if 'modify' in request.POST:
            dish_id = request.POST.get('modify')
            selected_dish = get_selected_dish(option, dish_id)
            dish_form = get_new_form_dish(option, selected_dish)
        elif 'delete' in request.POST:
            dish_id = request.POST.get('delete')
            selected_dish = get_selected_dish(option, dish_id)
            selected_dish.active = False
            selected_dish.save()
            removed = _('removed from the list')
            msg = {'message': f'{selected_dish.name} {removed}', 'category': _('Success')}
        elif 'register_data' in request.POST:
            dish_form = get_form_selected_dish(request, option)
            if dish_form.is_valid():
                msg = dish_form.save()
                dish_form = None
    if option != '0':
        known_dish = get_list_selected_dish(option, sorting)
    if not dish_form:
        dish_form = get_new_form_dish(option)
    context = {'option': option, 'dish_form': dish_form, 'known_dish': known_dish, 'sorting': sorting}
    if msg:
        context.update(msg)
    return render(request, 'app4_ehpad_base/cuisine_new_dish.html', context)


def get_evaluation_object(request, evaltype):
    if EvalMenuSetting.objects.exists():
        switch = EvalMenuSetting.objects.get().notation_switch
    else:
        # Default settings on 16pm UTC
        switch = datetime.strptime("16:00", "%H:%M").time()
    if switch > datetime.now().time():
        menutype = "noon"
    else:
        menutype = "evening"
    today_menu = Meal.objects.filter(date=datetime.today().date(), type=menutype)
    if len(today_menu) < 1:
        return None
    else:
        today_menu = today_menu[0]
    if evaltype == 'manual':
        voter = User.objects.get(pk=request.session['resident_id'])
    else:
        voter = User.objects.get(pk=request.session.get('voter'))
    evaluation = MenuEvaluation.objects.get_or_create(menu=today_menu, voter=voter)
    return evaluation[0]


@login_required
@permission_required('app0_access.view_evalmenu')
def evaluate_entree(request, evaltype, template='app4_ehpad_base/eval_entree.html', redir_url='Evaluate main dish', ws_alexa=None):
    evaluation = get_evaluation_object(request, evaltype)
    if evaluation is None:
        msg = str(_('No menu available.'))
        return HttpResponseRedirect('/error/' + msg)
    try:
        # TODO gérer type de restauration du votant ici
        mp = MealPresentation.objects.get(item='entree', meal=evaluation.menu, presentation__default=True)
    except ObjectDoesNotExist:
        mp = None
    if request.method == 'POST':
        evaluation.entry = request.POST.get('notation')
        evaluation.save()
        return redirect(redir_url, evaltype)
    return render(request, template, {'menu': evaluation.menu, 'ws_alexa': ws_alexa, 'mp': mp})


@login_required
@permission_required('app0_access.view_evalmenu')
def evaluate_main_dish(request, evaltype, template='app4_ehpad_base/eval_maindish.html', redir_url='Evaluate dessert',
                       ws_alexa=None):
    evaluation = get_evaluation_object(request, evaltype)
    try:
        # TODO gérer type de restauration du votant ici
        mp = MealPresentation.objects.get(item='main_dish', meal=evaluation.menu, presentation__default=True)
    except ObjectDoesNotExist:
        mp = None
    if request.method == 'POST':
        evaluation.main_dish = request.POST.get('notation')
        evaluation.save()
        return redirect(redir_url, evaltype)
    return render(request, template, {'menu': evaluation.menu, 'ws_alexa': ws_alexa, 'mp': mp})


@login_required
@permission_required('app0_access.view_evalmenu')
def evaluate_dessert(request, evaltype, template='app4_ehpad_base/eval_dessert.html', redir_url='finalize evaluation',
                     ws_alexa=None):
    evaluation = get_evaluation_object(request, evaltype)
    try:
        # TODO gérer type de restauration du votant ici
        mp = MealPresentation.objects.get(item='dessert', meal=evaluation.menu, presentation__default=True)
    except ObjectDoesNotExist:
        mp = None
    if request.method == 'POST':
        evaluation.dessert = request.POST.get('notation')
        evaluation.save()
        return redirect(redir_url, evaltype)
    return render(request, template, {'menu': evaluation.menu, 'ws_alexa': ws_alexa, 'mp': mp})


@login_required
@permission_required('app0_access.view_evalmenu')
def finalize_evaluation(request, evaltype, template='app4_ehpad_base/eval_finalize.html', redir_url='/', ws_alexa=None):
    evaluation = get_evaluation_object(request, evaltype)
    if request.method == 'POST':
        notation = request.POST.get('notation')
        if notation == '0':
            return redirect('Start evaluation', evaltype=evaltype)
        evaluation.service = notation
        evaluation.save()
        return redirect(redir_url)
    return render(request, template, {'menu': evaluation.menu, 'ws_alexa': ws_alexa})


def get_guest_count(date_value):
    result = {'resident': User.objects.filter(profileserenicia__status='home',
                                              groups__permissions__codename='view_residentehpad',
                                              profile__client__isnull=False).count(),
              'employee_noon': 0, 'employee_evening': 0,
              'guest_noon': 0, 'guest_evening': 0,
              'family_noon': 0, 'family_evening': 0,
              'total_noon': 0, 'total_evening': 0,
              'date': date_value}
    listbooking = MealBooking.objects.filter(date=date_value)
    for booking in listbooking:
        if booking.guests.filter(groups__permissions__codename='view_family').exists():
            if booking.dinner:
                result['family_evening'] += len(booking.guests.all()) + booking.other_guests
            if booking.lunch:
                result['family_noon'] += len(booking.guests.all()) + booking.other_guests
        else:
            if booking.dinner:
                result['employee_evening'] += 1
                result['guest_evening'] += booking.other_guests
            if booking.lunch:
                result['employee_noon'] += 1
                result['guest_noon'] += booking.other_guests
    result['total_noon'] = result['resident'] + result['employee_noon'] + result['family_noon'] + result['guest_noon']
    result['total_evening'] = result['resident'] + result['employee_evening'] \
                              + result['family_evening'] + result['guest_evening']
    return result


def get_reservations_now():
    if EvalMenuSetting.objects.exists():
        switch = EvalMenuSetting.objects.get().notation_switch
    else:
        # Default settings on 16pm UTC
        switch = datetime.strptime("16:00", "%H:%M").time()
    if switch > datetime.now().time():
        menutype = 'noon'
        booking_list = MealBooking.objects.order_by('-is_lunch_ready', Lower('owner__user__last_name')).filter(
            date=datetime.now().date(), lunch=True, is_lunch_served=False)
    else:
        menutype = 'evening'
        booking_list = MealBooking.objects.order_by('-is_dinner_ready', Lower('owner__user__last_name')).filter(
            date=datetime.now().date(), dinner=True, is_dinner_served=False)
    booking_list = booking_list.exclude(owner__user__groups__permissions__codename__in=[
        'view_family', 'view_residentrss', 'view_residentehpad'])
    return booking_list, menutype


@login_required
@permission_required('app0_access.view_cuisine')
def cuisine_index(request):
    date_now = timezone.localdate()
    context = {'today': get_guest_count(date_now), 'date_now': date_now}
    if request.method == 'POST':
        start_date = datetime.fromisoformat(request.POST.get('start_date')).date()
        if 'next.x' in request.POST:
            start_date = start_date + timedelta(weeks=1)
        elif 'previous.x' in request.POST:
            start_date = start_date - timedelta(weeks=1)
    else:
        start_date = date_now
    list_date = [start_date + timedelta(days=day) for day in range(0, 7)]
    context['week'] = [get_guest_count(next_date) for next_date in list_date]
    request.session['resident_id'] = None
    if get_reservations_now()[0].count():
        context['reservation'] = True
    return render(request, 'app4_ehpad_base/cuisine_index.html', context)


# def base64_file(data, name=None):
#     _format, _img_str = data.split(';base64,')
#     _name, ext = _format.split('/')
#     if not name:
#         name = _name.split(":")[-1]
#     return ContentFile(base64.b64decode(_img_str), name='{}.{}'.format(name, ext))
#

# def concat_filename(data, filetype):
#     return data.date.strftime("%d") + data.date.strftime("%m") + data.date.strftime("%y") + filetype + "-" + data.type


# def add_watermark(img):
#     photo = Image.open(img)
#     staticurl = settings.STATIC_ROOT + "/app4_ehpad_base/img/logo_eval-menu_80x32.png"
#     watermark = Image.open(staticurl)  # ajouter logo dans static
#     scaling_factor = 5  # 1/5ème da la taille de la photo
#     scaled = (photo.size[0] / scaling_factor) / watermark.size[0]
#     watermark = watermark.resize((int(watermark.size[0] * scaled), int(watermark.size[1] * scaled)), Image.ANTIALIAS)
#     photo.paste(watermark, (photo.size[0] - (watermark.size[0] + 25), photo.size[1] - (watermark.size[1] + 10)),
#                 watermark)
#     buffered = BytesIO()
#     photo.save(buffered, format="JPEG")
#     photobase64 = base64.b64encode(buffered.getvalue())
#     return photobase64


# @login_required
# @permission_required('app0_access.view_cuisine')
# def capture(request, menu_id, mealtype, pic_type):
#     selected_menu = Meal.objects.get(pk=menu_id)
#     if request.method == 'POST':
#         pics = {'normal_pic': {'entree': 'photo_entree',
#                                'maindish': 'photo_main_dish',
#                                'dessert': 'photo_dessert'},
#                 'mixed_pic': {'entree': 'photo_entree_mixed',
#                               'maindish': 'photo_main_dish_mixed',
#                               'dessert': 'photo_dessert_mixed'}}
#         str_img = request.POST.get('image')
#         filename = concat_filename(selected_menu, mealtype)
#         if pics[pic_type][mealtype] == 'photo_entree':
#             selected_menu.photo_entree = base64_file(str_img, filename)
#         elif pics[pic_type][mealtype] == 'photo_main_dish':
#             selected_menu.photo_main_dish = base64_file(str_img, filename)
#         elif pics[pic_type][mealtype] == 'photo_dessert':
#             selected_menu.photo_dessert = base64_file(str_img, filename)
#         elif pics[pic_type][mealtype] == 'photo_entree_mixed':
#             selected_menu.photo_entree_mixed = base64_file(str_img, filename)
#         elif pics[pic_type][mealtype] == 'photo_main_dish_mixed':
#             selected_menu.photo_main_dish_mixed = base64_file(str_img, filename)
#         elif pics[pic_type][mealtype] == 'photo_dessert_mixed':
#             selected_menu.photo_dessert_mixed = base64_file(str_img, filename)
#         selected_menu.save()
#         return redirect('Select menu', menu_id=menu_id, pic_type=pic_type)
#     return render(request, 'app4_ehpad_base/webcam.html', {'menu': selected_menu, 'mealtype': mealtype})


def get_connected_caregiver(date_value):
    return User.objects.filter(last_login__date=date_value,
                               groups__permissions__codename__in=['view_ash', 'view_as']).prefetch_related(
        'profileserenicia').exclude(groups__permissions__codename__in=['view_manager'])


@login_required
@permission_required('app0_access.view_cuisine')
def service_team(request, menu_id):
    # populate dropdown link
    context = {'history': Meal.objects.order_by('-date', 'type')[:20]}
    if menu_id > 0:
        # menu selected
        context['menu'] = Meal.objects.get(pk=menu_id)
        context['list_staff'] = get_connected_caregiver(context['menu'].date)
        if not context['list_staff'].count():
            # no staff logged
            context['info'] = _('No user logged in on this date')
    if request.method == 'POST':
        selected_staff = request.POST.getlist('staff')
        # remove unselected user
        [context['menu'].photo_service.remove(staff)
         for staff in context['menu'].photo_service.all() if staff not in selected_staff]
        # add selected user
        [context['menu'].photo_service.add(User.objects.get(id=staff_id)) for staff_id in selected_staff]
        context.update({'message': _('The service team has been registered'), 'category': _('Update')})
    return render(request, 'app4_ehpad_base/cuisine_service_team.html', context)


def get_form_photo_meal(initial, item):
    form = PhotoMealPresentation(initial=initial, auto_id=f'{item}_%s')
    form.initial.update({'item': item})
    return form


@login_required
@permission_required('app0_access.view_cuisine')
def select_menu(request, menu_id):
    # get the last 20 menu: 10 days 1 lunch + 1 dinner per day
    context = {'history': Meal.objects.order_by('-date', 'type')[:20],
               'list_presentation': PresentationType.objects.order_by(Lower('type'))}
    if request.method == 'POST':
        if request.POST.get('pic_type'):
            context['selected_type'] = PresentationType.objects.get(pk=request.POST.get('pic_type'))
        elif request.FILES.get('photo'):
            form = PhotoMealPresentation(request.POST, request.FILES)
            if not form.is_valid():
                MealPresentation.objects.filter(item=form.cleaned_data.get('item'), meal=form.cleaned_data.get('meal'),
                                                presentation=form.cleaned_data.get('presentation')).delete()
                form = PhotoMealPresentation(request.POST, request.FILES)
            if form.is_valid():
                form.save()
            context['selected_type'] = form.cleaned_data.get('presentation')
    if not context.get('selected_type'):
        try:
            context['selected_type'] = context['list_presentation'].get(default=True)
        except ObjectDoesNotExist:
            context['selected_type'] = context['list_presentation'].first()
    if menu_id > 0:
        context['menu'] = Meal.objects.prefetch_related('photo_service').get(pk=menu_id)
        context['pics'] = {mp.item: mp for mp in MealPresentation.objects.filter(meal=menu_id,
                                                                                 presentation=context['selected_type'])}
    initial = {'meal': menu_id, 'presentation': context['selected_type']}
    context['form_entree'] = get_form_photo_meal(initial, 'entree')
    context['form_main_dish'] = get_form_photo_meal(initial, 'main_dish')
    context['form_dessert'] = get_form_photo_meal(initial, 'dessert')
    return render(request, 'app4_ehpad_base/cuisine_select_menu.html', context)


def get_last_day_of_month(date_value):
    nextmonth = date_value.month + 1
    if nextmonth > 12:
        nextmonth = 1
        year = date_value.year + 1
    else:
        year = date_value.year
    last_date = datetime(year, nextmonth, 1).date() - timedelta(1)
    return last_date.day


def get_average_evaluation(nb_eval, menutype, date_value):
    if date_value.month == datetime.now().month:
        actual_monthrange = datetime.now().day
    else:
        actual_monthrange = calendar.monthrange(date_value.year, date_value.month)[1]
    average = floor(nb_eval / actual_monthrange)
    previous_month = date_value.month - 1
    previous_year = date_value.year
    if previous_month <= 1:
        previous_month = 1
        previous_year = date_value.year - 1
    nb_eval_previous = MenuEvaluation.objects.filter(menu__date__month=previous_month, menu__date__year=previous_year,
                                                     menu__type=menutype).count()
    previous_average = floor(nb_eval_previous / calendar.monthrange(previous_year, previous_month)[1])
    if average > previous_average:
        return 'border-darkblue'
    elif average < previous_average:
        return 'border-danger'
    elif average == previous_average:
        return 'border-warning'


def get_list_by_sort(sortby, date_value, menutype, res_id):
    eval_average = 'border-darkblue'
    date_range = {}
    result = []
    dict_match = {4: 'very_good', 3: 'good', 2: 'bad', 1: 'very_bad'}
    notation = {'very_good': {'entree': [], 'main_dish': [], 'dessert': [], 'service': []},
                'good': {'entree': [], 'main_dish': [], 'dessert': [], 'service': []},
                'bad': {'entree': [], 'main_dish': [], 'dessert': [], 'service': []},
                'very_bad': {'entree': [], 'main_dish': [], 'dessert': [], 'service': []}}
    if sortby == 'day':
        result = MenuEvaluation.objects.select_related('menu', 'voter').filter(menu__date=date_value,
                                                                               menu__type=menutype)
        date_range = None
    elif sortby == 'month':
        result = MenuEvaluation.objects.select_related('menu', 'voter').filter(menu__date__month=date_value.month,
                                                                               menu__date__year=date_value.year,
                                                                               menu__type=menutype)
        date_range['start'] = datetime.strptime('{}/{}/{}'.format('01', date_value.month, date_value.year),
                                                '%d/%m/%Y').date()
        date_range['end'] = datetime.strptime('{}/{}/{}'.format(get_last_day_of_month(date_value), date_value.month,
                                                                date_value.year), '%d/%m/%Y').date()
        eval_average = get_average_evaluation(result.count(), menutype, date_value)
    elif sortby == 'week':
        start = date_value - timedelta(days=date_value.weekday())
        end = start + timedelta(days=6)
        result = MenuEvaluation.objects.select_related('menu', 'voter').filter(menu__date__range=[start, end],
                                                                               menu__type=menutype)
        date_range['start'] = start
        date_range['end'] = end
    if res_id > 0:
        result = result.filter(voter=res_id)
    for evaluation in result:
        if evaluation.entry:
            notation[dict_match[evaluation.entry]]['entree'].append(evaluation)
        if evaluation.main_dish:
            notation[dict_match[evaluation.main_dish]]['main_dish'].append(evaluation)
        if evaluation.dessert:
            notation[dict_match[evaluation.dessert]]['dessert'].append(evaluation)
        if evaluation.service:
            notation[dict_match[evaluation.service]]['service'].append(evaluation)
    return result, notation, date_range, eval_average


def get_change_by_sortby(date_value, sortby, movement):
    if sortby == 'month':
        if movement == 'next':
            if date_value.month == 12:
                date_value = datetime.strptime('01/01/' + str(date_value.year + 1), '%d/%m/%Y').date()
            else:
                new_date = '01/' + str(date_value.month + 1) + "/" + str(date_value.year)
                date_value = datetime.strptime(new_date, '%d/%m/%Y').date()
        elif movement == 'previous':
            if date_value.month == 1:
                date_value = datetime.strptime('01/12/' + str(date_value.year - 1), '%d/%m/%Y').date()
            else:
                new_date = '01/' + str(date_value.month - 1) + "/" + str(date_value.year)
                date_value = datetime.strptime(new_date, '%d/%m/%Y').date()
        return date_value
    if sortby == 'day':
        shift = timedelta(1)
    else:
        shift = timedelta(weeks=1)
    if movement == 'next':
        date_value = date_value + shift
    elif movement == 'previous':
        date_value = date_value - shift
    return date_value


def get_global_notation(list_eval, option):
    if option == 'entry':
        evaluation = get_evaluation(list_eval)
        return get_rounded_notation(evaluation['notation']['entry'])
    elif option == 'main_dish':
        evaluation = get_evaluation(list_eval)
        return get_rounded_notation(evaluation['notation']['main_dish'])
    elif option == 'dessert':
        evaluation = get_evaluation(list_eval)
        return get_rounded_notation(evaluation['notation']['dessert'])


@login_required
@permission_required('app0_access.view_cuisine')
def dashboard_eval(request, res_id):
    res_id = int(res_id)
    context = {}
    if request.method == 'POST':
        sortby = request.POST.get('sortby')
        if sortby is None:
            sortby = request.POST.get('lastsort')
        selectedeval = request.POST.get('id_eval')
        if selectedeval is not None:
            date_value = MenuEvaluation.objects.get(pk=selectedeval).menu.date
            sortby = 'day'
        else:
            date_value = datetime.strptime(request.POST.get('date'), '%d/%m/%Y').date()
        if 'previous.x' in request.POST:
            date_value = get_change_by_sortby(date_value, sortby, "previous")
        elif 'next.x' in request.POST:
            date_value = get_change_by_sortby(date_value, sortby, "next")
    else:
        sortby = 'day'
        date_value = datetime.now().date()
    list_eval_noon, note_noon, date_range, context['eval_avg_noon'] = get_list_by_sort(sortby, date_value, 'noon',
                                                                                       res_id)
    if list_eval_noon.count():
        context['menu_noon'] = list_eval_noon[0].menu
        evaluation_noon = get_evaluation(list_eval_noon)
        context['eval_noon'] = evaluation_noon
        context['eval_noon_rounded_entry'] = {get_rounded_notation(evaluation_noon['notation']['entry']): True}
        context['eval_noon_rounded_main_dish'] = {get_rounded_notation(evaluation_noon['notation']['main_dish']): True}
        context['eval_noon_rounded_dessert'] = {get_rounded_notation(evaluation_noon['notation']['dessert']): True}
        context['eval_noon_rounded_service'] = {get_rounded_notation(evaluation_noon['notation']['service']): True}
        if sortby == 'day':
            list_eval_entry = MenuEvaluation.objects.filter(menu__entree=context['menu_noon'].entree,
                                                            menu__date__month=date_value.month,
                                                            menu__date__year=date_value.year)
            context['eval_noon_global_entry'] = {get_global_notation(list_eval_entry, 'entry'): True}
            list_eval_main_dish = MenuEvaluation.objects.filter(menu__main_dish=context['menu_noon'].main_dish,
                                                                menu__date__month=date_value.month,
                                                                menu__date__year=date_value.year)
            context['eval_noon_global_main_dish'] = {get_global_notation(list_eval_main_dish, 'main_dish'): True}
            list_eval_dessert = MenuEvaluation.objects.filter(menu__dessert=context['menu_noon'].dessert,
                                                              menu__date__month=date_value.month,
                                                              menu__date__year=date_value.year)
            context['eval_noon_global_dessert'] = {get_global_notation(list_eval_dessert, 'dessert'): True}
            pics_noon = MealPresentation.objects.filter(meal=context['menu_noon'])
            context['pics_noon'] = {item[0]: pics_noon.filter(item=item[0]).order_by('presentation__default',
                                                                                     'presentation__type')
                                    for loop, item in enumerate(MealPresentation.ITEM_CHOICES)}
    list_eval_evening, note_evening, date_range, context['eval_avg_evening'] = get_list_by_sort(sortby, date_value,
                                                                                                'evening', res_id)
    if list_eval_evening.count():
        context['menu_evening'] = list_eval_evening[0].menu
        evaluation_evening = get_evaluation(list_eval_evening)
        context['eval_evening'] = evaluation_evening
        context['eval_evening_rounded_entry'] = {get_rounded_notation(evaluation_evening['notation']['entry']): True}
        context['eval_evening_rounded_main_dish'] = {
            get_rounded_notation(evaluation_evening['notation']['main_dish']): True}
        context['eval_evening_rounded_dessert'] = {
            get_rounded_notation(evaluation_evening['notation']['dessert']): True}
        context['eval_evening_rounded_service'] = {
            get_rounded_notation(evaluation_evening['notation']['service']): True}
        if sortby == 'day':
            list_eval_entry = MenuEvaluation.objects.filter(menu__entree=context['menu_evening'].entree)
            context['eval_evening_global_entry'] = {get_global_notation(list_eval_entry, 'entry'): True}
            list_eval_main_dish = MenuEvaluation.objects.filter(menu__main_dish=context['menu_evening'].main_dish)
            context['eval_evening_global_main_dish'] = {get_global_notation(list_eval_main_dish, 'main_dish'): True}
            list_eval_dessert = MenuEvaluation.objects.filter(menu__dessert=context['menu_evening'].dessert)
            context['eval_evening_global_dessert'] = {get_global_notation(list_eval_dessert, 'dessert'): True}
            pics_evening = MealPresentation.objects.filter(meal=context['menu_evening'])
            context['pics_evening'] = {item[0]: pics_evening.filter(item=item[0]).order_by('presentation__default',
                                                                                           'presentation__type')
                                       for loop, item in enumerate(MealPresentation.ITEM_CHOICES)}
    context['date_value'] = date_value.strftime('%d/%m/%Y')
    context['sortby'] = sortby
    context['note_noon'] = note_noon
    context['note_evening'] = note_evening
    context['date_range'] = date_range
    context['list_residents'] = User.objects.filter(
        groups__permissions__codename='view_residentehpad').order_by(Lower('last_name'), Lower('first_name'))
    if res_id > 0:
        context['active_select'] = context['list_residents'].get(id=res_id).get_full_name()
    else:
        context['active_select'] = _('All residents')
    return render(request, 'app4_ehpad_base/eval_dashboard.html', context)


@login_required
@permission_required('app0_access.view_evalmenu')
def eval_identification(request):
    if request.method == 'POST':
        if 'valid.x' in request.POST:
            return redirect('Start evaluation', 'auto')
        elif 'invalid.x' in request.POST:
            return render(request, 'app4_ehpad_base/eval_auto_identification.html')
        else:
            request.session['voter'] = None
            request.session['voter_photo_url'] = settings.STATIC_URL + 'app4_ehpad_base/img/appareil_photo.png'
            request.session['voter_name'] = None
            received_key, _, _ = request.POST.get('identified_user').split('/')
            try:
                identified_user = User.objects.get(profileserenicia__folder=received_key)
            except ObjectDoesNotExist:
                msg = str(_("An error has occured"))
                return HttpResponseRedirect('/error/' + msg)
            request.session['voter'] = identified_user.id
            request.session['voter_photo_url'] = get_profile_pic_url(identified_user)
            request.session['voter_name'] = identified_user.first_name + ' ' + identified_user.last_name
            return render(request, 'app4_ehpad_base/eval_validation_identification.html')
    return render(request, 'app4_ehpad_base/eval_auto_identification.html')


def booking_meal_family(post, resident_id, user_id):
    date_value = datetime.strptime(post.get('booking_date'), '%d/%m/%Y').date()
    defaults = {'other_guests': post.get('other'), 'private': False, 'lunch': False, 'dinner': False,
                'surprise': False}
    if post.get('private'):
        defaults['private'] = True
    if post.get('lunch'):
        defaults['lunch'] = True
    if post.get('dinner'):
        defaults['dinner'] = True
    if post.get('surprise'):
        defaults['surprise'] = True
    booking, created = MealBooking.objects.update_or_create(date=date_value,
                                                            owner=Profile.objects.get(
                                                                user=resident_id),
                                                            defaults=defaults)
    list_user = post.getlist('guests')
    list_user.append(User.objects.get(pk=user_id))
    booking.guests.set(list_user)
    trad_booking = _('Your booking for the ') + post.get('booking_date') + _(', for a total of')
    trad_guests = _('guests')
    trad_register = _('has been registered !')
    return {
        'message': f"{trad_booking} {len(list_user) + int(defaults.get('other_guests', 0))} {trad_guests} {trad_register}",
        'category': _('Meal booking')}, booking


def get_booked_meal_list(user_id, year, month):
    days = {'Monday': _('Monday'), 'Tuesday': _('Tuesday'), 'Wednesday': _('Wednesday'), 'Thursday': _('Thursday'),
            'Friday': _('Friday'), 'Saturday': _('Saturday'), 'Sunday': _('Sunday')}
    booked_meal = MealBooking.objects.filter(date__month=month, date__year=year, owner__user__pk=user_id)
    daysnumber = calendar.monthrange(year, month)[1]
    result = []
    week = []
    last_week = datetime(year, month, 1).date().isocalendar()[1]
    for day in range(1, daysnumber + 1):
        tmp_date = datetime(year, month, day).date()
        str_day = days[tmp_date.strftime('%A')][:3] + '. ' + str(day)
        tmp = False
        for book in booked_meal:
            if book.date.day == day:
                if not tmp:
                    tmp = {'date': tmp_date, 'str_day': str_day}
                if book.lunch:
                    tmp['noon'] = book.lunch
                    tmp['guests_lunch'] = book.other_guests
                if book.dinner:
                    tmp['evening'] = book.dinner
                    tmp['guests_dinner'] = book.other_guests
        if not tmp:
            tmp = {'date': tmp_date, 'str_day': str_day, 'noon': False, 'evening': False}
        tmp['menu'] = Meal.objects.filter(date=tmp_date)
        week_number = datetime(year, month, day).date().isocalendar().__getitem__(1)
        if week_number == last_week:
            week.append(tmp)
        else:
            result.append({'week': week.copy(), 'week_number': last_week})
            week.clear()
            week.append(tmp)
            last_week = week_number
    result.append({'week': week.copy(), 'week_number': last_week})
    return result


def save_booked_meal_employee(month, year, listday, user, mealtype):
    for day in listday:
        if datetime(year, month, int(day)).date() >= datetime.now().date():
            datestr = day + "/" + str(month) + "/" + str(year)
            date_value = datetime.strptime(datestr, '%d/%m/%Y').date()
            if not MealBooking.objects.filter(owner=user.profile, date=date_value, other_guests__gt=0).exists():
                tmp = MealBooking.objects.update_or_create(owner=user.profile, date=date_value,
                                                           other_guests=0).__getitem__(0)
                tmp.guests.add(user)
                if mealtype == 'noon':
                    tmp.lunch = True
                elif mealtype == 'evening':
                    tmp.dinner = True
                tmp.save()
    month_range = list(range(1, calendar.monthrange(year, month)[1] + 1))
    for day in month_range:
        if str(day) not in listday:
            if datetime(year, month, day).date() > datetime.now().date():
                datestr = str(day) + "/" + str(month) + "/" + str(year)
                date_value = datetime.strptime(datestr, '%d/%m/%Y').date()
                try:
                    if not MealBooking.objects.filter(owner=user.profile, date=date_value, other_guests__gt=0).exists():
                        tmp = MealBooking.objects.get(owner=user.profile, date=date_value, other_guests=0)
                        if mealtype == 'noon':
                            tmp.lunch = False
                        elif mealtype == 'evening':
                            tmp.dinner = False
                        tmp.save()
                except ObjectDoesNotExist:
                    pass
    return


def booking_meal_employee(post_data, connected_user):
    month = int(post_data.get('month'))
    year = int(post_data.get('year'))
    if post_data.get('next'):
        month += 1
        if month > 12:
            month = 1
            year += 1
    elif post_data.get('previous'):
        month -= 1
        if month < 1:
            month = 12
            year -= 1
    if 'save' in post_data:
        user = User.objects.get(pk=connected_user.id)
        save_booked_meal_employee(month, year, post_data.getlist('noon'), user, 'noon')
        save_booked_meal_employee(month, year, post_data.getlist('evening'), user, 'evening')
    result = {'option': month, 'year': year, 'booklist': get_booked_meal_list(connected_user.id, year, month)}
    return result


def get_message(type_msg):
    msg = {'update': {'message': _('Your modification has been registered'), 'category': _('Booking updated')},
           'save': {'message': _('Your booking has been registered'), 'category': _('Booking saved')},
           'error': {'message': _('Please specify if this is a reservation for lunch or dinner'),
                     'category': _('Missing information')},
           'exist': {
               'message': _('Booking not possible, please check your reservation schedule (group and individual)'),
               'category': _('Registeration not possible')},
           'no guest': {'message': _('Please specifiy the number of guests'), 'category': _('Missing information')}}
    return {'message': msg[type_msg].get('message'), 'category': msg[type_msg].get('category')}


@login_required
@permission_required('app0_access.view_groupreservation')
def group_reservation(request):
    user = User.objects.get(pk=request.user.id)
    form = None
    context = {}
    if request.method == 'POST':
        if request.POST.get('delete'):
            MealBooking.objects.get(pk=request.POST.get('delete')).delete()
        elif request.POST.get('update'):
            form = BookingGroupForm(instance=MealBooking.objects.get(pk=request.POST.get('update')))
            context['save_update'] = request.POST.get('update')
        else:
            form = BookingGroupForm(request.POST)
            if form.is_valid():
                booking = form.save(commit=False)
                if (booking.lunch or booking.dinner) and not (booking.lunch and booking.dinner):
                    booking.owner = user.profile
                    existing = False
                    if booking.lunch:
                        existing = MealBooking.objects.filter(owner=booking.owner, date=booking.date,
                                                              lunch=True, other_guests__gt=0).exists()
                        if not existing:
                            existing = MealBooking.objects.filter(owner=booking.owner, date=booking.date,
                                                                  lunch=True, guests=booking.owner.user).exists()
                    elif booking.dinner:
                        existing = MealBooking.objects.filter(owner=booking.owner, date=booking.date,
                                                              dinner=True, other_guests__gt=0).exists()
                        if not existing:
                            existing = MealBooking.objects.filter(owner=booking.owner, date=booking.date,
                                                                  dinner=True, guests=booking.owner.user).exists()
                    if existing:
                        context.update(get_message('exist'))
                    elif booking.other_guests < 1:
                        context.update(get_message('no guest'))
                    else:
                        if request.POST.get('save_update'):
                            MealBooking.objects.filter(pk=request.POST.get('save_update')).update(
                                other_guests=booking.other_guests,
                                lunch=booking.lunch,
                                dinner=booking.dinner,
                                date=booking.date)
                            context.update(get_message('update'))
                        else:
                            booking.save()
                            context.update(get_message('save'))
                        form = None
                else:
                    context.update(get_message('error'))
    if not form:
        form = BookingGroupForm(initial={'date': timezone.localdate(), 'lunch': True})
    context['form'] = form
    context['next_booking'] = MealBooking.objects.filter(
        owner__user__groups__permissions__codename='view_groupreservation',
        date__gte=timezone.localdate(), other_guests__gt=0).distinct('id')
    return render(request, 'app4_ehpad_base/cuisine_group_reservation.html', context)


def add_booking_to_planning(booking):
    name = _('Meal with') + " "
    for user in booking.guests.all():
        if user == booking.guests.last():
            name += " " + _('and') + " "
        elif not user == booking.guests.first():
            name += ", "
        name += f"{user.first_name} {user.last_name} "
    if booking.other_guests:
        name += f" (+ {booking.other_guests} " + _('other guests') + ")"
    ev = Event.objects.create(type=name, organizer=booking.owner.user.profileserenicia)
    start = datetime(booking.date.year, booking.date.month, booking.date.day, 12, 0, 0, 0,
                     timezone.get_current_timezone())
    pl_ev = PlanningEvent.objects.create(event=ev, start=start, end=start + timedelta(hours=2))
    pl_ev.participants.add(booking.owner.user.profileserenicia)
    PlanningEventBooking.objects.create(booking=booking, planning_event=pl_ev)


def delete_booking_in_planning(booking):
    PlanningEventBooking.objects.filter(booking=booking).delete()


@login_required
def reservation(request):
    context = {}
    if request.method == 'POST':
        if request.user.has_perm('app0_access.view_family'):
            if request.POST.get('delete'):
                booking = MealBooking.objects.get(pk=request.POST.get('delete'))
                delete_booking_in_planning(booking)
                booking.delete()
                return {'message': _('Your reservation has been successfully deleted'),
                        'category': _('Meal booking')}
            else:
                result, booking = booking_meal_family(request.POST, request.session['resident_id'], request.user.id)
                add_booking_to_planning(booking)
                return result
        else:
            context = booking_meal_employee(request.POST, request.user)
    else:
        try:
            request.session.pop('resident_id')
        except KeyError:
            pass
        context['option'] = timezone.now().month
        context['year'] = timezone.now().year
    context['booklist'] = get_booked_meal_list(request.user.id, context['year'], context['option'])
    context['today'] = timezone.localdate()
    return render(request, 'app4_ehpad_base/cuisine_reservation_employee.html', context)


@login_required
@permission_required('app0_access.view_cuisine')
def display_reservation(request):
    booking_list, menutype = get_reservations_now()
    if request.method == 'POST':
        menu = None
        ready = request.POST.get('ready')
        if ready:
            menu = booking_list.get(pk=ready)
            if menutype == 'noon':
                menu.is_lunch_ready = not menu.is_lunch_ready
            else:
                menu.is_dinner_ready = not menu.is_dinner_ready
        else:
            selected_book = request.POST.get('is_served')
            if selected_book:
                menu = booking_list.get(pk=selected_book)
                if menutype == 'noon':
                    menu.is_lunch_served = True
                else:
                    menu.is_dinner_served = True
        menu.save()
    tmp_list = []
    for booking in booking_list:
        if menutype == 'noon':
            tmp_list.append({'booking': booking, 'ready': booking.is_lunch_ready})
        else:
            tmp_list.append({'booking': booking, 'ready': booking.is_dinner_ready})
    try:
        menu = Meal.objects.get(date=datetime.now().date(), type=menutype)
    except ObjectDoesNotExist:
        menu = None
    return render(request, 'app4_ehpad_base/cuisine_display_reservation.html', {'bookinglist': tmp_list, 'menu': menu})


def get_formatted_table(data, style):
    list_data = [[k, v] for k, v in data.items()]
    list_data.insert(0, [_('Name'), _('Quantity')])
    return Table(data=list_data, style=style, hAlign="CENTER")


# ((col, row), (col, row))
# (( start ), ( end ))
def get_table_style_serenicia():
    serenicia_blue = colors.Color(red=147, blue=169, green=210)
    return [('INNERGRID', (0, 1), (-1, -1), 1, colors.black),
            ('BOX', (0, 0), (1, 0), 1, serenicia_blue),
            ('LINEBEFORE', (0, 1), (0, 1), 1, colors.black),
            ('LINEAFTER', (1, 1), (1, 1), 1, colors.black),
            ('BOX', (0, 2), (-1, -1), 1, colors.black),
            ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
            ('BACKGROUND', (0, 0), (1, 0), colors.lightgrey)]


def is_staff(user):
    for perm in ['app0_access.view_as', 'app0_access.view_ash', 'acess.view_ide']:
        if user.has_perm(perm):
            return True
    return False


def define_user_type(user):
    if user.has_perm('app0_access.view_residentehpad'):
        return 'resident'
    elif is_staff(user):
        return 'staff'
    return 'training'


def get_dict_data_reservation(month, year, selectedtable):
    query = MealBooking.objects.filter(date__month=month, date__year=year, other_guests=0).exclude(lunch=False,
                                                                                                   dinner=False)  # no group reservation
    if not query:
        return None
    result = {name: {} for name in selectedtable}
    for booking in query:
        keys = [result[name].keys() for name in selectedtable]
        name = booking.owner.user.get_full_name()
        if name not in keys:
            dict_data = {name: query.filter(owner=booking.owner).count()}
            dict_data[name] += query.filter(owner=booking.owner, lunch=True, dinner=True).count()
            user_type = define_user_type(booking.owner.user)
            if user_type in selectedtable:
                result[user_type].update(dict_data)
    return result


def add_total_to_dict(data):
    data['total'] = {}
    total = 0
    for group in data.keys():
        data['total'][group] = 0
        for user in data[group].keys():
            data['total'][group] += data[group][user]
        if group != 'total':
            total += data['total'][group]
    data['total']['total'] = total
    return data


def get_title(name, styles):
    if name == 'resident':
        return Paragraph(_('Resident'), styles["h3"])
    elif name == 'staff':
        return Paragraph(_('Staff'), styles["h3"])
    elif name == 'training':
        return Paragraph(_('Discovery training'), styles["h3"])


def generate_pdf_reservation(selecteddate, selectedtable, user):
    reservations = get_dict_data_reservation(selecteddate.month, selecteddate.year, selectedtable)
    if not reservations:
        return None
    styles = getSampleStyleSheet()
    title_str = _('Reservations') + ' ' + selecteddate.strftime("%B %Y")
    # buffered document
    pdf_buffer = BytesIO()
    report = SimpleDocTemplate(pdf_buffer, title=title_str, author=user.get_full_name())
    title_style = styles["h1"]
    title_style.alignment = 1  # center title
    title_head = Paragraph(title_str, title_style)
    image = Image(settings.STATIC_ROOT + '/app4_ehpad_base/img/logo_eval-menu_80x32.png', 50 * mm, 27 * mm)
    spacer = Spacer(0, 5 * mm)
    document = [image, spacer, title_head, spacer]
    table_style = get_table_style_serenicia()
    for table_name in selectedtable:
        tmp_table = get_formatted_table(reservations[table_name], table_style)
        document.append(get_title(table_name, styles))
        document.append(tmp_table)
        document.append(spacer)
    title_total = Paragraph(_('Totals'), styles["h3"])
    document.append(title_total)
    reservations = add_total_to_dict(reservations)
    table_total = get_formatted_table(reservations['total'], table_style)
    document.append(table_total)
    report.build(document)
    pdf_buffer.seek(0)  # save buffer
    return {'data': pdf_buffer, 'name': title_str.replace(' ', '') + '.pdf'}


@login_required
@permission_required('app0_access.view_cuisine')
def download_reservation_pdf(request):
    now = datetime.now()
    if request.method == 'POST':
        selectedtable = request.POST.getlist('selectedtable')
        if not selectedtable:
            return render(request, 'app4_ehpad_base/cuisine_reservation_pdf.html', {'now': now, 'error': True})
        selecteddate = datetime.strptime(request.POST.get('month') + request.POST.get('year'), '%m%Y')
        file = generate_pdf_reservation(selecteddate, selectedtable, request.user)
        if not file:
            return render(request, 'app4_ehpad_base/cuisine_reservation_pdf.html', {'now': now, 'empty_date': selecteddate})
        return FileResponse(file['data'], as_attachment=True, filename=file['name'])
    return render(request, 'app4_ehpad_base/cuisine_reservation_pdf.html', {'now': now})
