from django.urls import path
from . import views, views_messaging, views_notifications


urlpatterns = [
        path('mails/create/', views.mails, name='mails_create'),
        path('mails/send/', views.mails_send, name='mails_send'),
        path('mails/manage/', views.mails_manage, name='mails_manage'),
        path('mails/mailbox/', views.mails_mailbox, name='mails_mailbox'),
        path('mails/lien/open/<str:clef>', views.lien_peculiar, name='mailslinkkey'),
        path('mails/lien/click/<str:clef>/<path:url_encoded>', views.lien_peculiar_click, name='mailslinkkeyclick'),
        path('mails/lien/unsubscribe/<str:clef>', views.lien_unsubscribe, name='mailslinkkeyunsubscribe'),
        path('messagerie/new/', views_messaging.internal_emailing, name='internal_emailing'),
        path('messagerie/new/receiver/<str:mod>/', views_messaging.select_receiver, name='internal_emailing_receiver'),
        path('messagerie/received/', views_messaging.internal_emailing_mailbox, name='internal_emailing_mailbox'),
        path('messagerie/mailbox', views_messaging.internal_emailing_mailbox, name='internal_emailing_mailbox_old'), # just to keep retrocompatibility delete after october 2022
        path('messagerie/sent/', views_messaging.internal_emailing_mailbox_sent,
             name='internal_emailing_mailbox_sent'),
        path('messagerie/mailbox/conv/<int:conv_id>', views_messaging.internal_emailing_conv,
             name='internal_emailing_mailbox_conv'),
        path('messagerie/mailbox/read/<int:conv_id>/', views_messaging.internal_emailing_opened, name='internal_emailing_opened'),
        path('messagerie/notifs/mailbox', views_notifications.notifs_mailbox, name='notifs_mailbox'),
        path('messagerie/notifs/mailbox/read', views_notifications.notifs_opened, name='notifs_opened'),
        path('groups/new/', views_messaging.custom_group_create, name='custom group create'),
        path('groups/modify/<int:selected>/', views_messaging.custom_group_modify, name='custom group modify'),
        path('notification/read/<int:notif_id>/', views_notifications.notif_read, name='notification read'),
    ]
