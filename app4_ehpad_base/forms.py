import re
from datetime import datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.functions import Lower

from app4_ehpad_base.models import Meal, Entree, \
    MainDish, Accompaniment, Dessert, Pic, ProfileSerenicia, BlogPost, Photos, MealBooking, \
    MealPresentation, EmptyRoomCleaned
from app15_calendar.models import PlanningEvent
from app1_base.models import SubSector, Sector, Profile
from django import forms
from django.utils.translation import gettext_lazy as _
from PIL import Image

from .api_ws_reco import create_thumbnail, rotation_image
from .models import AdministrativeDocument, Card, PreferencesSerenicia


class SocialPlanningEventsForm(forms.ModelForm):
    DURATION_CHOICES = (
        (30, '30 min'),
        (60, _('one hour')),
        (120, _('two hours')),
        (180, _('Three hours')),
        (240, _('Four hours')),
        (360, _('Six hours')),
        (720, _('All the day'))
    )
    event_duration = forms.ChoiceField(choices=DURATION_CHOICES,
                                       widget=forms.Select(attrs={'class': 'bootstrap-select text-center w-100'}))
    type = forms.CharField(max_length=100, required=True)

    class Meta:
        model = PlanningEvent
        fields = ['start', 'event_comment']
        widgets = {
            'start': forms.DateTimeInput(attrs={'class': 'id_event_date text-center w-100',
                                                'id': 'event_date',
                                                'readonly': 'true'}),
            'event_comment': forms.TextInput(attrs={'class': 'form-control', 'cols': 3, 'required': False})
        }

    def save(self, **kwargs):
        instance = super(SocialPlanningEventsForm, self).save(commit=kwargs['commit'])
        instance.start = self.cleaned_data['start']
        instance.end = instance.start + timedelta(minutes=int(self.cleaned_data['event_duration']))
        instance.event_comment = self.cleaned_data.get('event_comment')
        return instance, self.cleaned_data.get('type')


class SectorSelector(forms.Form):
    filter = forms.ModelChoiceField(queryset=SubSector.objects.all(), empty_label=_('All'), required=False, label='',
                                    widget=forms.Select(attrs={"onchange": 'this.form.submit()',
                                                               "class": 'btn btn-perso'}))


class Sector2Selector(forms.Form):
    filtersector = forms.ModelChoiceField(queryset=Sector.objects.all(), empty_label=_('All'), required=False, label='',
                                          widget=forms.Select(attrs={"onchange": 'this.form.submit()',
                                                                     "class": 'btn btn-perso'}))


class NewMenuForm(forms.ModelForm):
    date = forms.DateField(input_formats=['%Y-%m-%d', '%d/%m/%Y'], label="",
                           widget=forms.DateInput(attrs={'class': 'text-center', 'type': 'date'}))
    entree = forms.ModelChoiceField(Entree.objects.filter(active=True).order_by(Lower('name')), required=False,
                                    widget=forms.Select(attrs={'class': 'text-center'}), label=_('Entree'))
    main_dish = forms.ModelChoiceField(MainDish.objects.filter(active=True).order_by(Lower('name')), required=False,
                                       widget=forms.Select(attrs={'class': 'text-center'}), label=_('Main dish'))
    dessert = forms.ModelChoiceField(Dessert.objects.filter(active=True).order_by(Lower('name')), required=False,
                                     widget=forms.Select(attrs={'class': 'text-center'}), label=_('Dessert'))
    accompaniment = forms.ModelChoiceField(Accompaniment.objects.filter(active=True).order_by(Lower('name')),
                                           required=False, widget=forms.Select(attrs={'class': 'text-center'}),
                                           label=_('Accompaniment'))

    class Meta:
        model = Meal
        fields = ['date', 'type', 'substitution', 'entree', 'main_dish',
                  'accompaniment', 'dessert', 'dry_cheese', 'cottage_cheese', 'comment']
        labels = {
            'type': _('Menu'),
            'dry_cheese': _('Dry cheese'),
            'cottage_cheese': _('Cottage cheese'),
            'comment': '',
            'substitution': _('Substitution menu')
        }
        widgets = {
            'comment': forms.Textarea(attrs={'placeholder': _('Write your comments here'),
                                             'style': 'min-width: 150px; max-width: 300px; max-height: 150px;'}),
            'type': forms.Select(attrs={'class': 'text-center'})
        }

    def save(self, commit=True):
        instance = super(NewMenuForm, self).save(commit=False)
        if not instance.main_dish and not instance.accompaniment and not instance.dessert and not instance.entree:
            return None
        else:
            instance.save()
            return instance


def float_to_cent(price):
    return int(round(price * 100))


class NewEntreeForm(forms.ModelForm):
    id = forms.CharField(widget=forms.HiddenInput, required=False)
    price_cents = forms.FloatField(required=False, min_value=0.00, initial=0.00, label=_('Price'),
                                   widget=forms.NumberInput(attrs={'step': '0.01'}))
    name = forms.CharField(required=False, label=_('Name'))

    def __init__(self, *args, **kwargs):
        super(NewEntreeForm, self).__init__(*args, **kwargs)
        if kwargs.get('instance'):
            self.initial['price_cents'] = float(kwargs['instance'].price_cents / 100)

    class Meta:
        model = Entree
        fields = ['name', 'price_cents', 'id']

    def save(self):
        if self.cleaned_data.get('id'):
            entree = Entree.objects.get(id=self.cleaned_data.get('id'))
            if entree.id != int(self.cleaned_data.get('id')):
                exist = _('already exist')
                return {'message': f'{entree.name} {exist}', 'category': _('Error')}
            else:
                price_cents = float_to_cent(self.cleaned_data.get('price_cents'))
                Entree.objects.filter(id=self.cleaned_data.get('id')).update(name=self.cleaned_data.get('name'),
                                                                             price_cents=price_cents)
                updated = _('updated')
                return {'message': f'{entree.name} {updated}', 'category': _('Success')}
        elif self.cleaned_data.get('name'):
            try:
                entree = Entree.objects.get(name=self.cleaned_data.get('name'))
                entree.active = True
            except ObjectDoesNotExist:
                entree, is_created = Entree.objects.get_or_create(name=self.cleaned_data.get('name'))
                if not is_created:
                    entree.active = True
                entree.price_cents = float_to_cent(self.cleaned_data.get('price_cents'))
            entree.save()
            added = _('has been added to the list')
            return {'message': f'{entree.name} {added}', 'category': _('Success')}


class NewMainDishForm(forms.ModelForm):
    id = forms.CharField(widget=forms.HiddenInput, required=False)
    price_cents = forms.FloatField(required=False, min_value=0.00, initial=0.00, label=_('Price'),
                                   widget=forms.NumberInput(attrs={'step': '0.01'}))
    name = forms.CharField(required=False, label=_('Name'))

    def __init__(self, *args, **kwargs):
        super(NewMainDishForm, self).__init__(*args, **kwargs)
        if kwargs.get('instance'):
            self.initial['price_cents'] = float(kwargs['instance'].price_cents / 100)

    class Meta:
        model = MainDish
        fields = ['name', 'price_cents', 'id']

    def save(self):
        if self.cleaned_data.get('id'):
            meal = MainDish.objects.get(id=self.cleaned_data.get('id'))
            if meal.id != int(self.cleaned_data.get('id')):
                exist = _('already exist')
                return {'message': f'{meal.name} {exist}', 'category': _('Error')}
            else:
                price_cents = float_to_cent(self.cleaned_data.get('price_cents'))
                MainDish.objects.filter(id=self.cleaned_data.get('id')).update(name=self.cleaned_data.get('name'),
                                                                               price_cents=price_cents)
                updated = _('updated')
                return {'message': f'{meal.name} {updated}', 'category': _('Success')}
        elif self.cleaned_data.get('name'):
            try:
                meal = MainDish.objects.get(name=self.cleaned_data.get('name'))
                meal.active = True
            except ObjectDoesNotExist:
                meal, is_created = MainDish.objects.get_or_create(name=self.cleaned_data.get('name'))
                if not is_created:
                    meal.active = True
                meal.price_cents = float_to_cent(self.cleaned_data.get('price_cents'))
            meal.save()
            added = _('has been added to the list')
            return {'message': f'{meal.name} {added}', 'category': _('Success')}


class NewDessertForm(forms.ModelForm):
    id = forms.CharField(widget=forms.HiddenInput, required=False)
    price_cents = forms.FloatField(required=False, min_value=0.00, initial=0.00, label=_('Price'),
                                   widget=forms.NumberInput(attrs={'step': '0.01'}))
    name = forms.CharField(required=False, label=_('Name'))

    def __init__(self, *args, **kwargs):
        super(NewDessertForm, self).__init__(*args, **kwargs)
        if kwargs.get('instance'):
            self.initial['price_cents'] = float(kwargs['instance'].price_cents / 100)

    class Meta:
        model = Dessert
        fields = ['name', 'price_cents', 'id']

    def save(self):
        if self.cleaned_data.get('id'):
            dessert = Dessert.objects.get(id=self.cleaned_data.get('id'))
            if dessert.id != int(self.cleaned_data.get('id')):
                exist = _('already exist')
                return {'message': f'{dessert.name} {exist}', 'category': _('Error')}
            else:
                price_cents = float_to_cent(self.cleaned_data.get('price_cents'))
                Dessert.objects.filter(id=self.cleaned_data.get('id')).update(name=self.cleaned_data.get('name'),
                                                                              price_cents=price_cents)
                updated = _('updated')
                return {'message': f'{dessert.name} {updated}', 'category': _('Success')}
        elif self.cleaned_data.get('name'):
            try:
                dessert = Dessert.objects.get(name=self.cleaned_data.get('name'))
                dessert.active = True
            except ObjectDoesNotExist:
                dessert, is_created = Dessert.objects.get_or_create(name=self.cleaned_data.get('name'))
                if not is_created:
                    dessert.active = True
                dessert.price_cents = float_to_cent(self.cleaned_data.get('price_cents'))
            dessert.save()
            added = _('has been added to the list')
            return {'message': f'{dessert.name} {added}', 'category': _('Success')}


class NewAccompanimentForm(forms.ModelForm):
    id = forms.CharField(widget=forms.HiddenInput, required=False)
    price_cents = forms.FloatField(required=False, min_value=0.00, initial=0.00, label=_('Price'),
                                   widget=forms.NumberInput(attrs={'step': '0.01'}))
    name = forms.CharField(required=False, label=_('Name'))

    def __init__(self, *args, **kwargs):
        super(NewAccompanimentForm, self).__init__(*args, **kwargs)
        if kwargs.get('instance'):
            self.initial['price_cents'] = float(kwargs['instance'].price_cents / 100)

    class Meta:
        model = Accompaniment
        fields = ['name', 'price_cents', 'id']

    def save(self):
        if self.cleaned_data.get('id'):
            acc = Accompaniment.objects.get(id=self.cleaned_data.get('id'))
            if acc.id != int(self.cleaned_data.get('id')):
                exist = _('already exist')
                return {'message': f'{acc.name} {exist}', 'category': _('Error')}
            else:
                price_cents = float_to_cent(self.cleaned_data.get('price_cents'))
                Accompaniment.objects.filter(id=self.cleaned_data.get('id')).update(name=self.cleaned_data.get('name'),
                                                                                    price_cents=price_cents)
                updated = _('updated')
                return {'message': f'{acc.name} {updated}', 'category': _('Success')}
        elif self.cleaned_data.get('name'):
            try:
                acc = Accompaniment.objects.get(name=self.cleaned_data.get('name'))
                acc.active = True
            except ObjectDoesNotExist:
                acc, is_created = Accompaniment.objects.get_or_create(name=self.cleaned_data.get('name'))
                if not is_created:
                    acc.active = True
                acc.price_cents = float_to_cent(self.cleaned_data.get('price_cents'))
            acc.save()
            added = _('has been added to the list')
            return {'message': f'{acc.name} {added}', 'category': _('Success')}


class PhotoForm(forms.ModelForm):
    # resident = models.ForeignKey(User, on_delete=models.CASCADE)
    x = forms.FloatField(widget=forms.HiddenInput())
    y = forms.FloatField(widget=forms.HiddenInput())
    width = forms.FloatField(widget=forms.HiddenInput())
    height = forms.FloatField(widget=forms.HiddenInput())

    class Meta:
        model = Pic
        fields = ('file', 'x', 'y', 'width', 'height',)

    # def residents_user(self, client):
    #     listuser = User.objects.filter(profile__client=client)
    #     for user in listuser:
    #         if user.groups.filter(name='resident').exists():
    #             return user

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        super(PhotoForm, self).__init__(*args, **kwargs)
        # client = Client.objects.get(pk=self.request.session['client'])
        # self.fields['resident'] = self.residents_user(client)
        self.fields['resident'] = User.objects.get(pk=self.request.session['resident_id'])

    def save(self):
        photo = super(PhotoForm, self).save()

        x = self.cleaned_data.get('x')
        y = self.cleaned_data.get('y')
        w = self.cleaned_data.get('width')
        h = self.cleaned_data.get('height')

        image = Image.open(photo.file)
        cropped_image = image.crop((x, y, w + x, h + y))
        resized_image = cropped_image.resize((200, 200), Image.ANTIALIAS)
        resized_image.save(photo.file.path)

        return photo


class AddDocuments(forms.ModelForm):
    class Meta:
        model = AdministrativeDocument
        fields = "__all__"


class AddCard(forms.ModelForm):
    class Meta:
        model = Card
        fields = "__all__"


def create_username(first_name, last_name):
    # lower all char and delete unnecessary whitespace
    username = first_name.lower().strip() + "." + last_name.lower().strip()
    # replace multiple whitespace by one
    username = re.sub('\s+', ' ', username)
    # replace whitespace by '-'
    username = re.sub('\s+', '-', username)
    # replace multiple '-' by one
    username = re.sub('-+', '-', username)
    return username


class NewAccount(forms.ModelForm):
    username = forms.CharField(widget=forms.HiddenInput(), required=False)
    password = forms.CharField(widget=forms.HiddenInput(), required=False)
    created_by = forms.CharField(widget=forms.HiddenInput(), required=False)
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)
    email = forms.CharField(required=True)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'username', 'password', 'created_by']

    def save(self):
        tmp_username = create_username(self.cleaned_data.get('first_name'), self.cleaned_data.get('last_name'))
        user, is_created = User.objects.get_or_create(username=tmp_username)
        if not is_created:
            return user, is_created
        user.set_password(user.username)
        user.first_name = self.cleaned_data.get('first_name')
        user.last_name = self.cleaned_data.get('last_name')
        user.email = self.cleaned_data.get('email')
        user.save()
        Profile.objects.create(user=user, created_by=self.cleaned_data.get('created_by'))
        ProfileSerenicia.objects.create(user=user)
        return user, is_created


class UploadPhotos(forms.Form):
    images = forms.ImageField(widget=forms.ClearableFileInput(attrs={'multiple': True}))


class PhotoFromStaff(forms.Form):
    photo_from_staff = forms.ImageField(widget=forms.ClearableFileInput(attrs={'class': 'd-none',
                                                                               'onchange': 'this.form.submit()'}))
    folder = forms.CharField(widget=forms.HiddenInput())

    def save(self):
        file = self.cleaned_data.get('photo_from_staff')
        res_folder_path = settings.MEDIA_ROOT + '/residents/' + self.cleaned_data.get('folder') + '/'
        Path(res_folder_path).mkdir(exist_ok=True, parents=True)
        file_dest = res_folder_path + datetime.now().date().strftime('%Y-%m-%d') + '_' + file.name
        with open(file_dest, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
        rotation_image(file_dest)
        create_thumbnail(file_dest, f'{res_folder_path}/thumbnails/')


class PhotoFromStaffSensitive(forms.Form):
    photo_sensitive = forms.ImageField(widget=forms.ClearableFileInput(attrs={'class': 'd-none',
                                                                              'onchange': 'this.form.submit()'}))
    folder = forms.CharField(widget=forms.HiddenInput())

    def save(self):
        file = self.cleaned_data.get('photo_sensitive')
        res_folder_path = settings.MEDIA_ROOT + '/residents/' + self.cleaned_data.get('folder') + '/'
        Path(res_folder_path).mkdir(exist_ok=True, parents=True)
        file_dest = res_folder_path + datetime.now().date().strftime('%Y-%m-%d') + '_sensitive_' + file.name
        with open(file_dest, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
        rotation_image(file_dest)
        create_thumbnail(file_dest, f'{res_folder_path}/thumbnails/')


class CreatePostForm(forms.ModelForm):
    title = forms.CharField(label=_('Title'), max_length=150)
    content = forms.CharField(label=_('Content'), widget=forms.Textarea, required=False)
    files = forms.FileField(widget=forms.ClearableFileInput(attrs={'class': 'd-none', 'id': 'files__pdf'}),
                            required=False)
    from_device = forms.ImageField(widget=forms.ClearableFileInput(attrs={'class': 'd-none', 'id': 'from_device',
                                                                          'multiple': True}),
                                   required=False)

    class Meta:
        model = BlogPost
        fields = ["title", "content", "category", "is_public", "files"]
        help_texts = {'is_public': _('Uncheck if this post should not be visible by families'), }
        labels = {'is_public': _('is public'), 'category': _('Category')}


class FilterBlog(forms.ModelForm):
    created_on = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))

    class Meta:
        model = BlogPost
        fields = ["category", "created_on"]
        labels = {'category': _('Category'), 'created_on': _('Created the')}


class PublicPhoto(forms.ModelForm):
    file = forms.ImageField(widget=forms.ClearableFileInput(attrs={'class': 'd-none',
                                                                   'onchange': 'this.form.submit()',
                                                                   'id': 'public_photo_nav_btn'}))

    class Meta:
        model = Photos
        fields = ['file']


class BookingGroupForm(forms.ModelForm):
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'text-center'}))
    lunch = forms.BooleanField(widget=forms.CheckboxInput(attrs={'class': 'btn-check'}), required=False)
    dinner = forms.BooleanField(widget=forms.CheckboxInput(attrs={'class': 'btn-check'}), required=False)
    other_guests = forms.IntegerField(widget=forms.NumberInput(attrs={'min': 1, 'value': 1}))

    class Meta:
        model = MealBooking
        fields = ['date', 'lunch', 'dinner', 'other_guests']


class PhotoMealPresentation(forms.ModelForm):
    photo = forms.ImageField(widget=forms.ClearableFileInput(attrs={'class': 'd-none',
                                                                    'onchange': 'this.form.submit()'}), label='')

    class Meta:
        model = MealPresentation
        fields = ['photo', 'item', 'meal', 'presentation']
        widgets = {'item': forms.HiddenInput(), 'meal': forms.HiddenInput(), 'presentation': forms.HiddenInput()}


class PreferencesSereniciaForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(PreferencesSereniciaForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            if visible.field.widget.input_type == 'checkbox':
                visible.field.widget.attrs['class'] = 'form-check-input'

    class Meta:
        model = PreferencesSerenicia
        exclude = ['profile']


class EmptyRoomCleanedForm(forms.ModelForm):

    class Meta:
        model = EmptyRoomCleaned
        exclude = ['client']
