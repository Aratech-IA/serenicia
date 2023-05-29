from django.core.files.storage import default_storage
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone
from pathlib import Path

from app1_base.models import Profile, Client
from app4_ehpad_base.models import ProfileSerenicia, MealPresentation, BlogImage, EmptyRoomCleaned


@receiver(post_save, sender=ProfileSerenicia)
def update_date_deceased_status(instance, **kwargs):
    if instance.status == 'deceased' and (instance.date_status_deceased is None or instance.date_status_deceased == ''):
        instance.date_status_deceased = timezone.localtime().date()
        instance.save()


@receiver(pre_delete, sender=MealPresentation)
def delete_photo(instance, **kwargs):
    if instance.photo:
        Path(instance.photo.path).unlink(missing_ok=True)


@receiver(pre_delete, sender=BlogImage)
def delete_image(instance, **kwargs):
    if '/common/' not in instance.image:
        file_path = instance.image_blog
        default_storage.delete(file_path)
        full_pic = file_path.split('thumbnails/')
        default_storage.delete(full_pic[0] + full_pic[1])


@receiver(post_save, sender=Profile)
def profil_in_client(instance, **kwargs):
    for room in Client.objects.filter(profile__isnull=True, emptyroomcleaned__isnull=True):
        EmptyRoomCleaned.objects.create(client=room)
    EmptyRoomCleaned.objects.filter(client__profile__isnull=False).delete()
