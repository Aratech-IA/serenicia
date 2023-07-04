from django.urls import path

from app6_care.views.care_plan import care_plan_creation, show_event, create_event, delete_event, update_event, \
    change_task_color, care_plan, care_plan_intervention, finalize_intervention, care_plan_cancel, add_comment,\
    delete_comment
from app6_care.views.views_nappy_management import views_nappy_management, \
    views_nappy_restock, views_nappy_order, views_nappy_delivery, views_nappy_inventory
from app6_care.views.views_caregiver import views_caregiver, views_caregiver_treatment_plan, views_showers_report, \
    views_caregiver_free_comment, views_interventions_report, views_caregiver_treatment_plan_creation, dlProtocol, \
    plan_de_soin, plan_de_soin_jour, last_comments
from app6_care.websocket import app6_websocket

from app6_care.views.views_rela_table import table_relations
from app6_care.views.views_hotel import views_hotel, views_hotel_free_comment, personal_index

urlpatterns = [
    path('relat_table/', table_relations, name="table_relations"),

    # ----------------------- related to nappy_management -----------------------
    path('nappy_management/', views_nappy_management, name='nappy_management'),
    path('nappy_restock/', views_nappy_restock, name='nappy_restock'),
    path('nappy_inventory/', views_nappy_inventory, name='nappy_inventory'),
    path('nappy_delivery/', views_nappy_delivery, name='nappy_delivery'),
    path('nappy_order/', views_nappy_order, name='nappy_order'),

    # -----------------------  related to caregiver -----------------------
    path('caregiver/', views_caregiver, name='caregiver'),
    path('caregiver/free_comment/', views_caregiver_free_comment, name='caregiver_free_comment'),
    path('caregiver/treatments_plan/<str:profession>/<int:patient_id>/', views_caregiver_treatment_plan,
         name='caregiver_treatments_plan'),
    path('caregiver/treatments_plan_creation/<str:profession>/<int:patient_id>/',
         views_caregiver_treatment_plan_creation, name='caregiver_treatments_plan_creation'),
    path('app6_websocket/', app6_websocket),
    path('caregiver/plan_de_soin/<int:patient_id>/', plan_de_soin, name='plan_de_soin'),
    path('caregiver/plan_de_soin/<int:patient_id>/<int:day_id>/', plan_de_soin_jour, name='plan_de_soin_jour'),
    path('showers_report/', views_showers_report, name='showers_report'),
    path('interventions_report/', views_interventions_report, name='interventions_report'),

    # -----------------------  care plan -----------------------
    path('caregiver/plan/', care_plan_creation, name='care plan creation'),
    path('caregiver/plan/intervention/<int:lvl1>/<int:lvl1_inter_id>/<int:lvl2>/<int:lvl3>/<int:lvl4>/',
         care_plan_intervention, name='care plan intervention'),
    path('caregiver/plan/finalize/<int:lvl1>/<int:lvl1_inter_id>/', finalize_intervention,
         name='finalize intervention'),
    path('caregiver/plan/care/comment/<int:lvl1>/<int:lvl1_inter_id>/<int:lvl2>/<int:lvl3>/<str:comment>/', add_comment,
         name='care plan comment'),
    path('caregiver/plan/care/comment/delete/<int:com_id>/', delete_comment, name='care plan comment delete'),
    path('caregiver/plan/care/cancel/<int:detail_id>/', care_plan_cancel, name='care plan cancel'),
    path('caregiver/plan/create/', create_event, name='app6_care create cal event'),
    path('caregiver/plan/update/<int:pl_event_id>/<str:start>/', update_event, name='app6_care update event'),
    path('caregiver/plan/delete/<int:pl_event_id>/', delete_event, name='app6_care delete event'),
    path('caregiver/plan/modal/<int:pl_ev_id>/', show_event, name='app6_care show event'),
    path('caregiver/plan/color/<int:task_id>/<str:color>/', change_task_color, name='app6_care change task color'),
    path('caregiver/plan/care/', care_plan, name='care plan'),
    path('caregiver/comments/last/', last_comments, name='care last comments'),

    # -----------------------  related to hotel -----------------------
    path('hotel/', views_hotel, name='hotel'),
    path('hotel/free_comment/', views_hotel_free_comment, name='hotel_free_comment'),
    path('hotel/index/', personal_index, name='personal index hotel'),
    path('dlProtocol/<int:protocol_id>/', dlProtocol, name='app6_care dlProtocol'),
]
