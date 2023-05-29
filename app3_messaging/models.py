from django.db import models
from django.contrib.auth.models import User, Group
from django.db.models.functions import Lower

from app1_base.models import Profile
from app3_messaging.validators import validate_image
from django.utils.translation import gettext_lazy as _


class GroupsProspects(models.Model):
    group = models.OneToOneField(Group, on_delete=models.CASCADE)
    is_prospect = models.BooleanField(default=False)


class CreateEmail(models.Model):
    nom_du_mail_type = models.CharField(max_length=30, unique=True)
    content = models.TextField()


class Campaign(models.Model):
    nom_de_la_campagne = models.CharField(max_length=120, blank=True, null=True, unique=True)
    number_sent = models.PositiveSmallIntegerField(default=0, blank=True, null=True)
    number_opened = models.PositiveSmallIntegerField(default=0, blank=True, null=True)
    number_clicked = models.PositiveSmallIntegerField(default=0, blank=True, null=True)
    number_unsubscribed = models.PositiveSmallIntegerField(default=0, blank=True, null=True)
    mail_type = models.ForeignKey(CreateEmail, on_delete=models.SET_NULL, blank=True, null=True)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, default=1)


class DataEmail(models.Model):
    clef = models.CharField(max_length=30)
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=1)
    email_adress_sender = models.EmailField(max_length=50)
    subject = models.CharField(max_length=120)
    content = models.TextField()
    campaign_of_mail = models.ForeignKey(Campaign, on_delete=models.CASCADE, blank=True, null=True)
    date_creation = models.DateTimeField(blank=True, null=True)
    date_sent = models.DateTimeField(blank=True, null=True)
    date_opened = models.DateTimeField(blank=True, null=True)
    date_clicked = models.DateTimeField(blank=True, null=True)
    date_unsubscribed = models.DateTimeField(blank=True, null=True)
    is_notif = models.BooleanField(default=False)


class Conversation(models.Model):
    participants = models.ManyToManyField(User)


# class CopieC(models.Model):
#     copie_c_recipients = models.ManyToManyField(User, through='IntermediateCC')

class Tag(models.Model):
    name = models.CharField(max_length=120, blank=True, null=True)
    # color? Pour msg urgents (pastille rouge?)


class IntraEmail(models.Model):
    # sender = models.CharField(max_length=200, blank=True, null=True)  # Identifiant du sender
    recipients = models.ManyToManyField(User, through='Intermediate')
    # recipients_copie_c = models.OneToOneField(CopieC, on_delete=models.CASCADE, blank=True, null=True)
    number_opened = models.PositiveSmallIntegerField(default=0, blank=True, null=True)
    subject = models.CharField(max_length=120)
    content = models.TextField()
    content_text = models.TextField(default='')
    message_conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, blank=True, null=True)
    date_sent = models.DateTimeField(blank=True, null=True)
    is_support = models.BooleanField(default=False)
    tags = models.ManyToManyField(Tag)

    def get_members_id(self):
        return list(self.recipients.values_list('id', flat=True))


class IntraEmailAttachment(models.Model):
    intraemail = models.ForeignKey(IntraEmail, on_delete=models.CASCADE)
    name = models.CharField(max_length=120, blank=True, null=True)
    attachment = models.FileField(upload_to='attachment/%Y/%m/%d', validators=[validate_image], blank=True, null=True)


class Intermediate(models.Model):
    TYPE_CHOICES = (
        ('default', _('default')),
        ('sender', _('sender')),
        ('CC', _('CC')),
        ('CCI', _('CCI')),
    )

    message = models.ForeignKey(IntraEmail, on_delete=models.CASCADE)
    recipient = models.ForeignKey(User, on_delete=models.CASCADE)
    date_opened = models.DateTimeField(blank=True, null=True)
    user_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='default')
    is_shown = models.BooleanField(default=True)

    class Meta:
        unique_together = ('message', 'recipient')


# class IntermediateCC(models.Model):
#     message = models.ForeignKey(CopieC, on_delete=models.CASCADE)
#     recipient = models.ForeignKey(User, on_delete=models.CASCADE)
#     date_opened = models.DateTimeField(blank=True, null=True)
#     is_visible = models.BooleanField(default=True)


class Notification(models.Model):
    subject = models.CharField(max_length=120)
    content = models.TextField()
    recipients = models.ManyToManyField(User)
    date_sent = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    list_opened = models.ManyToManyField(User, blank=True, related_name="list_opened")


class CustomGroup(models.Model):
    groups = models.ManyToManyField(Group)
    members = models.ManyToManyField(User)
    name = models.CharField(max_length=120, unique=True)

    def get_members_id(self):
        result = User.objects.filter(groups__in=self.groups.all(), is_active=True)
        result = result.union(self.members.filter(is_active=True))
        return list(result.values_list('id', flat=True))


class ProfileProspect(models.Model):
    STATUS_CHOICES = (
        ('Privé non lucratif', _('Private non-profit')),
        ('Public', _('Public')),
        ('Privé commercial', _('Private commercial')),
    )
    function = models.CharField(max_length=200, blank=True, null=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    finess = models.CharField(max_length=30, blank=True, null=True)
    name = models.CharField(max_length=300, blank=True, null=True)
    capacity = models.PositiveIntegerField(default=0, blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, blank=True, null=True)
    dept_name = models.CharField(max_length=120, blank=True, null=True)
    dept_code = models.CharField(max_length=10, blank=True, null=True)
    gestionnaire = models.CharField(max_length=300, blank=True, null=True)
    info_presta = models.TextField(blank=True, null=True)
    info_tarif = models.TextField(blank=True, null=True)


class ProspectUser(User):
    class Meta:
        proxy = True


class ProspectUserProfile(Profile):
    class Meta:
        proxy = True
        verbose_name_plural = 'Prospect Unsubscribe'


class ProspectUserActive(User):
    class Meta:
        proxy = True
        verbose_name_plural = 'Prospect Active'
