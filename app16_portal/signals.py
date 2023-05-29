from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse

from app16_portal.models import PortalProfile, Key
from app16_portal.utils import post_message


@receiver(post_save, sender=PortalProfile)
def update_sites(instance, **kwargs):
    data = {'last_name': instance.last_name, 'first_name': instance.first_name, 'email': instance.email,
            'portal_token': instance.portalprofile.key, 'phone_number': instance.profile.phone_number or '',
            'civility': instance.profile.civility or '', 'adress': instance.profile.adress or '',
            'cp': instance.profile.cp or '', 'city': instance.profile.city or '',
            'birth_date': instance.profileserenicia.birth_date.isoformat() or ''}
    for site in instance.linked_sites.all():
        post_message(site.url + reverse('update portal user'), 2, data,
                     Key.objects.get(is_local=True, is_public=False).key_bytes())
