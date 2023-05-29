import secrets

import requests
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import UniqueConstraint, Q
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from app16_portal.utils import encode_data, decode_data


class Key(models.Model):
    is_public = models.BooleanField(default=True)
    is_local = models.BooleanField(default=False)
    key = models.CharField(max_length=1800)

    def key_bytes(self):
        return bytes(self.key, 'UTF-8')

    def save(self, *args, **kwargs):
        if type(self.key) is bytes:
            self.key = self.key.decode('UTF-8')
        return super(Key, self).save(*args, **kwargs)

    class Meta:
        constraints = [
            UniqueConstraint(fields=['is_public'], condition=Q(is_public=False), name='private_key'),
            UniqueConstraint(fields=['is_public', 'is_local'], condition=Q(is_public=True, is_local=True),
                             name='local_public_key')
        ]


class Group(models.Model):
    name = models.CharField(max_length=200, verbose_name=_('Name'))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('Group')


class Site(models.Model):
    name = models.CharField(max_length=200, verbose_name=_('Name'))
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Group'))
    url_validator = RegexValidator(r"https://", _('Your URL must start by "https://"'))
    url = models.CharField(max_length=200, validators=[url_validator], verbose_name=_('URL'), unique=True)
    facebook = models.CharField(max_length=200, blank=True, null=True, verbose_name=_('Facebook'),
                                help_text=_('auto completion'))
    main_site = models.CharField(max_length=200, blank=True, null=True, verbose_name=_('Main site'),
                                 help_text=_('auto completion'))
    public_key = models.ForeignKey(Key, on_delete=models.CASCADE, blank=True, null=True, verbose_name=_('Public key'),
                                   help_text=_('auto completion'))
    is_linked = models.BooleanField(default=False, verbose_name=_('Is linked'),
                                    help_text=_('The site know the portal public key, auto completion'))

    def __str__(self):
        return f'{self.name} - {self.url}'

    def save(self, *args, **kwargs):
        if not self.public_key and self.url:
            try:
                res = requests.get(str(self.url) + reverse('get public key'), timeout=2)
                if res.status_code == 200:
                    decoded_data = decode_data(res.content)
                    if decoded_data.get('key'):
                        key = Key.objects.create(key=decoded_data.get('key'))
                        self.public_key = key
                        self.facebook = decoded_data.get('facebook')
                        self.main_site = decoded_data.get('main_site')
            except requests.exceptions.RequestException:
                pass
        if not self.is_linked:
            encoded_data = encode_data({'key': Key.objects.get(is_local=True, is_public=True).key})
            try:
                res = requests.post(str(self.url) + reverse('add portal key'),
                                    data={'data': encoded_data.decode('UTF-8')}, timeout=2)
                if res.status_code == 200:
                    self.is_linked = True
            except requests.exceptions.RequestException:
                self.is_linked = False
        return super(Site, self).save(*args, **kwargs)

    class Meta:
        verbose_name = _('Site')


class PortalProfile(User):
    site_group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True,
                                   verbose_name=_('Site group'))
    key = models.CharField(max_length=100, default=secrets.token_urlsafe, verbose_name=_('Connexion key'))
    linked_sites = models.ManyToManyField(Site)

    def linked_sites_id(self):
        return self.linked_sites.values_list('id', flat=True)

    class Meta:
        verbose_name = _('Portal profile')
