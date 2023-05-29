from datetime import datetime

from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db.models import Q
from geopy.geocoders import Nominatim
from django.db import models

# add profile
from app1_base.models import Profile
from django.utils.translation import gettext_lazy as _


class DeliveryDay(models.Model):
    monday = models.BooleanField(default=False, verbose_name=_("Monday"))
    tuesday = models.BooleanField(default=False, verbose_name=_("Tuesday"))
    wednesday = models.BooleanField(default=False, verbose_name=_("Wednesday"))
    thursday = models.BooleanField(default=False, verbose_name=_("Thursday"))
    friday = models.BooleanField(default=False, verbose_name=_("Friday"))
    saturday = models.BooleanField(default=False, verbose_name=_("Saturday"))
    sunday = models.BooleanField(default=False, verbose_name=_("Sunday"))

    def get_day_valid_choices(self):
        list_tmp = []
        if self.monday:
            list_tmp.append(("monday", _("Monday")))
        if self.tuesday:
            list_tmp.append(("tuesday", _("Tuesday")))
        if self.wednesday:
            list_tmp.append(("wednesday", _("Wednesday")))
        if self.thursday:
            list_tmp.append(("thursday", _("Thursday")))
        if self.friday:
            list_tmp.append(("friday", _("Friday")))
        if self.saturday:
            list_tmp.append(("saturday", _("Saturday")))
        if self.sunday:
            list_tmp.append(("sunday", _("Sunday")))
        return list_tmp

    def get_day_valid(self, qs, day):
        if self.monday and qs.monday and day == "Monday":
            return True
        if self.tuesday and qs.tuesday and day == "Tuesday":
            return True
        if self.wednesday and qs.wednesday and day == "Wednesday":
            return True
        if self.thursday and qs.thursday and day == "Thursday":
            return True
        if self.friday and qs.friday and day == "Friday":
            return True
        if self.saturday and qs.saturday and day == "Saturday":
            return True
        if self.sunday and qs.sunday and day == "Sunday":
            return True
        return False

    def __str__(self):
        return f'Week Active for Business'


class ContractDelivery(models.Model):
    type_housing_choices = [
        ('house', 'Maison individuelle'),
        ('apartment', 'Appartement'),
    ]
    payment_method_choices = [
        ('check', 'Chèque'),
        ('sampling', 'Prélèvement SEPA'),
    ]
    date_start_contract = models.DateField(null=True)
    date_end_contract = models.DateField(null=True, blank=True)
    type_housing = models.CharField(choices=type_housing_choices, max_length=100, default="house")
    comment_access = models.CharField(max_length=256, blank=True)
    payment_method = models.CharField(choices=payment_method_choices, max_length=100, default="check")
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Contrat de -> {self.profile.user.last_name} , {self.profile.user.first_name}'


class WeekOfContract(models.Model):
    monday = models.BooleanField(default=False, verbose_name=_("Monday"))
    tuesday = models.BooleanField(default=False, verbose_name=_("Tuesday"))
    wednesday = models.BooleanField(default=False, verbose_name=_("Wednesday"))
    thursday = models.BooleanField(default=False, verbose_name=_("Thursday"))
    friday = models.BooleanField(default=False, verbose_name=_("Friday"))
    saturday = models.BooleanField(default=False, verbose_name=_("Saturday"))
    sunday = models.BooleanField(default=False, verbose_name=_("Sunday"))
    contract_delivery = models.OneToOneField(ContractDelivery, on_delete=models.CASCADE)


class MealsNumber(models.Model):
    meal_monday = models.IntegerField(default=0, verbose_name=_("Meal Monday"))
    meal_tuesday = models.IntegerField(default=0, verbose_name=_("Meal Tuesday"))
    meal_wednesday = models.IntegerField(default=0, verbose_name=_("Meal Wednesday"))
    meal_thursday = models.IntegerField(default=0, verbose_name=_("Meal Thursday"))
    meal_friday = models.IntegerField(default=0, verbose_name=_("Meal Friday"))
    meal_saturday = models.IntegerField(default=0, verbose_name=_("Meal Saturday"))
    meal_sunday = models.IntegerField(default=0, verbose_name=_("Meal Sunday"))
    week_of_contract = models.OneToOneField(WeekOfContract, on_delete=models.CASCADE)

    def get_nb_meals(self):
        nb = int()
        nb += self.meal_monday
        nb += self.meal_tuesday
        nb += self.meal_wednesday
        nb += self.meal_thursday
        nb += self.meal_friday
        nb += self.meal_saturday
        nb += self.meal_sunday
        return nb


class Referent(models.Model):
    quality_choices = [
        ('Children', 'Enfant'),
        ('Grandchild', 'Petit-enfant'),
        ('business', 'Entreprise'),
        ('other', 'Autre'),
    ]
    quality = models.CharField(choices=quality_choices, max_length=100, default="Children")
    last_name = models.CharField(max_length=100, null=True)
    first_name = models.CharField(max_length=100, null=True)
    phone_number = models.SmallIntegerField(null=True)
    contract = models.OneToOneField(ContractDelivery, on_delete=models.CASCADE)


class Constraint(models.Model):
    type_constraint_choices = [
        ('hourly', 'Horaire'),
        ('allergen', 'Allergie'),
    ]
    constraint_name = models.CharField(choices=type_constraint_choices, max_length=100, default="allergen")
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)


class DeliveryWindow(models.Model):
    day_week_choices = [
        (1, 'Monday'),
        (2, 'Tuesday'),
        (3, 'Wednesday'),
        (4, 'Thursday'),
        (5, 'Friday'),
        (6, 'Saturday'),
        (7, 'Sunday'),
    ]
    day_week_delivery = models.SmallIntegerField(unique=True, choices=day_week_choices, validators=[
        MaxValueValidator(7),
        MinValueValidator(1)
    ])
    time_start = models.TimeField(null=True)
    time_end = models.TimeField(null=True)
    constraint = models.ForeignKey(Constraint, on_delete=models.CASCADE)


class TourDelivery(models.Model):
    date_tour_delivery = models.DateField(null=True, unique=True)
    tour_delivery_routing = models.JSONField()
    time_estimate = models.TimeField(null=True, blank=True)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)

    def get_nb_meals_per_tour(self):
        target_day = datetime.today().date()
        contract_valid = self.delivery_set.filter(profile__user__groups__name="Customer Delivery",)
        for x in contract_valid:
            print(x.profile.contractdelivery_set.first())
        #     de contrat date comprise entre
        print(contract_valid)
        return contract_valid
        # for x in contract_valid:


class Delivery(models.Model):
    order = models.SmallIntegerField(null=True)
    finish = models.BooleanField(default=False)
    tour_delivery = models.ForeignKey(TourDelivery, on_delete=models.CASCADE)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)


class CancelDelivery(models.Model):
    date_cancel = models.DateField()
    commentary_cancel = models.CharField(max_length=255, null=True)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)


class InfoCustomerInvoice(models.Model):
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE)
    # name_regex = RegexValidator(regex=r"^[\\pL]+(([\\pL'\\-])*)+([\\pL])|(^[\\pL])$",
    #                             message=_("Nom d'usage du client. Facultatif si n’est pas différent du nom de "
    #                                       "naissance, attendu si différent. Le nom ne doit pas comporter de "
    #                                       "chiffres, ni de caractères spéciaux à l’exception de l’apostrophe "
    #                                       "(‘), du tiret (-) et de l’espace ( ). Il ne doit ni commencer ni "
    #                                       "finir par un caractère spécial."))
    birth_name = models.CharField(max_length=100, help_text="Nom de naissance du client")
    martial_name = models.CharField(max_length=100, help_text="Nom d'usage du client")
    birth_day = models.DateField(help_text="Date de naissance du client. Obligatoire")
    code_country_regex = RegexValidator(regex=r"^[0-9]{5}$")
    code_country_born = models.CharField(max_length=5, validators=[code_country_regex], help_text=_(
        "Code INSEE du pays sur 5 caractères numériques (cf nomenclature INSEE). Obligatoire"))
    departement_born_regex = RegexValidator(regex="^[09][0-9][0-9abAB]$", message=_("Format : 3 caractères "
                                                                                    "alphanumériques : 001, 040, "
                                                                                    "976. 02B pour le département de "
                                                                                    "Haute-Corse. Précision : cette "
                                                                                    "donnée est obligatoire si et "
                                                                                    "seulement si le code Pays de "
                                                                                    "naissance correspond à celui de "
                                                                                    "la France."))
    departement_born = models.CharField(max_length=3, validators=[departement_born_regex],
                                        help_text="Code INSEE du département à la date de naissance ou "
                                                  "TOM (si pays = "
                                                  "France) Format : 3 caractères alphanumériques : 001, 040, "
                                                  "976. 02B pour le département de Haute-Corse. Précision : cette "
                                                  "donnée est obligatoire si et seulement si le code Pays de "
                                                  "naissance correspond à celui de la France. Facultatif")

    commune_born = models.CharField(max_length=128,
                                    help_text=_("Commune de naissance. Précision : cette donnée est obligatoire si et "
                                                "seulement si le code Pays de naissance correspond à celui de la "
                                                "France. Facultatif"))
    number_lane_regex = RegexValidator(regex="^(?!^0$)([0-9]){0,20}$")
    number_lane = models.CharField(max_length=20, validators=[number_lane_regex],
                                   help_text=_("Numéro de la voie. Facultatif"))
    letter_lane = models.CharField(max_length=1, blank=True,
                                   help_text=_("Lettre associée au numéro de voie (B pour Bis, T pour "
                                               "Ter, Q pour Quater, C pour Quinquiès). Facultatif"))
    code_Type_lane_regex = RegexValidator(regex="^([0-9A-Za-z]){0,4}$",
                                          message=_("4 caratères alphanumeriques maximum."))
    code_Type_lane = models.CharField(max_length=4, blank=True, validators=[code_Type_lane_regex],
                                      help_text=_("Code type de voie. Facultatif."))
    libelle_voie = models.CharField(max_length=28, help_text=_("Nom de la voie. Facultatif"))
    complement = models.CharField(max_length=38, blank=True, help_text=_("Complément d'adresse. Facultatif"))
    said_place = models.CharField(max_length=38, blank=True, help_text=_("Lieu-dit. Facultatif"))
    commune_wording = models.CharField(max_length=50, help_text=_("Libelle de la commune. Obligatoire. Précision : "
                                                                  "les libellés attendus sont ceux du code officiel "
                                                                  "géographique INSEE. Aucun contrôle n'est effectué "
                                                                  "sur le libellé. La validité de l'information est "
                                                                  "de la responsabilité du tiers de prestation"))
    code_commune_regex = RegexValidator(regex="^[0-9][0-9a-bA-B][0-9]{3}$")
    code_commune = models.CharField(max_length=5, validators=[code_commune_regex],
                                    help_text=_("Code INSEE de la commune (cf nomenclature INSEE). "
                                                "Obligatoire. Aucun contrôle n'est effectué  sur "
                                                "l'existence du code. La validité de l'information est "
                                                "de la responsabilité du tiers de prestation"))
    postal_code_regex = RegexValidator(regex="^[0-9]{5}$")
    postal_code = models.CharField(max_length=5, validators=[postal_code_regex],
                                   help_text=_("Code postal de la commune "
                                               "(exemple : 75001 pour "
                                               "Paris 1er "
                                               "arrondissement). "
                                               "Obligatoire"))
    code_country = models.CharField(max_length=5, validators=[code_country_regex], help_text=_("Code INSEE du pays sur "
                                                                                               "5 caractères numériques "
                                                                                               "(cf nomenclature "
                                                                                               "INSEE). Obligatoire. "
                                                                                               "Aucun contrôle n'est "
                                                                                               "effectué  sur "
                                                                                               "l'existence du code. La "
                                                                                               "validité de "
                                                                                               "l'information est de la "
                                                                                               "responsabilité du "
                                                                                               "partenaire."))
    bic_regex = RegexValidator(regex="^[a-zA-Z]{6}[0-9a-zA-Z]{2}([0-9a-zA-Z]{3})?$")
    bic = models.CharField(max_length=11, validators=[bic_regex],
                           help_text=_("Identifiant BIC. Obligatoire. Le BIC est constitué : d’un code "
                                       "banque sur 4 caractères, d’un code pays (ISO 3166) sur 2 "
                                       "caractères, d’un code emplacement sur 2 caractères, "
                                       "d’un code branche, optionnel, sur 3 caractères. Celui-ci peut "
                                       "être facultativement complété avec trois X pour que le BIC "
                                       "soit sur 11 caractères"))
    iban_regex = RegexValidator(regex="^[a-zA-Z]{2}[0-9]{2}[a-zA-Z0-9]{4}[0-9]{7}([a-zA-Z0-9]?){0,16}$")
    iban = models.CharField(max_length=38, validators=[iban_regex], help_text=_("identifiant IBAN. Obligatoire. L’IBAN "
                                                                                "est constitué : d’un code pays (ISO "
                                                                                "3166) sur 2 caractères,d’une clé de "
                                                                                "contrôle sur 2 caractères, permettant "
                                                                                "de s’assurer de l’intégrité du compte, "
                                                                                "d’un BBAN sur 14 à 34 caractères (23 "
                                                                                "caractères pour les comptes français ("
                                                                                "ancien format du RIB))"))
    incumbent = models.CharField(max_length=100,
                                 help_text=_("titulaire du compte, civilité, nom et prénom. Obligatoire"))

    def __str__(self):
        return f'Info User {self.profile.user.last_name}, {self.profile.user.first_name}'


class DesignationInvoice(models.Model):
    percentage_vat_choices = [
        (0.2, '20%'),
        (0.1, '10%'),
        (0.085, '8,5%'),
        (0.055, '5,5%'),
        (0.021, '2,1%'),
    ]
    designation = models.CharField(max_length=128)
    percentage_vat = models.FloatField(choices=percentage_vat_choices)
    price = models.FloatField()

    def __str__(self):
        return f'{self.designation}, {self.get_price_with_vat()}'

    def get_price_with_vat(self):
        return (self.price * self.percentage_vat) + self.price


class InvoiceHomePlus(models.Model):
    number = models.CharField(unique=True, max_length=40)
    amount_without_vat = models.FloatField()
    info_client_invoice = models.ForeignKey(InfoCustomerInvoice, on_delete=models.CASCADE, blank=True, null=True)
    invoice = models.ManyToManyField(
        DesignationInvoice,
        through='NumberDesignationPerInvoice',
        through_fields=('invoice_home_plus', 'designation_invoice'),
        blank=True,
    )


class BillingPerson(models.Model):
    quality_choices = [
        ('Children', 'Enfant'),
        ('Grandchild', 'Petit-enfant'),
        ('business', 'Entreprise'),
        ('other', 'Autre'),
    ]
    quality = models.CharField(choices=quality_choices, max_length=100, default="Children")
    last_name = models.CharField(max_length=100, null=True)
    first_name = models.CharField(max_length=100, null=True)
    address = models.CharField(max_length=256, null=True)
    postal_code = models.SmallIntegerField(null=True)
    town_address = models.CharField(max_length=512, null=True)
    phone_number = models.SmallIntegerField(null=True)
    invoice = models.OneToOneField(InvoiceHomePlus, on_delete=models.PROTECT)


class NumberDesignationPerInvoice(models.Model):
    number_benefit = models.IntegerField()
    invoice_home_plus = models.ForeignKey(InvoiceHomePlus, on_delete=models.CASCADE, blank=True, null=True)
    designation_invoice = models.ForeignKey(DesignationInvoice, on_delete=models.CASCADE)


# ------------------ Admin models proxy ------------------


class BusinessDeliveryUser(User):
    class Meta:
        proxy = True

    def save(self, *args, **kwargs):
        self.set_password(self.password)
        super(User, self).save(*args, **kwargs)


class BusinessDeliveryProfile(Profile):
    class Meta:
        proxy = True

    def save(self, *args, **kwargs):
        full_adress = self.adress + "," + self.city + "," + self.cp
        geolocator = Nominatim(user_agent="deliveryMeal")
        coordinates = geolocator.geocode(full_adress)
        self.adress_latitude = coordinates.latitude
        self.adress_longitude = coordinates.longitude
        super(Profile, self).save(*args, **kwargs)


class DeliveryManUser(User):
    class Meta:
        proxy = True


class BusinessManProfile(Profile):
    class Meta:
        proxy = True
