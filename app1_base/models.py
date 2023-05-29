from __future__ import unicode_literals

import os
import pytz
import secrets

from django.db import models
from django.conf import settings
# from django.dispatch import receiver
from django.contrib.auth.models import User
# from django.db.models.signals import post_save
# from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator, EmailValidator, URLValidator, MinValueValidator, MaxValueValidator
from django.db import connection

# from random import randint
from datetime import datetime, timedelta

DAY_CHOICES = (('*', _('Every days')),
               (1, _('Monday')),
               (2, _('Tuesday')),
               (3, _('Wednesday')),
               (4, _('Thursday')),
               (5, _('Friday')),
               (6, _('Saturday')),
               (0, _('Sunday')),
               )


def local_to_utc(h, m, tz, d=False):
    local = datetime.now(tz)
    local = local.replace(hour=h, minute=m)
    if d:
        local = local + timedelta(days=(d - local.weekday() + 7) % 7)
    utc = local.astimezone(pytz.utc)
    return utc.hour, utc.minute, utc.weekday()


def utc_to_local(h, m, tz, d):
    utc = datetime.now(pytz.utc)
    utc = utc.replace(hour=int(h), minute=int(m))
    if d != '*':
        utc = utc + timedelta(days=(int(d) - utc.weekday() + 7) % 7)
        local = utc.astimezone(tz)
        return str(local.minute), str(local.hour), dict(DAY_CHOICES)[local.weekday()]
    else:
        local = utc.astimezone(tz)
        return str(local.minute), str(local.hour), dict(DAY_CHOICES)[d]


TIME_ZONE_CHOICES = [(i, i) for i in pytz.common_timezones if 'Asia/Ban' in i or 'Europe' in i]


class CustomUser(User):
    class Meta:
        ordering = ["last_name"]
        verbose_name = _("User")
        # verbose_name_plural = _("Families")
        proxy = True

    def __str__(self):
        return self.first_name + ' ' + self.last_name


DOCKER_VERSION = ((1.0, 1.0),
                  (1.1, 1.1),
                  (1.13, 1.13),
                  (1.2, 1.2),
                  (1.3, 1.3),
                  (1.4, 1.4),
                  (1.5, 1.5),
                  (1.6, 1.6),
                  (2.0, 2.0),
                  (2.1, 2.1),
                  (2.2, 2.2),
                  (2.3, 2.3),
                  (2.4, 2.4),
                  )


def get_default_tunnel_port():
    # to make migration uncomment
    # return None
    port_query = MachineID.objects.all().order_by('tunnel_port').values('tunnel_port')
    if port_query.count() == 0:
        return 40000
    list_port = [p['tunnel_port'] for p in port_query]
    if not any(list_port):
        return 40000
    port_start = list_port[0]
    for p in range(port_start, port_start + 1000):
        if p not in list_port:
            return p


class MachineID(models.Model):
    uuid = models.CharField(max_length=200, unique=True)
    date = models.DateTimeField(auto_now=True)
    future_user = models.CharField(max_length=200, null=True, blank=True)
    timestamp = models.DateTimeField(default=datetime(year=2000, month=1, day=1,
                                                      tzinfo=pytz.timezone(settings.TIME_ZONE)))
    tunnel_port = models.IntegerField(unique=True, null=True, blank=True,
                                      default=get_default_tunnel_port,
                                      validators=[MaxValueValidator(40999), MinValueValidator(40000)])
    reboot = models.BooleanField(default=False)
    docker_version = models.FloatField(choices=DOCKER_VERSION, default=2.0)
    change = models.BooleanField(default=False)
    multi_client = models.BooleanField(default=False,
                                       help_text=_("Check if the nnvission neural network server can accept more"
                                                   " than one client. So you can change the association between client"
                                                   "and machine_ID in the admin"))

    def __str__(self):
        return f'{self.uuid} - {self.date}'

    class Meta:
        verbose_name_plural = _('Security Box')


class Sector(models.Model):
    name = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.name


class SubSector(models.Model):
    name = models.CharField(max_length=200, blank=True)
    number = models.IntegerField(blank=True, null=True)
    sector = models.ForeignKey(Sector, blank=True, null=True, on_delete=models.CASCADE)
    is_UP = models.BooleanField(default=False)

    def __str__(self):
        return '{} - {}'.format(self.number, self.name)

    class Meta:
        ordering = ('number',)
        verbose_name = _('Sub sector')


CLIENT_TYPE_CHOICES = (('jo', _('serenicia')),
                       ('se', _('security')),
                       )

CLIENT_SHOWER = (('no', _('Standard')),
                 ('fi', _('Filter')),
                 )

CLIENT_HELPER = (('no', _('No')),
                 ('il', _('Integralift')),
                 ('cr', _('Ceiling Rail')),
                 )

BED_CHOICES = ( ('stand', _('Standard')),
                ('alzhei', _('Alzheimer')),
                ('xxl', _('XXL'))
                )


class Client(models.Model):
    adress_lieu = models.CharField(max_length=200, blank=True)
    adress = models.CharField(max_length=200, blank=True)
    cp = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=200, blank=True)
    key = models.CharField(max_length=200, default=secrets.token_hex)
    folder = models.CharField(max_length=200, default=secrets.token_urlsafe)
    rec = models.BooleanField(default=False)
    start_rec = models.DateTimeField(default=datetime(year=2500, month=1, day=1, tzinfo=pytz.UTC))
    change = models.BooleanField(default=False)
    update_camera = models.BooleanField(default=False)
    wait_before_detection = models.IntegerField(default=20)
    wait_before_cancel_alert = models.DurationField(default=timedelta(seconds=600))
    dataset_test = models.BooleanField(default=False)
    space_allowed = models.IntegerField(default=1000)  # en Mo
    image_panel_max_width = models.IntegerField(default=400)
    image_panel_max_hight = models.IntegerField(default=400)
    logo_perso = models.CharField(max_length=20, null=True, blank=True)
    stop_thread = models.CharField(max_length=200, default=secrets.token_hex)
    video_authorize = models.BooleanField(default=True)
    token_video = models.CharField(max_length=200, default=secrets.token_urlsafe)
    token_video_time = models.DateTimeField(default=datetime(year=2000, month=1, day=1))
    time_zone = models.CharField(max_length=30, choices=TIME_ZONE_CHOICES, default='Europe/Paris')
    actif = models.BooleanField(default=False)
    # ping = models.BooleanField(default=False)
    external_key = models.CharField(max_length=200, default='no external')
    room_number = models.IntegerField(blank=True, default=False, null=True)
    sector = models.ForeignKey(SubSector, on_delete=models.CASCADE, null=True, blank=True)
    type = models.CharField(max_length=2, choices=CLIENT_TYPE_CHOICES, default='jo')
    informations = models.TextField(null=True, blank=True)
    shower = models.CharField(max_length=30, choices=CLIENT_SHOWER, default='no')
    helper = models.CharField(max_length=30, choices=CLIENT_HELPER, default='no')
    bed = models.CharField(max_length=20, choices=BED_CHOICES, default='stand')
    price = models.CharField(max_length=10, verbose_name=_('Price'), default='0')
    captch = models.BooleanField(default=False, help_text=_("Check if the room sensor is installed"))
    captsdb = models.BooleanField(default=False, help_text=_("Check if the bathroom sensor is installed"))
    alexa_device_id = models.CharField(max_length=250, default='not set up')
    machine_id = models.ForeignKey(MachineID, null=True, blank=True, on_delete=models.SET_NULL)
    scan_camera = models.IntegerField(default=0,
                                      help_text=_("0 if you want a broadcast discovery of onvif camera,"
                                                  " port number between 0 and 65000 if you want a full scan"
                                                  " of area network"))  # port number
    scan = models.BooleanField(default=False,
                               help_text=_("Check if you want a periodic scan of the network to find the camera"))
    automatic_launch_from_scan = models.BooleanField(default=True,
                                                     help_text=_("Uncheck when client is only to scan and retrieve"
                                                                 " the URI"))
    # to suppr after migration MachineID and all client on or obove 2.1 --------------
    #tunnel_port = models.IntegerField(unique=True, null=True, blank=True,
    #                                  default=get_default_tunnel_port,
    #                                  validators=[MaxValueValidator(40999), MinValueValidator(40000)])
    #reboot = models.BooleanField(default=False)

    #docker_version = models.FloatField(choices=DOCKER_VERSION, default=1.2)
    #timestamp = models.DateTimeField(default=datetime(year=2000, month=1, day=1))

    def __str__(self):
        return '{} {} -  {} -  {} ({})'.format(self.adress_lieu, self.adress, self.cp, self.city, self.room_number)

    class Meta:
        ordering = ('cp',)
        verbose_name = _('Residence')


# @receiver(post_save, sender=Client)
# def create_related(sender, instance, created, **kwargs):
#     if created:
#         if not hasattr(instance, 'CLientRec'):
#             ClientRec.objects.create(client=instance)
#         if not hasattr(instance, 'CLientChange'):
#             CLientChange.objects.create(client=instance)
#
#
# class ClientRec(models.Model):
#     client = models.OneToOneField(Client, on_delete=models.CASCADE)
#     rec = models.BooleanField(default=False)
#
#
# class CLientChange(models.Model):
#     client = models.OneToOneField(Client, on_delete=models.CASCADE)
#     change = models.BooleanField(default=False)


LANGUAGE_CHOICES = (('en', _('English')),
                    ('fr', _('French')),
                    )


def get_token_telegram():
    return secrets.token_urlsafe(6)


def path_and_rename_profile(instance, filename):
    upload_to = 'users_photo/'  # chemin dossier photo
    extension = filename.split('.')[-1]  # isole l'extension du fichier à enregistrer
    filename = '{}.{}'.format(secrets.token_urlsafe(),
                              extension)  # reformate nom du fichier en token random + ajout extension
    return os.path.join(upload_to, filename)  # renvoi chemin + nom de fichier aléatoire


class Profile(models.Model):
    CIVILITY_CHOICES = (
        ('Mr', _('Mr')),
        ('Mrs', _('Mrs')),
        # ('', _('')),
    )
    adress_latitude = models.CharField(max_length=50, blank=True)
    adress_longitude = models.CharField(max_length=50, blank=True)
    client = models.ForeignKey(Client, null=True, blank=True, on_delete=models.CASCADE)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    photo = models.ImageField(upload_to=path_and_rename_profile, null=True, blank=True, verbose_name=_('Photo'))
    phone_regex = RegexValidator(regex=r'^[\+\d]\d{9,11}$',
                                 message=_("Phone number must be entered in the format: \
                                           '+999999999'. Up to 15 digits allowed."))
    phone_number = models.CharField(validators=[phone_regex], max_length=17, blank=True, null=True,
                                    verbose_name=_('Phone number'))
    civility = models.CharField(max_length=20, choices=CIVILITY_CHOICES, blank=True, null=True, default=" ",
                                verbose_name=_('Civility'))
    telegram_token = models.CharField(max_length=64, default=get_token_telegram)
    subscribe_emails = models.BooleanField(default="True")
    alert = models.BooleanField(default="True")
    language = models.CharField(max_length=2, choices=LANGUAGE_CHOICES, default='fr')

    adress = models.CharField(max_length=200, blank=True, null=True, verbose_name=_('Adress'))
    cp = models.CharField(max_length=200, blank=True, null=True, verbose_name=_('postcode'))  # -> should be integer
    city = models.CharField(max_length=200, blank=True, null=True, verbose_name=_('City'))
    department_number = models.CharField(max_length=2, blank=True, null=True, verbose_name=_('Department number'))

    phonetic_firstname = models.CharField(max_length=50, blank=True, null=True)
    phonetic_lastname = models.CharField(max_length=50, blank=True, null=True)
    video_ready = models.BooleanField(default=False)
    welcoming_sent = models.BooleanField(default=False)
    display_adress = models.BooleanField(default=True)
    comments = models.TextField(blank=True, null=True)
    mailer_daemon = models.BooleanField(default=False)
    advanced_user = models.BooleanField(default=False)
    portal_token = models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        ordering = ['user']
        # verbose_name = 'user'
        # verbose_name_plural = 'users'
        # permissions = [('camera', '>>> Can view camera'), ('dataset', '>>> Can make dataset')]

    email_0 = models.CharField(validators=[EmailValidator], max_length=30, blank=True)
    email_1 = models.CharField(validators=[EmailValidator], max_length=30, blank=True)
    email_2 = models.CharField(validators=[EmailValidator], max_length=30, blank=True)
    email_3 = models.CharField(validators=[EmailValidator], max_length=30, blank=True)
    email_4 = models.CharField(validators=[EmailValidator], max_length=30, blank=True)
    email_5 = models.CharField(validators=[EmailValidator], max_length=30, blank=True)
    email_6 = models.CharField(validators=[EmailValidator], max_length=30, blank=True)
    email_7 = models.CharField(validators=[EmailValidator], max_length=30, blank=True)
    email_8 = models.CharField(validators=[EmailValidator], max_length=30, blank=True)
    email_9 = models.CharField(validators=[EmailValidator], max_length=30, blank=True)

    phone_number_0 = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    phone_number_1 = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    phone_number_2 = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    phone_number_3 = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    phone_number_4 = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    phone_number_5 = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    phone_number_6 = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    phone_number_7 = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    phone_number_8 = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    phone_number_9 = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    tracking_number = models.CharField(max_length=30, default='', blank=True)
    tracking_site = models.URLField(blank=True, default='')
    created_by = models.CharField(max_length=30, default='admin')

    def get_photo_url(self):
        try:
            url = self.photo.url
        except ValueError:
            url = settings.STATIC_URL + 'app1_base/img/bi/person-circle.svg'
        return url

    def __str__(self):
        return 'user : {} - phone_number : {} - alert : {}'.format(self.user, self.phone_number, self.alert)


class Preferences(models.Model):
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE, blank=True, null=True)
    notif_all_new_msg = models.BooleanField(default=True, verbose_name=_('Receive incoming message notification'))


class Telegram(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)  # BUG onetoonelink
    chat_id = models.BigIntegerField(null=True)  # to suppress only for the change to char and not lost the connection.
    chat_id_char = models.CharField(max_length=64, null=True, default=None)
    name = models.CharField(max_length=64, default='unknow')


class Camera(models.Model):
    AUTH_CHOICES = (
        ('B', 'Basic'),
        ('D', 'Digest'))
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    name = models.CharField(max_length=20, default='unknow')
    brand = models.CharField(max_length=20, default='unknow')
    model = models.CharField(max_length=100, default='unknow')
    serial_number = models.CharField(max_length=200, null=True, blank=True, default=None)
    active = models.BooleanField(default=True)
    active_automatic = models.BooleanField(default=True)
    ip = models.GenericIPAddressField(null=True)
    port_onvif = models.IntegerField(default=80)
    auth_type = models.CharField(max_length=1, choices=AUTH_CHOICES, default='B')
    username = models.CharField(max_length=20, blank=True)
    password = models.CharField(max_length=20, blank=True)
    stream = models.BooleanField(default=False, help_text=_('Check this box if you want to use the rtsp of the camera'))
    threshold = models.FloatField(validators=[MinValueValidator(0.20), MaxValueValidator(0.99)], default=0.9)
    gap = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(99)], default=95)
    max_width_rtime = models.IntegerField(default=320)
    max_width_rtime_HD = models.IntegerField(default=1280)
    reso = models.BooleanField(default=False)
    width = models.IntegerField(default=1280)
    height = models.IntegerField(default=720)
    image_rotation = models.IntegerField(default=0)
    pos_sensivity = models.IntegerField(default=30)
    wait_for_set = models.BooleanField(default=True)
    from_client = models.BooleanField(default=False, help_text=_('Define if the camera has been detected or not'))
    on_camera_LD = models.BooleanField(default=False)
    on_camera_HD = models.BooleanField(default=False)
    on_rec = models.BooleanField(default=False)
    max_object_area_detection = models.IntegerField(default=100)
    update = models.BooleanField(default=True)
    change = models.BooleanField(default=False)

    class Meta:
        unique_together = (('client', 'ip'),
                           ('client', 'serial_number'),)

    def __str__(self):
        return '{} - {} ( {} )'.format(self.client.cp, self.name, self.ip)


class CameraUri(models.Model):
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE)
    use = models.BooleanField(default=False)
    index_uri = models.IntegerField(default=0)
    http = models.URLField(blank=True, default='http://0.0.0.0')
    rtsp = models.CharField(validators=[URLValidator(schemes=('rtsp',)), ], max_length=200, blank=True,
                            default='rtsp://0.0.0.0')

    class Meta:
        unique_together = ('camera', 'index_uri')

    # def clean(self):
    #     if self.use:
    #         used = CameraUri.objects.filter(use=True, camera=self.camera)
    #         if self.pk:
    #             used = used.exclude(pk=self.pk)
    #         if used.exists():
    #             raise ValidationError("An active URI already exists for this camera")

    def secure_rtsp(self):
        return self.rtsp

    def secure_url(self):
        return self.http.split('?')[0]


# Informations about the detection of the cameras
class Result(models.Model):
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE)
    # file = models.FilePathField(
    # path='/NNvivison/media_root/images', recursive=True, allow_folders=True, default='detect' )
    file = models.CharField(max_length=100, default='detect')
    video = models.CharField(max_length=100, default='None')
    video_time = models.DateTimeField(default=datetime(year=2000, month=1, day=1))
    time = models.DateTimeField(auto_now=True)
    brut = models.TextField(default='')
    alert = models.BooleanField(default=False)
    correction = models.BooleanField(default=False)
    force_send = models.BooleanField(default=False)
    face_check = models.BooleanField(default=False)
    users = models.ManyToManyField(User, blank=True)

    def __str__(self):
        return 'Camera : {} - at {}'.format(self.camera.name, self.time.astimezone(pytz.timezone('Europe/Paris')))


class Object(models.Model):
    result = models.ForeignKey(Result, on_delete=models.CASCADE)
    result_object = models.CharField(max_length=20, default='')
    result_prob = models.DecimalField(default=0, max_digits=3, decimal_places=2)
    result_loc1 = models.DecimalField(default=0, max_digits=6, decimal_places=2)
    result_loc2 = models.DecimalField(default=0, max_digits=6, decimal_places=2)
    result_loc3 = models.DecimalField(default=0, max_digits=6, decimal_places=2)
    result_loc4 = models.DecimalField(default=0, max_digits=6, decimal_places=2)
    result_option1 = models.CharField(max_length=20, default='normal')

    def __str__(self):
        return 'Object : {} with p={}'.format(self.result_object, self.result_prob)


STUFFS_CHOICES = ((1, _('person')),
                  (2, _('bicycle')),
                  (3, _('car')),
                  (4, _('motorbike')),
                  (5, _('cat')),
                  (6, _('dog')),
                  (7, _('aeroplane')),
                  (8, _('bus')),
                  (9, _('train')),
                  (10, _('truck')),
                  (11, _('boat')),
                  (12, _('bird')),
                  (13, _('backpack')),
                  (14, _('umbrella')),
                  (15, _('chair')),
                  (16, _('sofa')),
                  (17, _('tvmonitor')),
                  (18, _('laptop')),
                  (19, _('mouse')),
                  (20, _('keyboard')),
                  (21, _('book')),
                  (22, _('clock')),
                  (23, _('face')),
                  (24, _('vehicle')),
                  (25, _('falling')),
                  (26, _('masque')),
                  (27, _('incorrect_mask')),
                  (28, _('no_mask')),
                  (29, _('toothbrush')))

ACTIONS_CHOICES = ((1, _('appear')),
                   (2, _('disappear')),
                   (3, _('present'))
                   )

DISAPPEAR = {'car': 4,
             }

STUFFS_CHOICES_CHAR = [(reference, _(reference)) for reference in settings.CLASS]

ACTIONS_CHOICES_CHAR = (('appear', _('appear')),
                        ('disappear', _('disappear')),
                        ('present', _('present'))
                        )


class AlertStuffsChoice(models.Model):
    client = models.ManyToManyField(Client)
    stuffs = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return f'{_(self.stuffs)}'


class Alert(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    stuffs_char_foreign = models.ForeignKey(AlertStuffsChoice, on_delete=models.CASCADE, null=True, blank=True)
    actions_char = models.CharField(max_length=100, choices=ACTIONS_CHOICES_CHAR, default='present')
    stuffs = models.IntegerField(choices=STUFFS_CHOICES, default=1)
    actions = models.IntegerField(choices=ACTIONS_CHOICES, default=1)
    mail = models.BooleanField(default=True)  # should be a foreign key to Alert_type
    sms = models.BooleanField(default=False)
    telegram = models.BooleanField(default=False)
    call = models.BooleanField(default=False)
    alarm = models.BooleanField(default=False)
    mass_alarm = models.BooleanField(default=False)
    active = models.BooleanField(default=False)
    when = models.DateTimeField(default=datetime(year=2000, month=1, day=1, tzinfo=pytz.timezone(settings.TIME_ZONE)))
    last = models.DateTimeField(default=datetime(year=2000, month=1, day=1, tzinfo=pytz.timezone(settings.TIME_ZONE)))
    key = models.CharField(max_length=10, default='', blank=True)
    img_name = models.CharField(max_length=100, default='', blank=True)
    camera = models.ManyToManyField(Camera, blank=True)

    class Meta:
        unique_together = ('client', 'stuffs_char_foreign', 'actions_char')

    def __str__(self):
        return f'action : {self.actions_char} / object : {self.stuffs_char_foreign}'


ALERT_CHOICES = (('mail', 'mail'),
                 ('sms', 'sms'),
                 ('telegram', 'telegram'),
                 ('mass_alarm', 'mass_alarm'),
                 ('call', 'call'),
                 ('alarm', 'alarm'),
                 ('adam', 'adam'),
                 ('patrol', 'patrol')
                 )


class AlertByProfile(object):
    """
    model to setup the possibility to alert or not the user related to the residence
    fill by default for all the canal when saving ProfileSecurity many to many on Client
    """
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    kind = models.CharField(max_length=10, choices=ALERT_CHOICES)


class Alert_when(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    what = models.CharField(max_length=10, choices=ALERT_CHOICES)
    action = models.IntegerField(default=1)
    stuffs = models.IntegerField(default=1)
    when = models.DateTimeField(auto_now=True)
    who = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return '{} at {} to {}'.format(self.what, self.when.astimezone(pytz.timezone('Europe/Paris')), self.who)


class Alert_type(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    allowed = models.CharField(max_length=10, choices=ALERT_CHOICES)
    priority = models.IntegerField(default=1)
    delay = models.DurationField(default=timedelta(seconds=0))
    resent = models.DurationField(default=timedelta(seconds=300))
    post_wait = models.DurationField(default=timedelta(seconds=60))

    class Meta:
        unique_together = ('client', 'allowed')

    def __str__(self):
        return 'client : {} / allowed : {} '.format(self.client, self.allowed)


class UpdateId(models.Model):
    id_number = models.IntegerField(default=0)
    already_call = models.BooleanField(default=False)


class ProfileSecurity(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    client = models.ManyToManyField(Client, blank=True,
                                    help_text=_('Select the residence you want to access the interface <br>'))

    def __str__(self):
        return 'user : {}'.format(self.user)


class ProfileAlert(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    client = models.ManyToManyField(Client, blank=True,
                                    help_text=_('Select the residence you want to have the warnings <br>'))

    def __str__(self):
        return f'user : {self.user}'


class Action(models.Model):
    user = models.ForeignKey(Client, on_delete=models.CASCADE)
    time = models.DateTimeField(auto_now=True)
    action = models.CharField(max_length=10, default='')


class CameraSetup(models.Model):
    class Meta:
        verbose_name = _("Camera Setup")

    # Liste de choix d'état de la camera
    STATE_CHOICE = [
        ('working', _('working')),
        ('in_progress_installing', _('in progress installing')),
        ('to_install', _('to install')),
        ('in_default', _('in default')),
        ('not_equipped', _('not equipped')),
    ]
    # # Liste de choix de qualité video de la camera
    VIDEO_QUALITY_CHOICE = [
        ('380p', '380p'),
        ('480p', '480p'),
        ('720p', '720p'),
        ('1080p', '1080p'),
        ('unknown', _('unknown')),
    ]

    location = models.CharField(max_length=256, blank=False, verbose_name=_('Location'))
    room = models.CharField(max_length=150, blank=False, verbose_name=_('Room'))
    ip_identification = models.GenericIPAddressField(protocol='IPv4', blank=False,
                                                     verbose_name=f"IP {_('Identification')}")
    mac_identification = models.CharField(max_length=17, blank=False, verbose_name=_('Mac Identification'))
    state = models.CharField(max_length=30, choices=STATE_CHOICE, default='working', verbose_name=_('State'))
    video_quality = models.CharField(max_length=10, choices=VIDEO_QUALITY_CHOICE, default='380p',
                                     verbose_name=_('Video Quality'))

    def __str__(self):
        return f' {self.location} - {self.room} - {self.ip_identification} - {self.state}'


TIMELINE_EVENT_CHOICES = (('car', _('Car')),
                          ('person', _('Person')),
                          ('cat', _('Cat')),
                          ('dog', _('Dog')))


class TimelineConfiguration(models.Model):
    event = models.CharField(max_length=10, choices=TIMELINE_EVENT_CHOICES)
    inactivity_time = models.PositiveIntegerField(default=2)
