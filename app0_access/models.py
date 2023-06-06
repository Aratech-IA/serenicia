from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings


class Security(models.Model):
    description = models.TextField()

    def __str__(self):
        return f'{_("Access to")} {_("the security interface")}'


if settings.DOMAIN.lower() == 'serenicia':
    USER_TYPE = {'view_as': 'AS',
                 'view_ash': 'ASH',
                 'view_ide': 'IDE',
                 'view_family': _('Family member'),
                 'view_prospect': _('Prospect'),
                 'view_practicians': _('Practician'),
                 'view_resident': _('Resident'),
                 'view_residentehpad': _('Resident Ehpad'),
                 'view_residentrss': _('Resident RSS'),
                 'view_manager': _('Manager'),
                 'view_otheremployee': _('Other employee'),
                 'view_otherextern': _('Other external worker'),
                 }

    # This dictionnary could be generate automatically and class for right should have a precise description
    ACCESS_DESCRIPTIONS = {'view_invoicemanagement': {'app_name': _('Invoice Management'),
                                                      'description': _('Can manage the invoices for the family')},
                           'view_usermanagement': {'app_name': _('User Management'),
                                                   'description': _('Can manage the users and the residences ')},
                           'view_payrollmanager': {'app_name': _('Payroll Management'),
                                                   'description': _('Can make pay sheet ')},
                           'view_contact': {'app_name': _('Hotline'),
                                            'description': _('Hotline member')},
                           'view_synerpa': {'app_name': _('Synerpa'),
                                            'description': _('Customer from Synerpa')},
                           'view_internalemployees': {'app_name': _('Payroll'),
                                                      'description': _('Can get payroll')},
                           'view_security': {'app_name': _('Security'),
                                             'description': _('Access to the security interface')},
                           'view_supportproject': {'app_name': _('Support project'),
                                                   'description': _('Access to the support project interface')},
                           'view_createaccount': {'app_name': _('User account'),
                                                  'description': _('Access to the user account creation')},
                           'view_cuisine': {'app_name': _('Cuisine'),
                                            'description': _('Access to the cuisine interface')},
                           'view_evalmenu': {'app_name': "Eval'Menu", 'description': _("Can use Eval'Menu")},
                           'view_communication': {'app_name': _('Communication'),
                                                  'description': _('Can use the mail app')},
                           'view_care': {'app_name': _('Care'), 'description': _('Access to the care interface')},
                           'view_documents': {'app_name': _('Documents'),
                                              'description': _('Access to the administrative documents interface')},
                           'view_contactdemo': {'app_name': _('Demonstration'),
                                                'description': _('Receive mail for demonstration requests')},
                           'view_massmailing': {'app_name': _('Mass mailing'),
                                                'description': _('Can send mail to prospects')},
                           'view_groupreservation': {'app_name': _('Group reservation'),
                                                     'description': _('Can book meal for groups')},
                           'view_photostaff': {'app_name': _('Photos'),
                                               'description': _('Can take public or private photos')},
                           'view_animation': {'app_name': _('Social life'),
                                              'description': _('Access to the social life interface')},
                           'view_blog': {'app_name': _('Blog'), 'description': _('Access to blog interface')},
                           'view_registerfacereco': {'app_name': _('Facial recognition'),
                                                     'description':
                                                         _('Can create facial recognition videos for residents')},
                           'view_hotel': {'app_name': _('Hotel'), 'description': _('Access to the hotel interface')},
                           'view_delivery': {'app_name': _('Delivery'),
                                             'description': _('Access to the delivery interface')},
                           'view_quality': {'app_name': _('Referential'),
                                            'description': _('Access to referential interface')},
                           'view_genosociogram': {'app_name': _('Genosociogram'),
                                                  'description': _('Access to the genosociogram interface')},
                           'view_monavis': {'app_name': _('My opinion'),
                                            'description': _('Access to the Mon Avis interface')},
                           'view_rightsmanagement': {'app_name': _('Access management'),
                                                     'description': _('Access to the access management interface')},
                           'view_app5customgroup': {'app_name': _('Messaging'),
                                                    'description': _('Can manage custom groups')}}

    RELATED_PERMISSIONS = {
        'view_invoicemanagement': {'perms': [{'app_label': 'app4_ehpad_base', 'models': ['invoice', ]}, ],
                                   'description': _('Access administration to manage invoices')},
        'view_usermanagement': {'perms': [{'app_label': 'app1_base', 'models': ['client', 'profile', ]},
                                          {'app_label': 'app4_ehpad_base', 'models': ['profileserenicia', ]},
                                          {'app_label': 'auth', 'models': ['user', ]}],
                                'description': _('Access administration to manage users and residence')},
        'view_payrollmanager': {'perms': [{'app_label': 'app4_ehpad_base', 'models': ['payroll', ]}, ],
                                'description': _('Access administration to make the pay sheet')},
        'view_supportproject': {'perms': [{'app_label': 'app9_personnalized_project', 'models': ['chapter', 'question', 'survey',
                                                                              'appointmentslot', 'notation',
                                                                              'storylifetitle',
                                                                              'unavailability', 'importedproject']},
                                          {'app_label': 'app8_survey', 'models': ['chapter', 'notationchoices',
                                                                           'question', 'survey']}],
                                'description': _('Can access to Support project administration')},
        'view_animation': {'perms': [{'app_label': 'app10_social_activities', 'models': ['question', 'report']},
                                     {'app_label': 'app15_calendar', 'models': ['planningevent', 'recurrence', 'event',
                                                                              'location']}],
                           'description': _('Can access to Social Life administration')},
        'view_cuisine': {'perms': [{'app_label': 'app4_ehpad_base', 'models': ['presentationtype']},
                                   {'app_label': 'app0_access', 'models': ['cuisineprice']}],
                         'description': _('Can access cuisine administration and view the prices in the interface')},
        'view_quality': {'perms': [{'app_label': 'app11_quality', 'models': ['critere']}],
                         'description': _('Can choose people to answer the criteria')},
        'view_monavis': {'perms': [{'app_label': 'app8_survey', 'models': ['survey', 'chapter', 'question', 'notationchoices']}],
                         'description': _('Access to Mon Avis administration')}
    }


    def get_permission_description(codename):
        try:
            result = ACCESS_DESCRIPTIONS[codename]
        except KeyError:
            return None
        return f'{result} : {codename}'

    class UserManagement(models.Model):
        def __str__(self):
            return f'{_("Manage users and residence")}'


    class OtherExtern(models.Model):
        def __str__(self):
            return f'{_("External worker with no specific rights")}'


    class OtherEmployee(models.Model):
        def __str__(self):
            return f'{_("Employee with no specific rights")}'


    class SupportProject(models.Model):
        def __str__(self):
            return f'{_("Access to")} {_("the personalized support project")}'


    class CreateAccount(models.Model):
        def __str__(self):
            return f'{_("Access to")} {_("user account creation")}'


    class Cuisine(models.Model):
        def __str__(self):
            return f'{_("Access to")} {_("the kitchen interface")}'


    class CuisinePrice(models.Model):
        def __str__(self):
            return f'{_("Add prices to")} {_("the kitchen interface")}'


    class EvalMenu(models.Model):
        def __str__(self):
            return f'{_("Access to")} {_("rating for meals")} Eval\'Menu'


    class Communication(models.Model):
        def __str__(self):
            return f'{_("Access to")} {_("the communication interface")}'


    class Care(models.Model):
        def __str__(self):
            return f'{_("Access to")} {_("the care interface")}'


    class Documents(models.Model):
        def __str__(self):
            return f'{_("Access to")} {_("the documents interface")}'


    class Resident(models.Model):
        def __str__(self):
            return f'{_("Access to")} {_("the TV interface")}'


    class ResidentEhpad(models.Model):
        def __str__(self):
            return f'{_("Access to")} {_("the EHPAD services")}'

    class ResidentRSS(models.Model):
        def __str__(self):
            return f'{_("Access to")} {_("the RSS services")}'


    class Contact(models.Model):
        def __str__(self):
            return f'{_("Can be contacted by users")}'


    class ContactDemo(models.Model):
        def __str__(self):
            return f'{_("Receive mail for demonstration requests")}'


    class AS(models.Model):
        def __str__(self):
            return f'{_("Caregiver")}'


    class ASH(models.Model):
        def __str__(self):
            return f'{_("Hospital services officer")}'


    class Synerpa(models.Model):
        def __str__(self):
            return f'{_("Synerpa")}'


    class IDE(models.Model):
        def __str__(self):
            return f'{_("Nurse")}'


    class Family(models.Model):
        def __str__(self):
            return f'{_("Family")}'


    class Prospect(models.Model):
        def __str__(self):
            return f'{_("Prospect")}'


    class MassMailing(models.Model):
        def __str__(self):
            return f'{_("Can send mails to prospects")}'


    class GroupReservation(models.Model):
        def __str__(self):
            return f'{_("Can book meal for group")}'


    class Manager(models.Model):
        def __str__(self):
            return f'{_("Manager")}'


    class PhotoStaff(models.Model):
        def __str__(self):
            return f'{_("Can take photos")}'


    class Animation(models.Model):
        def __str__(self):
            return f'{_("Access to")} {_("Animation interface")}'


    class Blog(models.Model):
        def __str__(self):
            return f'{_("Can access to blog")}'


    class RegisterFaceReco(models.Model):
        def __str__(self):
            return f'{_("Can create facial recognition videos for residents")}'


    class MonAvis(models.Model):
        def __str__(self):
            trad = _('Access to the Mon Avis interface')
            return trad

    # --------------------------------------------FACTURES------------------------------------------------------------------
    class InvoiceManagement(models.Model):
        def __str__(self):
            return f'{_("Invoice Management")}'

    # ----------------------------------------------------------------------------------------------------------------------
    class Admin(models.Model):
        def __str__(self):
            return f'{_("Admin")}'


    class Doctor(models.Model):
        def __str__(self):
            return f'{_("Doctor")}'


    class Hotel(models.Model):
        def __str__(self):
            return f'{_("Hotel")}'


    class InternalEmployees(models.Model):
        def __str__(self):
            return f'{_("Can get payroll")}'

    class PayrollManager(models.Model):
        def __str__(self):
            return f'{_("Can make payroll")}'

    class Practicians(models.Model):
        def __str__(self):
            return f'{_("Practicians")}'

    # --------------------------------------------Delivery------------------------------------------------------------------
    class Delivery(models.Model):
        def __str__(self):
            return f'{_("Access to")} {_("provide delivery")}'


    class DeliveryBusiness(models.Model):
        def __str__(self):
            return f'{_("Access to")} {_("provide all access for app delivery")}'


    class CustomerDelivery(models.Model):
        def __str__(self):
            return f'{_("Access to")} {_("provide customer of delivery")}'

    # --------------------------------------------Quality------------------------------------------------------------------
    class Quality(models.Model):
        description = models.TextField()

        def __str__(self):
            return f'{_("Access to")} {_("Quality")}'


    class ResponseQuality(models.Model):
        description = models.TextField()

        def __str__(self):
            return f'{_("Access to")} {_("Response to Criterion")}'


    class Genosociogram(models.Model):
        def __str__(self):
            return f'{_("Access to")} {_("genosociogram")}'


    class RightsManagement(models.Model):
        def __str__(self):
            return _('access to rights management interface')


    class App5CustomGroup(models.Model):
        def __str__(self):
            return _('Can manage custom group')
