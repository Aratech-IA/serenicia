"""
This is the repartition algorithm for residents to employees :

The rules are :
_ Consecutive room number
_ balance in the number of residents per employee
_ UP volonteer only fo UP residents
_ Possibility of manual affectation, the manual affectation will not move at all
_ Proximity association between experimented employee and newbie employee
_ Maximize the stability when number of resident or employee change.

"""
from app1_base.models import Profile
from app1_base.log import Logger
from app4_ehpad_base.models import ProfileSerenicia, UserListIntermediate
from app6_care.views import resident_employee, resident_employee_manual
import datetime

import logging

if 'log_shuffle' not in globals():
    global log_algo_shuffles
    log_algo_shuffles = Logger('algo_shuffles', file=True, level=logging.INFO).run()


def get_residents(access, up=False):
    """
    :param up:
    :param access:
    :return: list of resident for a categorie without manual affectation
    """
    # exclude resident without Client and resident already manually affected
    manual_resident = UserListIntermediate.objects.filter(
        profileserenicia__user__groups__permissions__codename=access,
        was_manual=True, profile__client__sector__is_UP=up).values_list("profile", flat=True)
    residents = Profile.objects.filter(user__groups__permissions__codename='view_residentehpad',
                                       client__isnull=False, client__sector__is_UP=up, user__is_active=True).exclude(
        user__profileserenicia__status="deceased").exclude(id__in=manual_resident).order_by('client__sector',
                                                                                            'client__room_number')
    log_algo_shuffles.debug(f'Get Resident -->List of resident nb is {residents.count()}'
                            f' / Manual is {manual_resident.count()}')
    return residents


def get_employees(access, up=False):
    """
    delete relation before returning
    :param up:
    :param access:
    :return: list of employees of category access ordered by entry date
    """
    log_algo_shuffles.debug(f"SHUFFLE access concerned: {access}")
    employees = ProfileSerenicia.objects.filter(user__groups__permissions__codename=access, UP_volunteer=up,
                                                user__profile__advanced_user=False)
    employees = employees.exclude(user__last_login__isnull=True).exclude(user__is_active=False)
    employees = employees.order_by('entry_date')
    log_algo_shuffles.debug(f'List of {access} is {employees} nb is {employees.count()}')
    return employees


def make_dispo_dict(residents, affectation_employees_manual):
    if not affectation_employees_manual:
        return [{}, {}]
    nb_residents = (len(residents))
    dict_affectation_final = affectation_employees_manual.copy()
    list_dict_affectation = []
    for tour in range(2):
        for _ in range(nb_residents):
            employee_concerned = min(dict_affectation_final, key=dict_affectation_final.get)
            if tour < len(dict_affectation_final):  # this is for the case one employee in UP
                dict_affectation_final[employee_concerned] += 1
        list_dict_affectation.append(dict_affectation_final.copy())
    return list_dict_affectation


def dispo_by_employee(access, residents_normal, residents_up):
    # UP is taken separatly
    affectation_employees_manual_up = resident_employee_manual(access, up=True)
    affectation_employees_manual_up = {key: len(value) for key, value in affectation_employees_manual_up.items()}
    list_dict_affectation_final_up = make_dispo_dict(residents_up, affectation_employees_manual_up)

    # global affectation
    affectation_employees_manual_normal = resident_employee_manual(access, up=False)
    affectation_employees_manual_normal = {key: len(value) for key, value in affectation_employees_manual_normal.items()}
    dict_manual_up = {**affectation_employees_manual_normal, **list_dict_affectation_final_up[1]}
    list_dict_manual_up = make_dispo_dict(residents_normal, dict_manual_up)

    list_dict_affectation_final = [
        {'up': list_dict_affectation_final_up[0], 'normal': list_dict_manual_up[0]},
        {'up': list_dict_affectation_final_up[1], 'normal': list_dict_manual_up[1]},
    ]
    return list_dict_affectation_final


def dispo_by_employee_initial(access):
    return {**{k: len(v) for k, v in resident_employee_manual(access, up=True).items()},
            **{k: len(v) for k, v in resident_employee_manual(access, up=False).items()}}


def delete_affectations(access):
    """
    remove all automatic affectations for employees
    :param access:
    :return:
    """
    employees = ProfileSerenicia.objects.filter(user__groups__permissions__codename=access,
                                                user__profile__advanced_user=False)
    UserListIntermediate.objects.filter(profileserenicia__in=employees, was_manual=False).delete()


def make_employee_resident(affectation):
    employee_resident = {}
    for employee, resident in affectation.items():
        for res in resident:
            if res in employee_resident:
                employee_resident[res].append(employee)
            else:
                employee_resident[res] = [employee, ]
    return employee_resident


def get_closer_employee(res, residents, previous_affectation_residents, employees, affectation_tour,
                        last_employee=None):
    """
    Closer by room but farest by entry_date

    The first part affectation tour is useful only if you want to make the affectation of residents in two part
    half part each time. If affectation_tour is none the first part is not used.

    :param affectation_tour:
    :param res:
    :param residents:
    :param previous_affectation_residents:
    :param employees:
    :param last_employee:
    :return: Profil
    """
    log_algo_shuffles.debug(f'GET CLOSER EMPLOYEE / last_employee -------> {last_employee}')
    if res in affectation_tour:
        first_tour_employee = affectation_tour[res][0]
        # find the previous employee
        index_resident = list(residents).index(res)
        # first part of reverse list
        try:
            previous_employee = [affectation_tour[r] for r in list(residents)[index_resident::-1] if
                                 affectation_tour[r][0] != first_tour_employee and affectation_tour[r][0] in
                                 employees]
            if previous_employee:
                previous_employee = previous_employee[0][0]
            else:
                previous_employee = [affectation_tour[r] for r in list(residents)[len(residents):1:-1] if
                                     affectation_tour[r][0] != first_tour_employee and affectation_tour[r][0] in
                                     employees][0][0]
            return previous_employee
        except IndexError:
            log_algo_shuffles.debug(f'except no previous employee return employee not the last')
            for em in employees:
                if em is not first_tour_employee:
                    log_algo_shuffles.debug(f'except no previous employee return employee not the last ---> {em}')
                    return em
            return None
    else:
        log_algo_shuffles.debug(f'Tour 0')
        good_employee = None
        i = list(residents).index(res)
        for res in residents[i:]:
            try:
                experience_diff = datetime.timedelta(seconds=0)  # add crit of entry date
                good_employee = None
                for employee in previous_affectation_residents[res]:
                    if employee.id in employees:
                        if last_employee:
                            _experience_diff = abs(employee.entry_date - last_employee.entry_date)
                            log_algo_shuffles.debug(f'experience diff {_experience_diff}')
                            if _experience_diff >= experience_diff:
                                experience_diff = _experience_diff
                                good_employee = employee
                        else:
                            return employee
                if good_employee:
                    return good_employee
            except KeyError:
                pass
        if not last_employee:
            if employees:
                return employees[0]
            return None
        else:
            experience_diff = datetime.timedelta(seconds=0)  # add crit of entry date
            for employee in employees:
                _experience_diff = abs(employee.entry_date - last_employee.entry_date)
                log_algo_shuffles.debug(f'---** last part {employee}/{employee.entry_date}-->{last_employee.entry_date}'
                                        f' {_experience_diff}')
                if _experience_diff >= experience_diff:
                    experience_diff = _experience_diff
                    good_employee = employee
            return good_employee


def round_tour(access, previous_affectation_residents, employees_actual, employees_final,
               new_affectation=None, up=True):
    # get the first tour affectation if exists
    if new_affectation is None:
        _round = 0
        new_affectation = {}
    else:
        _round = 1
    affectation_tour = make_employee_resident(new_affectation)
    _new_affectation = {}

    # get the employees
    if up:
        _employees_final = employees_final[_round]['up'].copy()
    else:
        _employees_final = employees_final[_round]['normal'].copy()

    residents = get_residents(access, up=up)
    employees = list(_employees_final.keys())
    if not employees:  # case nobody is up volonteer
        return new_affectation
    log_algo_shuffles.info(f'>>>>>>>>>>>>>>>>>>> The residents to affects are  {residents}-->{residents.count()}'
                           f' for employees : \n'
                           f' {employees}-->{len(employees)}')

    # first iter to affect residents
    _residents = residents[:]
    res = residents[0]
    employee = get_closer_employee(res, _residents, previous_affectation_residents, employees, affectation_tour)

    if not employee:  # affectation impossible no employee available skip and re-calcule the final state
        log_algo_shuffles.info(f'!!!!!! Can not find employee for {res} !!!!!!!!!!')
        # for _ in range(len(_residents)):
        #     dict_employees_concerned = {k: v for k, v in {**employees_final[_round]['up'],
        #                                 **employees_final[_round]['normal']}.items()
        #                                 if v-employees_actual[k] > 0}
        #
        #     employee_to_decreased = max(dict_employees_concerned, key=dict_employees_concerned.get)
        #     if employee_to_decreased in employees_final[_round]['up'].keys():
        #         employees_final[_round]['up'][employee_to_decreased] -= 1
        #     else:
        #         employees_final[_round]['normal'][employee_to_decreased] -= 1
        return _new_affectation

    employees.remove(employee)
    if employees_actual[employee] < _employees_final[employee]:
        _new_affectation[employee] = [res, ]
        employees_actual[employee] += 1
        log_algo_shuffles.info(f'>>>> New affectation of {res} room {res.client.room_number} for {employee}')
        residents = residents.exclude(id=res.id)

    #  next iter for the other residents
    for res in residents[:]:
        if employees_actual[employee] >= _employees_final[employee]:  # change employee
            while employees_actual[employee] >= _employees_final[employee]:  # affect only if max not reach
                employee = get_closer_employee(res, _residents, previous_affectation_residents, employees,
                                               affectation_tour, last_employee=employee)
                log_algo_shuffles.debug(f'Get closer employee of {res} -> {employee}')
                log_algo_shuffles.debug(f'parameters residents->{_residents}  employees->{employees}')

                if not employee:  # affectation impossible no employee available skip and re-calcule the final state
                    log_algo_shuffles.info(f'!!!!!! Can not find employee for {res} !!!!!!!!!!')
                    # for _ in range(len(_residents)):
                    #     dict_employees_concerned = {k: v for k, v in {**employees_final[_round]['up'],
                    #                                                   **employees_final[_round]['normal']}.items()
                    #                                 if v - employees_actual[k] > 0}
                    #
                    #     employee_to_decreased = max(dict_employees_concerned, key=dict_employees_concerned.get)
                    #     if employee_to_decreased in employees_final[_round]['up'].keys():
                    #         employees_final[_round]['up'][employee_to_decreased] -= 1
                    #     else:
                    #         employees_final[_round]['normal'][employee_to_decreased] -= 1
                    return _new_affectation
                employees.remove(employee)
            _new_affectation[employee] = [res, ]
            employees_actual[employee] += 1
            log_algo_shuffles.info(f'>> Affectation of : {res}  ROOM {res.client.room_number} to {employee}')
            residents = residents.exclude(id=res.id)
        else:
            _new_affectation[employee].append(res)
            log_algo_shuffles.info(f'>> Affectation of : {res}  ROOM {res.client.room_number} to {employee}')
            residents = residents.exclude(id=res.id)
            employees_actual[employee] += 1
    return _new_affectation


def concatenate_dict(dict1, dict2):
    new_dict = {}
    for key, value in dict1.items():
        if key in dict2:
            new_dict[key] = value + dict2[key]
        else:
            new_dict[key] = value
    for key, value in dict2.items():
        if key not in dict1:
            new_dict[key] = value
    return new_dict


def affect_employees(access):
    previous_affectation_employees = resident_employee(access)
    previous_affectation_residents = make_employee_resident(previous_affectation_employees)

    residents_normal = get_residents(access, up=False)
    residents_up = get_residents(access, up=True)

    employees_initial = dispo_by_employee_initial(access)
    employees_final = dispo_by_employee(access, residents_normal, residents_up)
    employees_final[0] = employees_final[1]  # force consecutive affectation

    #  Round 1
    new_affectation1 = round_tour(
        access, previous_affectation_residents, employees_initial, employees_final, up=True)
    log_algo_shuffles.info(f'------------------------------------------------')

    new_affectation3 = round_tour(
        access, previous_affectation_residents, employees_initial, employees_final, up=True)
    log_algo_shuffles.info(f'------------------------------------------------')

    new_affectation2 = round_tour(
        access, previous_affectation_residents, employees_initial, employees_final, up=False)
    log_algo_shuffles.info(f'------------------------------------------------')

    new_affectation4 = round_tour(
        access, previous_affectation_residents, employees_initial, employees_final, up=False)

    new_affectation = concatenate_dict(new_affectation1, new_affectation2)
    new_affectation = concatenate_dict(new_affectation, new_affectation3)
    new_affectation = concatenate_dict(new_affectation, new_affectation4)

    return new_affectation


def save_affectation(access):
    affectation = affect_employees(access)
    if affectation:
        delete_affectations(access)
        for employee, list_profile in affectation.items():
            employee.user_list.add(*list_profile)


def reset_all_affectation():
    scope = ['view_ide', 'view_ash', 'view_as']
    UserListIntermediate.objects.filter(profileserenicia__user__groups__permissions__codename__in=scope).delete()


def reset_all_manual_affectation():
    scope = ['view_ide', 'view_ash', 'view_as']
    UserListIntermediate.objects.filter(profileserenicia__user__groups__permissions__codename__in=scope,
                                        was_manual=True).delete()


def reset_all_inactive_affectation():
    UserListIntermediate.objects.filter(profile__user__is_active=False).delete()


def main():
    reset_all_inactive_affectation()
    save_affectation('view_as')
    print(f'\n\n\n')
    save_affectation('view_ide')
    print(f'\n\n\n')
    save_affectation('view_ash')


if __name__ == "__main__":
    main()
