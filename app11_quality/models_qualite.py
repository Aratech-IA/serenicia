from datetime import datetime
from multiprocessing import Value
from django.db import models
from app1_base.models import Profile
from app4_ehpad_base.models import ProfileSerenicia
from django.utils.translation import gettext_lazy as _
from django.conf import settings


class Chapitre(models.Model):
    number = models.PositiveIntegerField(verbose_name=_('Order'), unique=True)
    title = models.CharField(max_length=50, verbose_name=_('Title'))

    def __str__(self):
        return f'{self.number} - {self.title}'

    class Meta:
        verbose_name = _('Chapter')


class Thematique(models.Model):
    number = models.PositiveIntegerField(verbose_name=_('Order'))
    title = models.CharField(max_length=100, verbose_name=_('Title'))

    def __str__(self):
        return f'{self.title}'


class Objectif(models.Model):
    number = models.PositiveIntegerField(verbose_name=_('Order'))
    title = models.CharField(max_length=200, verbose_name=_('Title'))

    def __str__(self):
        return f'{self.number} - {self.title}'

    class Meta:
        verbose_name = _('Goal')


class ChampApplicationPublic(models.Model):
    PUBLIC_CHOICES = (
        ('pa', _('PA')),
        ('pha', _('PHA')),
        ('phe', _('PHE')),
        ('pds', _('PDS')),
        ('ahi', _('AHI')),
        ('pe-pjj', _('PE-PJJ'))
    )
    public = models.CharField(max_length=20, choices=PUBLIC_CHOICES, verbose_name=_('Public'))

    def __str__(self):
        return f'{self.public}'


class References(models.Model):
    REFERENCE_CHOICES = (
        ('globales', _('HAS - Global')),
        ('specifiques', _('HAS – specific')),
        ('references', _('Legal and regulatory references')),
        ('autresreferences', _('Other references'))
    )
    reference = models.CharField(max_length=20, choices=REFERENCE_CHOICES, verbose_name=_('Reference'))
    detail = models.CharField(max_length=300, verbose_name=_('Detail'))
    reference_url = models.CharField(max_length=500, verbose_name=_('Url reference'))

    def __str__(self):
        return f'{self.reference} - {self.detail} - {self.reference_url}'


class Critere(models.Model):
    chapitre = models.ForeignKey(Chapitre, on_delete=models.CASCADE, verbose_name=_('Chapter'))
    thematique = models.ForeignKey(Thematique, on_delete=models.CASCADE, verbose_name=_('Thematic'))
    objectif = models.ForeignKey(Objectif, on_delete=models.CASCADE, verbose_name=_('Goal'))
    number = models.PositiveIntegerField(verbose_name=_('Order'))
    title = models.CharField(max_length=300, verbose_name=_('Title'))
    manager = models.ForeignKey(ProfileSerenicia, on_delete=models.CASCADE, verbose_name=_('Manager'), null=True)

    EXIGENCE_CHOICES = (
        ('standard', _('Standard')),
        ('imperative', _('Imperative'))
    )
    exigence = models.CharField(max_length=20, choices=EXIGENCE_CHOICES, verbose_name=_("Requirement level"))

    manager_choices = (
        ('all', _('All')),
        ('personals', _('My critera'))
    )

    ESSMS_CHOICES = (
        ('essms', _('All ESSMS')),
        ('social', _('Social')),
        ('medicosocial', _('Medico-social'))
    )
    essms = models.CharField(max_length=20, choices=ESSMS_CHOICES, verbose_name=_('ESSMS'))

    STRUCTURE_CHOICES = (
        ('structures', _('All structures')),
        ('etablissement', _('Establishment')),
        ('service', _('Service'))
    )
    structure = models.CharField(max_length=20, choices=STRUCTURE_CHOICES, verbose_name=_('Structure'))

    public = models.ManyToManyField(ChampApplicationPublic, verbose_name=_('Public'))
    reference = models.ManyToManyField(References, verbose_name=_('Reference'))

    def __str__(self):
        return f'{self.chapitre.number} - {self.objectif.number} - {self.number} - {self.title}'

    class Meta:
        verbose_name = _('Criterion')


class Elementsevaluation(models.Model):
    ELEMENT_CHOICES = (
        ('entretienpersonne', _('Interview with the person')),
        ('entretienpro', _('Interview with the professionals')),
        ('entretiencsv', _('Interview with CVS members')),
        ('entretienessms', _('Interview with the ESSMS')),
        ('consultationdoc', _('Document consultation')),
        ('observation', _('Observation'))
    )

    EVALUATION_CHOICES = (
        (1, _('Not at all satisfactory')),
        (2, _('Rather unsatisfactory')),
        (3, _('Quite satisfying')),
        (4, _('Quite satisfactory')),
        (5, _('Optimized')),
    )

    critere = models.ForeignKey(Critere, on_delete=models.CASCADE, verbose_name=_('Criterion'))
    element = models.CharField(max_length=20, choices=ELEMENT_CHOICES, verbose_name=_('Elements of evaluation'))
    detail = models.CharField(max_length=500, verbose_name=_('Detail'))
    evaluation = models.IntegerField(choices=((0, _('In progress')),) + EVALUATION_CHOICES, default=0)

    def __str__(self):
        return f'{self.critere} - {self.detail}'


class Response(models.Model):
    critere = models.ForeignKey(Critere, on_delete=models.CASCADE, verbose_name=_('Criterion'))
    text = models.TextField(null=True)
    date = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(ProfileSerenicia, on_delete=models.CASCADE)
    protocols = models.ManyToManyField('app11_quality.Protocol_list', verbose_name=_('Protocol'))

    def get_photo_url(self):
        try:
            photo=self.created_by.user.profile.photo.url
        except ValueError:
            photo=settings.STATIC_URL + 'app1_base/img/bi/person-circle.svg'
        return photo
