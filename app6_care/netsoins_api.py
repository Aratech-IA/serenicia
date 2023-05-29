from urllib.parse import quote_plus

import requests

from app1_base import log
from app4_ehpad_base.api_netsoins import TLSAdapter
from app4_ehpad_base.models import ProfileSerenicia
from app6_care.models import InterventionDetail, TaskComment

from projet.settings.settings import NETSOINS_URL, NETSOINS_TYPE, NETSOINS_KEY

log_netsoins = log.Logger('api_netsoins', level=log.logging.DEBUG).run()
session = requests.session()
session.mount('https://', TLSAdapter())


def post_intervention(intervention):
    selected_treatments = '[ '
    commented_tasks = ''

    for detail in InterventionDetail.objects.filter(intervention=intervention):
        if detail.task_level_4:
            selected_treatments += '|' + detail.task_level_4.name + '|'
        elif detail.task_level_3:
            selected_treatments += '|' + detail.task_level_3.name + '|'
        elif detail.task_level_2:
            selected_treatments += ' ]'

    comments = TaskComment.objects.filter(intervention=intervention)
    for comment in comments:
        commented_tasks += '[ '
        if comment.related_task_level_2:
            commented_tasks += comment.related_task_level_2.name + ' : ' + comment.content
        elif comment.related_task_level_3:
            commented_tasks += comment.related_task_level_3.name + ' : ' + comment.content
        else:
            commented_tasks += comment.related_task_level_4.name + ' : ' + comment.content
        commented_tasks += ' ]'

    try:
        uri_resident = ProfileSerenicia.objects.get(user=intervention.patient).uri_netsoins
        response = session.get(NETSOINS_URL + 'Resident?' + NETSOINS_TYPE + '&' + NETSOINS_KEY +
                               '&output=json&input=json&fields=EtablissementChambre&Uri=' + quote_plus(uri_resident))
        uri_etablissement_chambre = response.json()['Resident'][0]['EtablissementChambre']['Uri']

        # in the response, Netsoins API returns a "WS-Code" attribute equal to 0 when everything is OK
        if response.json()['WS-Code'] != 0:
            log_netsoins.debug(f"Cannot GET resident on API NETSOINS with resident : {intervention.patient}")

    except requests.exceptions.RequestException as e:
        log_netsoins.debug(f"Error: {e}, cannot GET resident on API NETSOINS with uri_resident : {uri_resident}, "
                           f"response : {response.json()}")

    transmission = [
        {'IdentifiantExterne': intervention.patient.id,
         'Module': 1,
         'UriResident': uri_resident,
         'UriEtablissementChambre': uri_etablissement_chambre,
         'DateDebut': intervention.start.isoformat(),
         'DateFin': intervention.end.isoformat(),
         'TransmissionMessage': [{
             'IdentifiantExterne': intervention.id,
             'Message': 'category : ' + intervention.type.name + ', commented_treatments : ' +
                        commented_tasks + ', selected_treatments : ' + selected_treatments,
             'Date': intervention.end.isoformat(),
             'Type': 'NARRATIVE',
             'UriPersonnel': ProfileSerenicia.objects.get(user=intervention.nurse).uri_netsoins
         }]}]

    try:
        response = session.post(NETSOINS_URL + 'Transmission?' + NETSOINS_TYPE + '&' + NETSOINS_KEY +
                                '&output=json&input=json', json=transmission)
        # in the response, Netsoins API returns a "WS-Code" attribute equal to 0 when everything is OK
        if response.json()['WS-Code'] == 0:
            log_netsoins.info(f"intervention_id : {intervention.id} has been successfully POST on Netsoins API")
        else:
            log_netsoins.debug(f"Cannot POST transmission on Netsoins API: {transmission}, "
                               f"response : {response.json()}")

    except requests.exceptions.RequestException as e:
        log_netsoins.debug(f"Error: {e}, cannot POST transmission on Netsoins API: {transmission}, "
                           f"response : {response.json()}")


def post_free_comment(free_comment):
    try:
        uri_resident = ProfileSerenicia.objects.get(user=free_comment.patient).uri_netsoins
        response = session.get(NETSOINS_URL + 'Resident?' + NETSOINS_TYPE + '&' + NETSOINS_KEY +
                               '&output=json&input=json&fields=EtablissementChambre&Uri=' + quote_plus(uri_resident))
        uri_etablissement_chambre = response.json()['Resident'][0]['EtablissementChambre']['Uri']

        # in the response, Netsoins API returns a "WS-Code" attribute equal to 0 when everything is OK
        if response.json()['WS-Code'] != 0:
            log_netsoins.debug(f"Cannot GET resident on API NETSOINS with uri_resident : {uri_resident}, "
                               f"response : {response.json()}")

    except requests.exceptions.RequestException as e:
        log_netsoins.debug(f"Cannot GET resident on API NETSOINS with resident : {free_comment.patient}")

    transmission = [
        {'IdentifiantExterne': free_comment.patient.id,
         'Module': 1,
         'UriResident': uri_resident,
         'UriEtablissementChambre': uri_etablissement_chambre,
         'DateDebut': free_comment.start.isoformat(),
         'DateFin': free_comment.start.isoformat(),
         'TransmissionMessage': [{
             'IdentifiantExterne': free_comment.id,
             'Message': free_comment.content,
             'Date': free_comment.start.isoformat(),
             'Type': 'NARRATIVE',
             'UriPersonnel': ProfileSerenicia.objects.get(user=free_comment.nurse).uri_netsoins
         }]}]

    try:
        response = session.post(NETSOINS_URL + 'Transmission?' + NETSOINS_TYPE + '&' + NETSOINS_KEY +
                                '&output=json&input=json', json=transmission)
        # in the response, Netsoins API returns a "WS-Code" attribute equal to 0 when everything is OK
        if response.json()['WS-Code'] == 0:
            log_netsoins.info(f"intervention_id : {free_comment.id} has been successfully POST on Netsoins API")
        else:
            log_netsoins.debug(f"Cannot POST transmission on Netsoins API: {transmission}, "
                               f"response : {response.json()}")

    except requests.exceptions.RequestException as e:
        log_netsoins.debug(f"Error: {e}, cannot POST transmission on Netsoins API: {transmission}, "
                           f"response : {response.json()}")