from django.db import models
from django.utils.translation import gettext_lazy as _
from datetime import datetime

# Ne pas supprimer l'import ci-dessous, il est utile
from app11_quality import models_qualite


# Here we define the image model of the protocol
class Image(models.Model):
    image = models.ImageField(upload_to='protocol_images/', verbose_name=_('Picture'))


# Here we define the content model of the protocol
class Title(models.Model):
    name = models.CharField(max_length=255, verbose_name=_('Title'))
    description = models.TextField(verbose_name=_('Description'))
    image = models.ManyToManyField(Image, verbose_name=_('Picture'))


# Here we define the protocol model, with the name/type Exemple : CARSAT, Hygiene ...
class Protocol(models.Model):
    VALUE_CHOICES = (
        ("generic", _("Generic")),
        ("specific", _("Specific")),
    )

    name = models.CharField(max_length=200)
    title = models.ManyToManyField(Title, blank=True,
                                   verbose_name=_("Content of the protocol"))
    category = models.CharField(max_length=15, choices=VALUE_CHOICES, verbose_name=_("Category"))


##################################################################################
class Tag(models.Model):
    # VALUE_CHOICES = (
    #     ("nursing", _("Nursing")),
    #     ("treatment", _("Treatment")),
    #     ("recommandation", _("Recommandation")),
    # )
    name = models.CharField(max_length=15, verbose_name=_("Tag"), unique=True)


class Protocol_list(models.Model):
    name = models.CharField(max_length=200)
    file = models.FileField(upload_to='protocol_list/', verbose_name=_('File'))
    tag = models.ManyToManyField(Tag, blank=True, verbose_name=_("Flag"))
    description = models.TextField(verbose_name=_('Description'), max_length=255)

    def __str__(self):
        return self.name


##################################################################################

# Here we define chat models

# Here we define the room model which contains a name
class Room(models.Model):
    name = models.CharField(max_length=255, verbose_name=_('Name'))


# Here we define the message model which is defined by its value ( message content  the date, its user and the room
# where it's been posted
class Message(models.Model):
    value = models.TextField(verbose_name=_('Value'))
    date = models.DateTimeField(default=datetime.now, blank=True, verbose_name=_('Date'))
    user = models.CharField(max_length=255, verbose_name=_('User'))
    room = models.ForeignKey(Room, on_delete=models.CASCADE, verbose_name=_('Room'))


class TempMessage(models.Model):
    value = models.TextField(verbose_name=_('Value'))
    date = models.DateTimeField(default=datetime.now, blank=True, verbose_name=_('Date'))
    user = models.CharField(max_length=255, verbose_name=_('User'))
    room = models.ForeignKey(Room, on_delete=models.CASCADE, verbose_name=_('Room'), null=True)
