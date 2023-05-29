from django.urls import path
from django.views.generic.base import RedirectView

from django.contrib.auth import views as auth_views

from app4_ehpad_base import api_alexa, views_blogger, api_ws_reco, api_ws_reco_on_cam
from . import views, api, api_ws, views_administrative_documents, views_cuisine_eval, views_cuisine_commission, \
    views_personalized_documents

favicon_view = RedirectView.as_view(url='https://dev.serenicia.fr:8080/static/app4_ehpad_base/img/favicon.ico', permanent=True)

urlpatterns = [
     path('', views.index, name='app4_ehpad_base index'),
     path('resident/', views.personal_page, name='personal page'),
     path('welcome/', views.welcome, name='welcome'),
     path('videochat/', views.contact_selection, name="Contact selection"),
     path('contact/', views.contact_selection, name="Contact"),
     path('contact/call/', views.get_videochat_url, name="Contact videochat"),
     path('videochat/call/', views.get_videochat_url, name="Videochat"),
     path('presence/', views.presenceclient, name="Attendance list"),
     path('error/<str:msg>', views.error_msg, name="error message"),
     path('cuisine/newmenu/', views_cuisine_eval.new_menu, name="New menu"),
     path('evaluation/identification/', views_cuisine_eval.eval_identification, name="identification evaluation"),
     path('evaluation/entree/<str:evaltype>', views_cuisine_eval.evaluate_entree, name="Start evaluation"),
     path('evaluation/maindish/<str:evaltype>', views_cuisine_eval.evaluate_main_dish, name="Evaluate main dish"),
     path('evaluation/dessert/<str:evaltype>', views_cuisine_eval.evaluate_dessert, name="Evaluate dessert"),
     path('evaluation/finalize/<str:evaltype>', views_cuisine_eval.finalize_evaluation, name="finalize evaluation"),
     path('cuisine/newmenu/<str:selectdate>/<str:menutype>/<str:substit>/', views_cuisine_eval.new_menu,
          name="Selected menu"),
     path('cuisine/newdish/', views_cuisine_eval.new_dish, name="New dish"),
     path('cuisine/', views_cuisine_eval.cuisine_index, name="Cuisine index"),
     path('cuisine/reservation/', views_cuisine_eval.display_reservation, name="display reservation"),
     # path('cuisine/capture/<int:menu_id>/<str:mealtype>/<str:pic_type>/', views_cuisine_eval.capture, name="capture"),
     path('cuisine/selectmenu/<int:menu_id>/', views_cuisine_eval.select_menu, name="Select menu"),
     path('cuisine/service/<int:menu_id>/', views_cuisine_eval.service_team, name='service team'),
     path('cuisine/dashboard/<str:res_id>/', views_cuisine_eval.dashboard_eval, name="Dashboard evaluation"),
     path('cuisine/booking/', views_cuisine_eval.reservation, name='Meal booking employee'),
     path('cuisine/booking/group/', views_cuisine_eval.group_reservation, name='Meal booking group'),
     path('cuisine/reservation/download/', views_cuisine_eval.download_reservation_pdf, name='dll pdf reservation'),
     path('cuisine/commission/', views_cuisine_commission.prepare_menu_commission, name='menu commission'),
     path('selection/', views.select_resident, name="select resident"),
     path('emptyroomcleaned/<int:room_id>/', views.room_cleaned, name="room cleaned"),
     path('favicon.ico', favicon_view),
     path('photo_list/', views.photo_list, name="photo_list"),
     path('photo_list/<int:image_id>', views.photo_list, name="photo_list_focus"),
     path('getclient/<str:password>', api.get_client, name="get_client"),
     path('getclient/inactive/<str:password>', api.get_client_inactive, name="get_client"),
     path('gallery/', views.access_gallery, name="Gallery"),
     path('gallery/details/', views.gallery_details, name="app4_ehpad_base gallery details"),
     path('photoalbum/<str:name>/', views.photo_from_family, name="photo_from_family"),
     path('photoalbum/', views.photo_from_family, name="new_photo_album"),
     path('ws_image/', api_ws.ws_profile_image),
     path('ws_image_bytes/', api_ws.ws_image_bytes),
     path('security/family/', views.security_family, name="app4_ehpad_base security family"),

     path('ws_reservation/', api_ws.reservation, name='ws reservation'),
     path('ws_client_in_alert/', api_ws.client_in_alert, name='ws client in alert'),
     path('alexa', api_alexa.get_action),
     path('ws_alexa/', api_alexa.alexa_order),
     path('blog/gestion/', views_blogger.create_or_edit_post, name='public_photo'),
     path('blog/gestion/create_post/<int:act_id>/', views_blogger.create_post, name='create_post'),
     path('blog/<int:post_id>/', views_blogger.show_post, name='show_post'),
     path('blog/image/', views_blogger.show_post_image, name='show_post_picture'),
     path('passphrase/', views.record_passphrase, name='record passphrase'),
     path('record/<str:onboard>/', views.record_word, name='record word'),
     path('identification/', views.face_reco, name='face reco'),

     path('blog/gestion/edit_post/<int:post_id>/', views_blogger.edit_post, name='edit_post'),
     path('blog/gestion/delete_post/<int:post_id>/', views_blogger.delete_post, name='delete_post'),
     path('blog/gestion/delete_picture/<int:picture_id>/', views_blogger.delete_picture, name='delete_picture'),
     path('api/blog/', views_blogger.get_api_blog, name="get_api_blog"),

     path('blog/', views_blogger.show_blog, name='blog'),
     path('multiple_faces/', api_ws_reco.multiple_faces, name='ws multiple faces'),
     path('reco_on_cam/', api_ws_reco_on_cam.reco_on_cam, name='ws reco on camera'),
     path('photoform/', views.public_photo_form, name='public photo form'),

     # Documents:
     path('invoice/', views_administrative_documents.invoice, name='invoice'),
     path('documents/', views_administrative_documents.documents, name='documents'),
     path('documents/<int:pk>/', views_administrative_documents.delete_card, name='delete_card'),

     path('personalized_documents/', views_personalized_documents.check_user_field, name='personalized_documents'),
     path('sign_documents/', views_administrative_documents.sign_documents, name='sign_document'),
     path('documents/signed/', views_administrative_documents.document_signed, name='document_signed'),

     path('inventory/', views_administrative_documents.inventory, name='inventory'),
     path('create_inventory/', views_administrative_documents.kit_inventory, name='create_inventory'),
     path('laundry_management/', views_administrative_documents.laundry_management, name='laundry_management'),

     path('resident_form/', views_administrative_documents.resident_form, name='resident_form'),
     path('diet/', views_administrative_documents.diet, name='diet'),

     path('account', views.create_account, name='create account'),
    ]
