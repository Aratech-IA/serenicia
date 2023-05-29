from django.urls import path
from . import views, views_qualite

urlpatterns = [
    path('', views.index, name='app11_quality index'),
    path('protocols_list/', views.protocols_list, name='app11_quality protocols'),
    path('protocols_list/<int:response_id>/', views.protocols_list, name='app11_quality selectProtocols'),
    path('protocols_list/addExistingTag/<int:protocol_id>', views.addExistingTag, name='app11_quality addExistingTag'),
    path('protocols_list/dl/<int:protocol_id>/', views.dlProtocol, name='app11_quality dlProtocol'),
    path('protocols_list/deleteTag/<int:protocol_id>/<int:tag_id>/', views.removeTagRelation, name='app11_quality '
                                                                                                   'removeTagRelation'),
    path('protocols_list/deleteProtocol/<int:protocol_id>/', views.deleteProtocol, name='app11_quality deleteProtocol'),
    path('protocols_list/addProtocol/', views.addNewProtocol, name='app11_quality addNewProtocol'),
    path('chat/', views.chat, name='app11_quality chat'),
    path('chat/enter/', views.enter, name='enter'),
    path('chat/enter/chat/<str:room>/', views.room, name='app11_quality room'),
    path('chat/enter/chat/<str:room>/send/', views.send, name='send'),
    path('ws_chat/', views.ws_chat, name='ws_chat'),
    path('getMessages/<str:room>/', views.getMessages, name='getMessages'),
    path('quality/index-fiche-critere/', views_qualite.index_fiche_critere, name='app11_quality index-fiche-critere'),
    path('quality/fiche-critere/<int:manual_id>', views_qualite.fiche_critere, name='app11_quality fiche-critere'),
    path('<int:protocol_id>/', views.toPdf, name='app11_quality pdf'),
    path('download/evaluations/', views_qualite.download_pdf, name='app11_quality pdf evaluations'),
    path('download/evaluations/xls/', views_qualite.download_xls, name='app11_quality xls evaluations'),
    path('manager/<int:crit_id>/', views_qualite.select_manager, name='app11_quality select manager'),
]
