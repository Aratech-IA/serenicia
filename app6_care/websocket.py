import asyncio
from asgiref.sync import sync_to_async

from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.core.exceptions import ObjectDoesNotExist

from app1_base import log
from app6_care.models import TmpInterventionTreatmentPlanForWebsocket, InterventionTreatmentPlan

log = log.Logger('app6_websocket', level=log.logging.DEBUG).run()


async def app6_websocket(socket):
    await socket.accept()
    cookie = socket.headers['cookie']
    session_id = cookie.split('sessionid=')[1].split(';')[0]
    session_req = sync_to_async(_get_session, thread_sensitive=True)
    session = await session_req(session_id)
    session_data = session.get_decoded()

    user_id = session_data.get('_auth_user_id')
    user_req = sync_to_async(_get_user, thread_sensitive=True)
    user = await user_req(user_id)

    patient_id = session_data.get('resident_id')
    patient_req = sync_to_async(_get_patient, thread_sensitive=True)
    patient = await patient_req(patient_id)

    while True:
        try:
            get_tmp_intervention_req = sync_to_async(_get_tmp_intervention, thread_sensitive=True)
            tmp_intervention = await get_tmp_intervention_req(user, patient)

            get_datas_to_send_req = sync_to_async(_get_datas_to_send, thread_sensitive=True)
            task_id, planned_time, is_done = await get_datas_to_send_req(tmp_intervention)

            if task_id and planned_time:
                data = {'id': task_id, 'isDone': is_done, 'start': planned_time.isoformat()}
                await socket.send_json(data)

                if is_done == False:
                    get_intervention_id_req = sync_to_async(_get_intervention, thread_sensitive=True)
                    intervention_treatment_plan = await get_intervention_id_req(tmp_intervention)

                clean_tmp_table_req = sync_to_async(_clean_tmp_table, thread_sensitive=True)
                await clean_tmp_table_req(tmp_intervention)

                if is_done == False:
                    delete_intervention_req = sync_to_async(_delete_intervention, thread_sensitive=True)
                    await delete_intervention_req(intervention_treatment_plan)

            await asyncio.sleep(1)

        except Exception as ex:
            log.debug(f"Error: {ex}")
            break
    await socket.close()


def _get_user(user_id):
    try:
        user = User.objects.get(id=user_id)
        return user
    except ObjectDoesNotExist:
        return False


def _get_patient(patient_id):
    try:
        user = User.objects.get(id=patient_id)
        return user
    except ObjectDoesNotExist:
        return False


def _get_session(session_id):

    try:
        session = Session.objects.get(session_key=session_id)
        return session
    except ObjectDoesNotExist:
        return False


def _get_tmp_intervention(user, patient):
    try:
        return TmpInterventionTreatmentPlanForWebsocket.objects.get(nurse=user, patient=patient)
    except ObjectDoesNotExist:
        return False


def _get_datas_to_send(tmp_intervention):
    try:
        intervention_treatment_plan = InterventionTreatmentPlan.objects.get(
            tmpinterventiontreatmentplanforwebsocket=tmp_intervention)
        task_id = intervention_treatment_plan.treatment_plan_task.pk
        planned_time = intervention_treatment_plan.planned_time
        is_done = tmp_intervention.is_done

        return task_id, planned_time, is_done

    except (ObjectDoesNotExist, AttributeError):
        return None, None, None


def _clean_tmp_table(tmp_intervention):
    tmp_intervention.delete()


def _delete_intervention(intervention_treatment_plan):
    intervention_treatment_plan.delete()


def _get_intervention(tmp_intervention):
    try:
        return InterventionTreatmentPlan.objects.get(tmpinterventiontreatmentplanforwebsocket=tmp_intervention)
    except ObjectDoesNotExist:
        return False
