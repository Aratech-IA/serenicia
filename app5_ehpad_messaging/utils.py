from django.conf import settings as param
from app1_base.models import ProfileSecurity
from app4_ehpad_base.models import *

# The model used for this app depend on the domain Protecia or Serenicia, we need to get the correct model.
if "protecia" in param.DOMAIN.lower():
    model_linked = ProfileSecurity
else:
    from app4_ehpad_base.models import ProfileSerenicia
    model_linked = ProfileSerenicia


def create_ref(resident, access, already_sent=False):
    ref_temp = model_linked.objects.filter(user__groups__permissions__codename=access,
                                           user_list=resident.profile)
    ref_temp = ref_temp.exclude(user__last_login__isnull=True).exclude(user__is_active=False)
    if already_sent:
        ref_temp = ref_temp.exclude(user__id__in=already_sent)
    return [ref.user for ref in ref_temp]
