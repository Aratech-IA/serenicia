from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User, Permission, ContentType
from django import forms
from .models import Image, Title, Protocol, Room, Message, Protocol_list, Tag
from .models_qualite import Chapitre, Thematique, Objectif, Critere, ChampApplicationPublic, Elementsevaluation, References, Response

########################################################################################################################
# This is where we define the admin interface for the chat models.

admin.site.register(Room)
admin.site.register(Message)


########################################################################################################################
# This where we define the admin interface for the protocols models

class TitleTabularInline(admin.TabularInline):
    model = Protocol.title.through


class ImageTabularInline(admin.TabularInline):
    model = Title.image.through


@admin.register(Protocol)
class ProtocolAdmin(admin.ModelAdmin):
    inlines = [TitleTabularInline]
    exclude = ['title']
    list_display = ['name']
    search_fields = ['name']


@admin.register(Title)
class TitleAdmin(admin.ModelAdmin):
    inlines = [ImageTabularInline]
    exclude = ['image']


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ['image']


########################################################################################################################

# qualite

class ReferencesAdmin(admin.ModelAdmin):
    model = References
    search_fields = ('detail',)
    ordering = ("reference", "detail",)


class CritereAdmin(admin.ModelAdmin):
    model = Critere
    ordering = ("chapitre__number", "objectif__number", "number")


class ElementsevaluationAdmin(admin.ModelAdmin):
    model = Elementsevaluation
    search_fields = ('critere__title',)
    ordering = ("critere__chapitre__number", "critere__objectif__number", "critere__number",)


admin.site.register(Chapitre)
admin.site.register(Thematique)
admin.site.register(Objectif)
admin.site.register(Critere, CritereAdmin)
admin.site.register(ChampApplicationPublic)
admin.site.register(Elementsevaluation, ElementsevaluationAdmin)
admin.site.register(References, ReferencesAdmin)
admin.site.register(Response)
admin.site.register(Tag)
admin.site.register(Protocol_list)
