from random import randint

from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.db import models
import os
from django.db.models import Q

from .validators import validate_image, validate_file_extension
from app1_base.log import Logger
from app1_base.models import Client, Profile, CustomUser
from django.utils.translation import gettext_lazy as _
import secrets
from django.utils.deconstruct import deconstructible
from datetime import datetime, timedelta, date
from django.utils import timezone
import logging

from multiselectfield import MultiSelectField


if 'log_model' not in globals():
    global log_model
    log_model = Logger('model', level=logging.ERROR, file=False).run()


# This is the list of opening hours for France, should be adapted for other countries
def get_time_choices():
    log_model.debug(f"defautl time zone  :{timezone.get_default_timezone()}  ")
    log_model.debug(f"current time zone  :{timezone.get_current_timezone()}  ")
    now = timezone.localtime()
    log_model.debug(f"now tz  :{now.tzinfo}  ")
    list_hour = [now.replace(hour=7, minute=0, second=0, microsecond=0)]
    log_model.debug(f"list tz  :{list_hour[0].tzinfo}  ")
    for i in range(29):
        list_hour.append(list_hour[-1] + timedelta(minutes=30))
    return list_hour


def get_token():
    return secrets.token_hex(16)


def date_now():
    return datetime.now(timezone.utc).date()


def date_payroll():
    return date.today() - timedelta(days=30)


def random_token2():
    return randint(1000, 9999)


class TypeRoutine(models.Model):
    TIME_CHOICES_TUPLES = [(idx, i.strftime("%H:%M")) for idx, i in enumerate(get_time_choices())]
    name = models.CharField(max_length=20, default='family')
    start = models.IntegerField(default=0, choices=TIME_CHOICES_TUPLES)
    end = models.IntegerField(default=2, choices=TIME_CHOICES_TUPLES)

    def __str__(self):
        return '{} : {} -> {}'.format(self.name, self.TIME_CHOICES_TUPLES[self.start][1],
                                      self.TIME_CHOICES_TUPLES[self.end][1])


class WeekRoutine(models.Model):
    DAY_CHOICES = (
        (10, _('Every days')),
        (0, _('Monday')),
        (1, _('Tuesday')),
        (2, _('Wednesday')),
        (3, _('Thursday')),
        (4, _('Friday')),
        (5, _('Saturday')),
        (6, _('Sunday'))
    )
    # user_resident = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    routine = models.ForeignKey(TypeRoutine, on_delete=models.CASCADE, null=True)
    day = models.IntegerField(choices=DAY_CHOICES)
    service_type = models.CharField(max_length=50, default="service standard")

    class Meta:
        unique_together = (('routine', 'day', 'service_type'),)

    def __str__(self):
        return '{} {}'.format(self.routine, dict(self.DAY_CHOICES)[self.day])


class PresentationType(models.Model):
    DEFAULT_CHOICES = ((None, _('No')),
                       (True, _('Yes')))
    type = models.CharField(max_length=100, verbose_name=_('Presentation'), unique=True)
    default = models.BooleanField(default=None, null=True, blank=True, unique=True, choices=DEFAULT_CHOICES,
                                  verbose_name=_('Default'), help_text=_('Presentation of the meal before processing'))

    class Meta:
        verbose_name = _('Presentation type')

    def __str__(self):
        return f'{self.type}'


def path_and_rename_profile(instance, filename):
    upload_to = 'users_photo/'  # chemin dossier photo
    extension = filename.split('.')[-1]  # isole l'extension du fichier à enregistrer
    filename = '{}.{}'.format(secrets.token_urlsafe(),
                              extension)  # reformate nom du fichier en token random + ajout extension
    return os.path.join(upload_to, filename)  # renvoi chemin + nom de fichier aléatoire


def upload_passphrase(instance, filename):
    upload_to = 'audio_record/' + instance.folder + '/'
    return os.path.join(upload_to, filename)


class ProfileSerenicia(models.Model):
    # def now(): # only not to break migration should be deleted
    #     return datetime.now()
    # def random_token(): # only not to break migration should be deleted
    #     pass
    HOMEPAGE_CHOICES = (
        ('family', _('family')),
        ('cuisine', _('cuisine'))
    )
    STATUS_CHOICES = (
        ('home', _('Present')),
        ('hospitalized', _('Hospitalized')),
        ('vacation', _('Vacation')),
        ('deceased', _('Deceased'))
    )

    FAMILY_LINK_CHOICES = (
        ('', '-------------------'),
        (_('Child'), (
            (_('Son'), _('Son')),
            (_('Daughter'), _('Daughter')),
        )
         ),
        (_('Grandchildren'), (
            (_('Grandson'), _('Grandson')),
            (_('Granddaughter'), _('Granddaughter')),
        )
         ),
        (_('Other'), (
            (_('Brother'), _('Brother')),
            (_('Sister'), _('Sister')),
            (_('Cousin'), _('Cousin')),
            (_('Uncle'), _('Uncle')),
            (_('Aunt'), _('Aunt')),
            (_('Niece'), _('Niece')),
            (_('Nephew'), _('Nephew')),
        )
         ),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    user_list = models.ManyToManyField(Profile, through='UserListIntermediate', blank=True)
    family_bond = models.CharField(
        max_length=14, choices=FAMILY_LINK_CHOICES, blank=True, null=True, verbose_name=_('Family bond')
    )
    # Si problèmes de migration à cause du through, supprimer user_list, makemigrations/migrate, puis rajoutez-le.
    folder = models.CharField(max_length=200, default=secrets.token_urlsafe, blank=True)
    homepage = models.CharField(max_length=20, choices=HOMEPAGE_CHOICES, default='family')
    status = models.CharField(max_length=200, choices=STATUS_CHOICES, default='home', verbose_name=_('Status'))
    external_key = models.IntegerField(blank=True, null=True, default=False)
    birth_city = models.CharField(max_length=200, blank=True, null=True, verbose_name=_('Birth city'))
    birth_date = models.DateField(null=True, blank=True, verbose_name=_('Birth date'))
    entry_date = models.DateField(null=True, blank=True, default=date_now, verbose_name=_('Entry date'))
    cal_id = models.EmailField(blank=True, null=True, default=False)
    titan_key = models.CharField(max_length=200, blank=True, null=True)
    pics_total = models.IntegerField(blank=True, null=True, default=False)
    pics_last = models.IntegerField(blank=True, null=True, default=False)
    token_video_call = models.IntegerField(blank=True, null=True, default=random_token2)
    uri_netsoins = models.CharField(max_length=200, blank=True, null=True)
    # service account for google calendar ------------------------------------------------------------------------------
    service_account_file = models.JSONField(default=dict)
    gcp_project = models.CharField(max_length=50, null=True, blank=True, default='undefined')
    has_active_service_account = models.BooleanField(default=False)
    active_since = models.DateField(null=True, blank=True)
    sa_email = models.EmailField(null=True, blank=True)
    has_active_subcalendar = models.BooleanField(default=False)
    user_waiting = models.ManyToManyField(User, blank=True, related_name='wait_for_help')
    bacterium = models.BooleanField(default=False)
    date_status_deceased = models.DateField(null=True, blank=True, default=None)
    UP_volunteer = models.BooleanField(default=False)
    passphrase = models.FileField(upload_to=upload_passphrase, null=True, blank=True)
    word_played = models.PositiveIntegerField(default=0)
    total_score = models.PositiveIntegerField(default=0)
    meal_type = models.ForeignKey(PresentationType, on_delete=models.SET_NULL, blank=True, null=True)

    def __str__(self):
        return '{} {}'.format(self.user.last_name, self.user.first_name)


class UserListIntermediate(models.Model):
    profileserenicia = models.ForeignKey(ProfileSerenicia, on_delete=models.PROTECT)
    profile = models.ForeignKey(Profile, on_delete=models.PROTECT)
    was_manual = models.BooleanField(default=False)


class PreferencesSerenicia(models.Model):
    INTERVENTIONS_CHOICES = ((0, _('No display')),
                             (1, _('Photo of contributor and time only')),
                             (2, _('Titled only')),
                             (3, _('Full display')))
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE, blank=True, null=True)
    notif_family_new_picture = models.BooleanField(default=True, verbose_name=_('Receive new photo notification'))
    notif_doctor_demand_date = models.BooleanField(default=True,
                                                   verbose_name=_('Receive doctor visit request notification'))
    sensitive_photos = models.BooleanField(default=True, verbose_name=_('See sensitive photos in the gallery'))
    interventions = models.IntegerField(choices=INTERVENTIONS_CHOICES, default=3,
                                        verbose_name=_('Display of interventions'))


class ProfileEhpad(models.Model):
    PLACEMENT_CHOICES = (
        ('ehpad', _('EHPAD')),
        ('ehpadpu', _('EHPAD Protected Unit')),
        ('ehpadstudypu', _('EHPAD Study the protected unit')),
        ('senior_residence ', _('Senior residence')),
    )
    SITUATION_CHOICES = (
        ('Marital life', (
            ('single', _('Single')),
            ('married', _('Married')),
            ('divorced', _('Divorced')),
            ('widower', _('Widower')),
        )),
    )
    RELIGION_CHOICES = (
        ('without', _('Without / Do not wish to communicate this information')),
        ('christians', _('Christians')),
        ('muslims', _('Muslims')),
        ('hindus', _('Hindus')),
        ('jews', _('Jews')),
        ('buddhists', _('Buddhists')),
        ('other', _('Other')),
    )

    resident = models.OneToOneField(User, on_delete=models.CASCADE)

    # PLACEMENT --------------------------------------------------------------------------------------------------------
    wanted_placement = models.CharField(
        max_length=20, choices=PLACEMENT_CHOICES, default='EHPAD', verbose_name=_('Placement choice for resident')
    )
    wanted_entry_date = models.DateField(
        null=True, blank=True, verbose_name=_('Date for entry wanted')
    )
    # RESIDENT INFO FAMILY & MARITAL LIFE ------------------------------------------------------------------------------
    marital_status = models.CharField(
        max_length=8, choices=SITUATION_CHOICES, default='single', verbose_name=_('Marital status')
    )
    religion = models.CharField(
        max_length=20, choices=RELIGION_CHOICES, default='unaffiliated', verbose_name=_('Religion')
    )
    previous_profession = models.CharField(
        max_length=200, null=True, blank=True, verbose_name=_('Previous profession of resident')
    )

    def __str__(self):
        return '{}'.format(self.resident)


class MedicalFile(models.Model):
    resident = models.OneToOneField(User, on_delete=models.CASCADE)


# class PensionFund(models.Model):
#     profile_ehpad = models.ForeignKey(ProfileEhpad, on_delete=models.CASCADE)  # CASCADE OR PROTECT?
#     phone_regex = RegexValidator(regex=r'^[\+\d]\d{9,11}$',
#                                  message=_("Phone number must be entered in the format: \
#                                                    '+999999999'. Up to 15 digits allowed."))
#     adress = models.CharField(max_length=200, blank=True, null=True)
#     cp = models.CharField(max_length=200, blank=True, null=True)
#     city = models.CharField(max_length=200, blank=True, null=True)
#     phone = models.CharField(validators=[phone_regex], max_length=17, blank=True)
#     affiliation_number = models.CharField(max_length=200, blank=True, null=True)
#     monthly_amount = models.CharField(max_length=200, blank=True, null=True)


class Entree(models.Model):
    name = models.CharField(max_length=200)
    active = models.BooleanField(default=True)
    price_cents = models.PositiveIntegerField(default=0)

    def __getitem__(self, item):
        if item == 'price_cents':
            return '{:,.2f}€'.format(self.price_cents / 100)
        else:
            return super(Entree, self).__getitem__()

    def __str__(self):
        return '{}'.format(self.name)


class MainDish(models.Model):
    name = models.CharField(max_length=200, blank=True, null=True)
    active = models.BooleanField(default=True)
    price_cents = models.PositiveIntegerField(default=0)

    def __getitem__(self, item):
        if item == 'price_cents':
            return '{:,.2f}€'.format(self.price_cents / 100)
        else:
            return super(MainDish, self).__getitem__()

    def __str__(self):
        return '{}'.format(self.name)


class Dessert(models.Model):
    name = models.CharField(max_length=200, blank=True, null=True)
    active = models.BooleanField(default=True)
    price_cents = models.PositiveIntegerField(default=0)

    def __getitem__(self, item):
        if item == 'price_cents':
            return '{:,.2f}€'.format(self.price_cents / 100)
        else:
            return super(Dessert, self).__getitem__()

    def __str__(self):
        return '{}'.format(self.name)


class Accompaniment(models.Model):
    name = models.CharField(max_length=200, blank=True, null=True)
    active = models.BooleanField(default=True)
    price_cents = models.PositiveIntegerField(default=0)

    def __getitem__(self, item):
        if item == 'price_cents':
            return '{:,.2f}€'.format(self.price_cents / 100)
        else:
            return super(Accompaniment, self).__getitem__()

    def __str__(self):
        return '{}'.format(self.name)


class Meal(models.Model):
    TYPE_CHOICES = (
        ('noon', _('noon')),
        ('evening', _('evening'))
    )
    date = models.DateField(null=True, default=datetime.today)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='noon')
    entree = models.ForeignKey(Entree, on_delete=models.CASCADE, null=True, blank=True, limit_choices_to=Q(active=True))
    main_dish = models.ForeignKey(MainDish, on_delete=models.CASCADE, null=True, blank=True,
                                  limit_choices_to=Q(active=True))
    accompaniment = models.ForeignKey(Accompaniment, on_delete=models.CASCADE, null=True, blank=True,
                                      limit_choices_to=Q(active=True))
    dessert = models.ForeignKey(Dessert, on_delete=models.CASCADE, null=True, blank=True)
    dry_cheese = models.BooleanField(default=True)
    cottage_cheese = models.BooleanField(default=True)
    comment = models.CharField(null=True, blank=True, max_length=1000)
    photo_service = models.ManyToManyField(User, blank=True)
    price_cents_to_date = models.PositiveIntegerField(default=0)
    substitution = models.BooleanField(default=False)

    class Meta:
        unique_together = ('date', 'type', 'substitution',),

    @property
    def get_price_to_date_display(self):
        return '{:,.2f}€'.format(self.price_cents_to_date / 100)

    @property
    def get_price_today_display(self):
        price = 0
        if self.entree:
            price = self.entree.price_cents
        if self.main_dish:
            price += self.main_dish.price_cents
        if self.accompaniment:
            price += self.accompaniment.price_cents
        if self.dessert:
            price += self.dessert.price_cents
        return '{:,.2f}€'.format(price / 100)

    def __str__(self):
        return '{} - {} - {}'.format(self.date, self.get_type_display(), self.main_dish)


class MealPresentation(models.Model):
    ITEM_CHOICES = (('entree', _('Entree')),
                    ('main_dish', _('Main dish')),
                    ('dessert', _('Dessert')))
    presentation = models.ForeignKey(PresentationType, on_delete=models.CASCADE)
    photo = models.ImageField(upload_to='cuisine/', null=True)
    meal = models.ForeignKey(Meal, on_delete=models.CASCADE)
    item = models.CharField(max_length=10, choices=ITEM_CHOICES)

    class Meta:
        unique_together = ('item', 'meal', 'presentation')


class MenuEvaluation(models.Model):
    NOTATION = ((1, '1'),
                (2, '2'),
                (3, '3'),
                (4, '4'))
    menu = models.ForeignKey(Meal, on_delete=models.CASCADE, null=True, blank=True)
    voter = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    entry = models.IntegerField(choices=NOTATION, null=True, blank=True)
    main_dish = models.IntegerField(choices=NOTATION, null=True, blank=True)
    dessert = models.IntegerField(choices=NOTATION, null=True, blank=True)
    service = models.IntegerField(choices=NOTATION, null=True, blank=True)

    class Meta:
        unique_together = (('menu', 'voter'),)

    def __str__(self):
        return '{} - {}'.format(self.menu, self.voter)


class EvalMenuSetting(models.Model):
    notation_switch = models.TimeField(default=datetime.strptime("16:00", "%H:%M"))

    # allow only one instance of this model
    def save(self, *args, **kwargs):
        self.id = 1
        return super().save(*args, **kwargs)

    def __str__(self):
        return 'Notation type switch : {} (UTC)'.format(self.notation_switch)


# class ResidentsPhoto(models.Model):
#     identified_residents = models.ForeignKey(Client, on_delete=models.CASCADE)
#     description = models.CharField(max_length=250, default="No Description")
#     horodate = models.DateTimeField(auto_now=True)
#     down_vote = models.ManyToManyField(User)
#     photo = models.ImageField()
#     resident_profile_picture = models.ImageField()
#
#     def __str__(self):
#         return 'picture of {} {} number : {}.'.format(Client.first_name, Client.name, self.id)


class Pic(models.Model):
    profil = models.ForeignKey(ProfileSerenicia, on_delete=models.CASCADE)
    file = models.ImageField()
    description = models.CharField(max_length=250, blank=True, null=True, default="No Description")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'photo'
        verbose_name_plural = 'photos'

    def __str__(self):
        return 'cropped profile picture ({}) of {} {}\'s resident.'.format(self.file,
                                                                           self.profil.profile.user.first_name,
                                                                           self.profil.profile.user.last_name)


# batch script to populate photo model


class MotDirection(models.Model):
    object = models.CharField(max_length=100, default='vide')
    image = models.ImageField(blank=True, null=True)
    text = models.TextField(blank=True, null=True)


class MotPoleSoins(models.Model):
    object = models.CharField(max_length=100, default='vide')
    image = models.ImageField(blank=True, null=True)
    text = models.TextField(blank=True, null=True)


class MotHotelResto(models.Model):
    object = models.CharField(max_length=100, default='vide')
    image = models.ImageField(blank=True, null=True)
    text = models.TextField(blank=True, null=True)


class MotCVS(models.Model):
    object = models.CharField(max_length=100, default='vide')
    image = models.ImageField(blank=True, null=True)
    text = models.TextField(blank=True, null=True)


class BlogImage(models.Model):
    image = models.CharField(max_length=250)
    image_blog = models.CharField(max_length=250, null=True)


class BlogPost(models.Model):
    CATEGORIES = [
        ('direction', _('Direction')), # Direction
        ('social_life', _('Social life')), # Vie sociale
        ('care', _('Care')), # Soins
        ('hospitality', _('Hotel')), # Hotellerie
        ('News', _('News')), # Actualité
    ]
    title = models.CharField(max_length=120, verbose_name=_('Title'))
    content = models.TextField(blank=True, verbose_name=_('Content'))
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Author'))
    created_on = models.DateField(null=True, blank=True, verbose_name=_('Created the'))
    images = models.ManyToManyField(BlogImage, blank=True)
    cover = models.ForeignKey(BlogImage, on_delete=models.SET_NULL, null=True, related_name='cover_image')
    files = models.FileField(upload_to='blog_doc/', null=True, blank=True)
    category = models.CharField(max_length=150, choices=CATEGORIES, default='activities', null=True, blank=True,
                                verbose_name=_("Category"))
    is_public = models.BooleanField(default=True)


# NE PLUS UTILISER -> MIGRE DANS app15_calendar
class Location(models.Model):
    name = models.CharField(max_length=150)
    photo = models.ImageField(blank=True)
    new_pk = models.IntegerField(null=True)

    class Meta:
        app_label = 'app10_social_activities'
        verbose_name = _('Place')
        verbose_name_plural = _('Places')

    def __str__(self):
        return f"{self.name}"


class MealBooking(models.Model):
    owner = models.ForeignKey(Profile, on_delete=models.CASCADE, null=True)
    date = models.DateField(null=True)
    lunch = models.BooleanField(default=False)
    dinner = models.BooleanField(default=False)
    is_lunch_served = models.BooleanField(default=False)
    is_dinner_served = models.BooleanField(default=False)
    is_lunch_ready = models.BooleanField(default=False)
    is_dinner_ready = models.BooleanField(default=False)
    guests = models.ManyToManyField(User)
    other_guests = models.IntegerField(null=True, default=0)
    private = models.BooleanField(default=False)
    updated = models.DateTimeField(auto_now=True)
    surprise = models.BooleanField(default=False)

    def __str__(self):
        return '{} - {} - {}'.format(self.date, self.lunch, self.dinner)


# ---------------------------------------------  DOC  ------------------------------------------------------------------


@deconstructible()
class InvoiceFile(object):
    def __call__(self, instance, filename):
        path = 'doc_adm/invoice/'
        token = secrets.token_hex()
        file = f'{token}'
        return os.path.join(path, file)


invoice_file = InvoiceFile()


class Invoice(models.Model):
    INVOICE_CHOICES = [
        ('invoice', _('Invoice')),
        ('invoice_hairdresser', _('Invoice Hairdresser')),
        ('invoice_pedicure', _('Invoice Pedicure')),
        ('invoice_pharmacy', _('Invoice Pharmacy')),
        ('other_invoice', _('Other Invoice')),
    ]
    user_resident = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='user', verbose_name=_('Resident'))
    name = models.CharField(max_length=100, verbose_name=_('Name of invoice'), help_text=_('Define name for this invoice'), default=_('Invoice EHPAD'))
    type = models.CharField(max_length=50, choices=INVOICE_CHOICES, verbose_name=_('Type of invoice'), default='invoice')
    upload = models.FileField(upload_to=invoice_file, verbose_name=_('File'), null=True, blank=True)
    pub_date = models.DateField(default=timezone.localtime, verbose_name=_('Publication date'), help_text=_('Define the day/month/year of the invoice'))
    added_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('Added by'), related_name='staff', null=True)

    class Meta:
        verbose_name = _('Invoice')

    def __str__(self):
        return '{} - {} - {}'.format(self.user_resident, self.type, self.pub_date)


@deconstructible()
class MutualDocumentsFile(object):
    def __call__(self, instance, filename):
        path = 'doc_adm/documents/mutual'
        token = secrets.token_hex()
        file = f'{token}'
        return os.path.join(path, file)


mutual_documents_file = MutualDocumentsFile()

DOCUMENTS_CHOICES = [
    ('bond', _('Surety Bond')),
    ('stay-contract', _('Stay Contract')),
    ('general-condition', _('General Condition')),
    ('price-statement', _('Price Statement')),
    ('benefit', _('Benefit')),
    ('endorsement', _('Endorsement')),
    ('rules-operation', _('Rules Operation')),
    ('conduct-charter', _('Conduct Charter')),
    ('reading-certificate', _('Reading Certificate')),
    ('image-authorization', _('Image Authorization')),
]


class MutualDocument(models.Model):
    file = models.FileField(upload_to=mutual_documents_file, validators=[validate_file_extension],
                            verbose_name=_('File'))
    document_type = models.CharField(verbose_name=_('Type of document'), max_length=100, choices=DOCUMENTS_CHOICES,
                                     default=None)
    added_date = models.DateField(default=timezone.localtime, verbose_name=_('Add date'))

    def __str__(self):
        return '{}'.format(self.document_type)


class PersonalizedDocument(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name=_('User'))
    user_resident = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name=_('Resident'))
    file = models.FileField(upload_to=mutual_documents_file, validators=[validate_file_extension],
                            verbose_name=_('File'))
    document_type = models.CharField(max_length=100, choices=DOCUMENTS_CHOICES, default=None,
                                     verbose_name=_('Type of document'))

    def __str__(self):
        return '{} {}'.format(self.user, self.document_type)


@deconstructible()
class AdministrativeDocumentsFile(object):
    def __call__(self, instance, filename):
        path = 'doc_adm/documents/'
        token = secrets.token_hex()
        file = f'{token}'
        return os.path.join(path, file)


administrative_documents_file = AdministrativeDocumentsFile()


class AdministrativeDocument(models.Model):
    user_family = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name=_('Family'))
    user_resident = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('Resident'))
    document_type = models.CharField(
        max_length=100, choices=DOCUMENTS_CHOICES, default=None, verbose_name=_('Type of document')
    )
    file = models.FileField(
        upload_to=administrative_documents_file, validators=[validate_file_extension], verbose_name=_('File'),
    )
    envelope_id = models.CharField(max_length=100, null=True, blank=True, default=None, verbose_name=_('Envelope id'))
    doc_id = models.IntegerField(null=True, blank=True, verbose_name=_('Document id'))
    signature_date = models.DateTimeField(null=True, blank=True, verbose_name=_('Signature date'))
    signer_user_id = models.CharField(max_length=100, null=True, blank=True, verbose_name=_('Signer user id'))

    def __str__(self):
        return '{} - {}'.format(self.user_resident, self.document_type)


class KitInventory(models.Model):
    RESPONSE_CHOICES = [
        (_('yes'), _('yes')),
        (_('no'), _('no')),
    ]
    LABELED_MARK_CHOICES = [
        ('labeled by family', _('Laundry labeled by family')),
        ('labeled by residence', _('Laundry labeled by residence')),
    ]
    LAUNDRY_WASHED_CHOICES = [
        ('washed by family', _('Laundry washed by family')),
        ('washed by residence', _('Laundry washed by residence')),
    ]
    DENTAL_EQUIPMENT = [
        (_('top'), _('Top')),
        (_('bottom'), _('Bottom')),
        (_('top bottom'), _('Top and Bottom')),
        (_('does not have'), _('Does not have one')),
    ]
    HEARING_EQUIPMENT = [
        (_('left'), _('Left')),
        (_('right'), _('Right')),
        (_('right left'), _('Right and Left')),
        (_('does not have'), _('Does not have one')),
    ]

    user_resident = models.ForeignKey(User, on_delete=models.CASCADE, related_name=_('Resident'))
    nurses = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name=_('Nurses'))
    creation_date = models.DateField(default=timezone.localtime, verbose_name=_('Add date'))

    laundry_labeled = models.CharField(
        max_length=50, choices=LABELED_MARK_CHOICES, default=None, verbose_name=_('Laundry mark')
    )
    laundry_washed = models.CharField(
        max_length=50, choices=LAUNDRY_WASHED_CHOICES, default=None, verbose_name=_('Laundry washed')
    )
    dental_equipment = models.CharField(
        max_length=17, choices=DENTAL_EQUIPMENT, default=None, verbose_name=_('Dental equipment')
    )
    hearing_equipment = models.CharField(
        max_length=17, choices=HEARING_EQUIPMENT, default=None, verbose_name=_('Hearing equipment')
    )
    cane = models.CharField(max_length=27, choices=RESPONSE_CHOICES, default='no', verbose_name=_('Cane'))
    walker = models.CharField(max_length=27, choices=RESPONSE_CHOICES, default='no', verbose_name=_('Walker'))
    glasses = models.CharField(max_length=27, choices=RESPONSE_CHOICES, default='no', verbose_name=_('Glasses'))
    wheelchair = models.CharField(max_length=27, choices=RESPONSE_CHOICES, default='no', verbose_name=_('Wheelchair'))

    QUANTITY_CHOICES = (
        (0, 0),
        (1, 1),
        (2, 2),
        (3, 3),
        (4, 4),
        (5, 5),
        (6, 6),
        (7, 7),
        (8, 8),
        (9, 9),
        (10, 10),
        (11, 11),
        (12, 12),
        (13, 13),
        (14, 14),
        (15, 15),
    )
    pants = models.IntegerField(choices=QUANTITY_CHOICES, default=0, verbose_name=_('Pants'))
    skirt_dress = models.IntegerField(choices=QUANTITY_CHOICES, null=True, blank=True, default=0,
                                      verbose_name=_('Skirt and dress'))

    pull = models.IntegerField(choices=QUANTITY_CHOICES, default=0, verbose_name=_('Pull'))
    jacket = models.IntegerField(choices=QUANTITY_CHOICES, default=0, verbose_name=_('Jacket'))
    head_cover = models.IntegerField(choices=QUANTITY_CHOICES, default=0, verbose_name=_('Head cover'))
    sweater_long = models.IntegerField(choices=QUANTITY_CHOICES, default=0, verbose_name=_('Long sleeve sweater'))
    sweater_short = models.IntegerField(choices=QUANTITY_CHOICES, default=0, verbose_name=_('Short sleeve sweater'))
    t_shirt_long = models.IntegerField(choices=QUANTITY_CHOICES, default=0, verbose_name=_('Long sleeve t-shirt'))
    t_shirt_short = models.IntegerField(choices=QUANTITY_CHOICES, default=0, verbose_name=_('Short sleeve t-shirt'))

    socks = models.IntegerField(choices=QUANTITY_CHOICES, default=0, verbose_name=_('Socks'))
    slipper = models.IntegerField(choices=QUANTITY_CHOICES, default=0, verbose_name=_('Slipper'))
    summer_shoe = models.IntegerField(choices=QUANTITY_CHOICES, default=0, verbose_name=_('Summer shoe'))
    winter_shoe = models.IntegerField(choices=QUANTITY_CHOICES, default=0, verbose_name=_('Winter  shoe'))

    bra = models.IntegerField(choices=QUANTITY_CHOICES, null=True, blank=True, default=0, verbose_name=_('Bra'))
    underwear = models.IntegerField(choices=QUANTITY_CHOICES, default=0, verbose_name=_('Underwear'))

    nightdress = models.IntegerField(choices=QUANTITY_CHOICES, default=0, verbose_name=_('Nightdress'))
    dressing_gown = models.IntegerField(choices=QUANTITY_CHOICES, default=0, verbose_name=_('Dressing gown'))


class Diet(models.Model):
    DIET_CHOICES = [
        (_('normal'), _('Normal')),
        (_('diabetic'), _('Diabetic')),
        (_('without salt'), _('Without salt')),
        (_('without residue'), _('Without residue')),
        (_('high protein'), _('High protein')),
    ]
    FOOD_CHOICES = [
        (_('normal'), _('Normal')),
        (_('minced'), _('Minced')),
        (_('mixed'), _('Mixed')),
        (_('liquid'), _('Liquid')),
        (_('gelled waters'), _('Gelled waters')),
    ]

    ALLERGIES_CHOICES = (
        (_('gluten'), _('Gluten')),
        (_('peanut'), _('Peanut')),
        (_('milk'), _('Milk')),
        (_('eggs'), _('Eggs')),
        (_('nut'), _('Nut')),
        (_('molluscs'), _('Molluscs')),
        (_('seafood'), _('Seafood')),
        (_('mustard'), _('Mustard')),
        (_('fish'), _('Fish')),
        (_('celery'), _('Celery')),
        (_('soy'), _('Soy')),
        (_('sulphites'), _('Sulphites')),
        (_('sesame'), _('Sesame')),
        (_('lupine'), _('Lupine')),
    )

    user_resident = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('Resident'))
    type_diet = models.CharField(max_length=30, choices=DIET_CHOICES, null=True, blank=True, default=None,
                                 verbose_name=_('Type of diet'))
    food_option = models.CharField(max_length=30, choices=FOOD_CHOICES, null=True, blank=True, default=None,
                                   verbose_name=_('Food option'))
    allergies = MultiSelectField(choices=ALLERGIES_CHOICES, null=True, blank=True, verbose_name=_('Allergies'))


@deconstructible()
class CardFile(object):
    def __call__(self, instance, filename):
        path = 'doc_adm/card/'
        token = secrets.token_hex()
        file = f'{token}'
        return os.path.join(path, file)


card_file = CardFile()


class Card(models.Model):
    CARD_CHOICES = [
        ('national_card', _('National Card')),
        ('vital_card', _('Vital Card')),
        ('mutual_card', _('Mutual Card')),
        ('blood_card', _('Blood Card')),
    ]
    user_resident = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('Resident'), null=True, blank=True)
    type_card = models.CharField(max_length=30, choices=CARD_CHOICES, default=None, verbose_name=_('Type of card'))
    upload_card = models.FileField(upload_to=card_file, verbose_name=_('File'))
    active = models.BooleanField(default=False, verbose_name=_('Is active'))

    # sent_to_netsoins = models.BooleanField(default=False, null=True, blank=True)

    def __str__(self):
        return '{} - {} - {}'.format(self.user_resident, self.type_card, self.active)


# -----------------------------------------------------------------------------------------------------------------------


class AlexaOrders(models.Model):
    ORDER_CHOICES = [
        ('visio_call', _('Visio Call')),
        ('back_to_index', _('Back to Index')),
    ]
    alexa_device_id = models.CharField(max_length=250, null=True, blank=True)
    order_type = models.CharField(max_length=50, choices=ORDER_CHOICES, default='')
    video_call_contact_id = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    score = models.CharField(max_length=50, null=True, blank=True)


class Photos(models.Model):
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    date_add = models.DateTimeField(auto_now_add=True)
    file = models.ImageField(upload_to='tmp_photos/', validators=[validate_image])
    identified = models.ManyToManyField(ProfileSerenicia, blank=True)


class WordToRecord(models.Model):
    text = models.CharField(max_length=500)
    points = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f'{self.text} ({self.points} pts)'


class IntonationToRecord(models.Model):
    text = models.CharField(max_length=100)
    points = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f'{self.text} ({self.points} pts)'


class PayRoll(models.Model):
    employees = models.ForeignKey(User, limit_choices_to=Q(groups__permissions__codename='view_internalemployees'), related_name='user_list', verbose_name=_("Name of employee"), blank=True, on_delete=models.CASCADE)
    date_of_payslip = models.DateField(default=date_payroll, verbose_name=_('Date of payslip'), help_text=_("Chose a date with correct month of payslip, dont mind the day"))
    payslip = models.FileField(upload_to='payroll/', verbose_name=_('Payslip'), null=True, blank=True)

    class Meta:
        verbose_name = _('Payroll')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['employees', 'date_of_payslip'], name='Can have one payslip per month per employee in a year'),
        ]


# class Integralift(model.Model):
#     integralift = models.BooleanField()

class EmptyRoomCleaned(models.Model):
    client = models.OneToOneField(Client, on_delete=models.CASCADE)
    inventory = models.BooleanField(default=False, help_text=_("State of fixtures"))
    disinfection = models.BooleanField(default=False, help_text=_("Smoke disinfection"))
    painting = models.BooleanField(default=False, help_text=_("Painting done"))
    menage = models.BooleanField(default=False, help_text=_("Menage done"))
    bed = models.BooleanField(default=False, help_text=_("Bed done"))

    def __str__(self):
        return f'{self.client} - {self.inventory} - {self.painting} - {self.menage} - {self.bed}'

    class Meta:
        verbose_name = _('Empty Room Cleaned')
