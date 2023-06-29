from django.conf import settings
from django.conf.urls import include

from django.urls import path
from django.utils.translation import gettext_lazy as _
from django.shortcuts import redirect

from django.views.generic.base import RedirectView

from django.contrib import admin
from django.contrib.auth import views as auth_views

from app1_base import api
from app1_base.admin_debug import admin_debug

admin.site.site_header = settings.DOMAIN+" Admin"
admin.site.site_title = settings.DOMAIN+" Admin"
admin.site.index_title = "Manage sensors, users and alert :"


if "protecia" in settings.DOMAIN.lower():
    urlpatterns = [
        path('', include('app1_base.urls')),
        path('appmail/', include('app3_messaging.urls')),
        ]
elif "serenicia" in settings.DOMAIN.lower():
    urlpatterns = [
        path('', include('app4_ehpad_base.urls')),
        path('security/', include('app1_base.urls')),
        path('app13_resident/', include('app13_resident.urls')),
        path('appmail/', include('app3_messaging.urls')),
        path('appmail/', include('app5_ehpad_messaging.urls')),
        path('app6_care/', include('app6_care.urls')),
        path('recognize/', include('app7_video.urls')),
        path('profile/', include('app14_profile.urls')),
        path('monavis/', include('app8_survey.urls')),
        path('support/', include('app9_personnalized_project.urls')),
        path('animation/', include('app10_social_activities.urls')),
        path('i18n/', include('django.conf.urls.i18n')),
        path('app11_quality/', include('app11_quality.urls')),
        path('referential/', include('app11_quality.urls')),
        path('app12_delivery/', include('app12_delivery.urls')),
        path('management/', include('app0_access.urls')),
        path('calendar/', include('app15_calendar.urls')),
        path('portal/', include('app16_portal.urls')),
        path('help/', include('app17_help.urls')),
        # path('__debug__/', include('debug_toolbar.urls')),
    ]
    # try:
    #     # urlpatterns.append(path('', include('app999_commercial.urls')),)
    # except RuntimeError:
    #     pass
else:
    urlpatterns = []

if "protecia" in settings.DOMAIN.lower():
    favicon_view = RedirectView.as_view(url=settings.STATIC_URL+'app1_base/img/favicon.ico', permanent=True)
elif "serenicia" in settings.DOMAIN.lower():
    favicon_view = RedirectView.as_view(url=settings.STATIC_URL+'app4_ehpad_base/img/favicon.ico', permanent=True)
else:
    favicon_view = None

urlpatterns += [
    path('uploadimage', api.upload_image),
    path('uploadresult', api.upload_result),
    path('conf', api.init_conf),
    path('ws', api.ws_cam),
    path('ws_receive_cam', api.ws_receive_cam),
    path('ws_send_cam', api.ws_send_cam),
    path('favicon.ico', favicon_view),
    path('debug_admin/', admin_debug.urls),
    path('ws_get_state', api.ws_get_state),
    path('ws_get_camera_state', api.ws_get_camera_state),
    path('ws_run_cam_result', api.ws_run_cam_result),
    path('ws_run_cam_img', api.ws_run_cam_img),
    path('ws_run_cam_img_real', api.ws_run_cam_img_real),
    path('admin/', admin.site.urls),
    path('__debug__/', include('debug_toolbar.urls')),

    path('accounts/', include('django.contrib.auth.urls')),

    # Reset password
    path('password_reset/',
         auth_views.PasswordResetView.as_view(template_name='registration/password_reset.html'),
         name='password_reset'),

    path('password_reset_sent/',
         auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_sent.html'),
         name='password_reset_done'),

    path('reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_form.html'),
         name='password_reset_confirm'),

    path('password_reset_complete/',
         auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_done.html'),
         name='password_reset_complete'),
    ]


def error_404(request, exception):
    return redirect('https://serenicia.net')


handler404 = error_404

