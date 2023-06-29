import glob
import json
import mimetypes
import os
from datetime import datetime, date, timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User
from django.core import serializers
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.storage import default_storage
from django.core.files.uploadhandler import MemoryFileUploadHandler
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import render, redirect

from app10_social_activities.views import get_activity_path_and_url
from app4_ehpad_base.api_ws_reco import create_thumbnail, rotation_image
from app4_ehpad_base.forms import CreatePostForm, FilterBlog
from app4_ehpad_base.models import BlogPost, BlogImage
from app15_calendar.models import PlanningEvent


def get_type_of_file(filename):
    type_of_file = mimetypes.guess_type(filename)[0]
    return type_of_file.split('/')[0]


@login_required
@permission_required('app0_access.view_blog')
def create_or_edit_post(request):
    try:
        request.session.pop('resident_id')
    except KeyError:
        pass
    today = date.today()
    article = BlogPost.objects.all().order_by('-created_on')
    paginator = Paginator(article, 25)  # Show 25 articles per pages
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {'data': page_obj, 'today': today}
    return render(request, 'app4_ehpad_base/public_photo.html', context)


def show_post(request, post_id):
    post = BlogPost.objects.get(pk=post_id)
    images = post.images.all()
    file = False
    if post.files:
        file = settings.MEDIA_URL + 'blog_doc/' + post.files.path.split('/')[-1]
        file = {'file': file, 'type_of_file': get_type_of_file(file), 'extension_of_file': file.split('.')[-1]}
    img_list = [{'url': settings.MEDIA_URL + img.image_blog,
                 'url_full': settings.MEDIA_URL + (img.image_blog.split('/thumbnails', 1)[0] +
                                                   img.image_blog.split('/thumbnails', 1)[1])} for img in images]
    context = {'post': post, 'img_list': img_list, 'file': file}
    return render(request, 'app4_ehpad_base/post.html', context)


def save_file_to_media(file, directory):
    file_path = directory + '/' + file.name
    thumb_full_path = default_storage.location + '/' + directory + '/thumbnails/'
    Path(thumb_full_path).mkdir(exist_ok=True, parents=True)
    with default_storage.open(file_path, 'wb') as destination:
        for chunk in file.chunks():
            destination.write(chunk)
    rotation_image(path_file=default_storage.path(file_path))
    create_thumbnail(path_file=default_storage.path(file_path), path_thumb=thumb_full_path)
    return directory + '/thumbnails/' + file.name


@login_required
def create_post(request, act_id=0):
    if request.method == 'POST':
        form = CreatePostForm(request.POST, request.FILES)
        if form.is_valid():
            title = form.cleaned_data['title']
            content = form.cleaned_data['content']
            category = form.cleaned_data['category']
            is_public = form.cleaned_data['is_public']
            files = form.cleaned_data['files']
            created_on = date.today()
            author = User.objects.get(pk=request.user.id)
            insert_article = BlogPost.objects.create(title=title, content=content, category=category,
                                                     is_public=is_public, files=files, created_on=created_on,
                                                     author=author)
            # if request.FILES:
            #     BlogPost.objects.filter(pk=insert_article.id).update(files=request.FILES['file'])
            #           add images to blogimage DB
            list_img = [img.split(settings.MEDIA_URL)[1] for img in request.POST.getlist('pics_list')]
            list_img = [BlogImage.objects.create(image_blog=img) for img in list_img]
            for img in request.FILES.getlist('from_device'):
                img_url = save_file_to_media(img, f'blog_doc/images/{insert_article.id}')
                list_img.append(BlogImage.objects.create(image_blog=img_url))
            insert_article.images.add(*list_img)
            cover = insert_article.images.first()
            if act_id:
                activity = PlanningEvent.objects.get(id=act_id)
                activity.blog_post = insert_article
                activity.save()
                try:
                    cover = BlogImage.objects.get(image=activity.thumbnail_url)
                except ObjectDoesNotExist:
                    pass
            # if not cover:
            #     cover = \
            #     BlogImage.objects.get_or_create(image=f'{settings.STATIC_URL}app4_ehpad_base/img/{category}.jpg')[0]
            BlogPost.objects.filter(id=insert_article.id).update(cover=cover)
            return redirect('public_photo')
    context = {'tinymce_key': settings.TINYMCE_KEY, 'act_id': act_id, 'new_post': True}
    if act_id:
        activity = PlanningEvent.objects.get(id=act_id)
        path, url = get_activity_path_and_url(activity)
        path += '/thumbnails/'
        url += 'thumbnails/'
        form = CreatePostForm(initial={'title': activity.event.type, 'category': 'activities'})
        context['check_all'] = True
    else:
        path = f'{settings.MEDIA_ROOT}/common/thumbnails/'
        url = f'{settings.MEDIA_URL}common/thumbnails/'
        form = CreatePostForm()
    context['list_pictures'] = [url + path_picture.split('/')[-1]
                                for path_picture in glob.glob(path + '*.*', recursive=False)]
    context['form'] = form
    return render(request, 'app4_ehpad_base/create_post.html', context)


@login_required
def edit_post(request, post_id):
    try:
        post = BlogPost.objects.get(pk=post_id)
    except ObjectDoesNotExist:
        return redirect('public_photo')
    
    if request.method == 'POST':
        if request.FILES.get('files') or request.POST.get('files-clear'):
            post.files.delete()
        form = CreatePostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            list_img = [BlogImage.objects.create(image=img) for img in request.POST.getlist('pics_list')]
            for img in request.FILES.getlist('from_device'):
                img_url = save_file_to_media(img, f'blog_doc/images/{post.id}')
                list_img.append(BlogImage.objects.create(image=img_url))
            post.images.add(*list_img)
            post = BlogPost.objects.get(pk=post_id)
            return redirect('public_photo')
    form = CreatePostForm(instance=post)
    tinymce_key = settings.TINYMCE_KEY
    path = f'{settings.MEDIA_ROOT}/common/thumbnails/'
    list_pictures = [settings.MEDIA_URL + 'common/thumbnails/' + path_picture.split('/')[-1]
                     for path_picture in glob.glob(path + '*.*', recursive=False)]
    pictures_already_put = [img for img in post.images.all()]
    context = {'form': form, 'tinymce_key': tinymce_key, 'post_name': post.title, 'post_id': post.id,
               'list_pictures': list_pictures, 'pictures_already_put': pictures_already_put}
    return render(request, 'app4_ehpad_base/create_post.html', context)


@login_required
def delete_post(request, post_id):
    post = BlogPost.objects.get(pk=post_id)
    post.delete()
    return redirect('public_photo')


@login_required
def delete_picture(request, picture_id):
    picture = BlogImage.objects.get(id=picture_id)
    post_id = BlogPost.objects.get(images=picture).id
    picture.delete()
    return redirect('edit_post', post_id=post_id)


# def show_blog(request):
#     test = FilterBlog()
#     today = date.today()
#     start_week = today - timedelta(today.weekday())
#     end_week = start_week + timedelta(weeks=1)
#     week = 0
#     articles = BlogPost.objects.filter(created_on__range=[start_week, end_week])
#     if request.POST:
#         if request.POST.get('created_on') and request.POST.get('category'):
#             articles = BlogPost.objects.filter(created_on=request.POST.get('created_on'),
#                                                category=request.POST.get('category'))
#         elif request.POST.get('created_on'):
#             articles = BlogPost.objects.filter(created_on=request.POST.get('created_on'))
#         elif request.POST.get('category'):
#             articles = BlogPost.objects.filter(category=request.POST.get('category'))
#         elif request.POST.get('next'):
#             week = int(request.POST.get('next')) + 1
#             today += timedelta(weeks=week)
#             start_week = today - timedelta(today.weekday())
#             end_week = start_week + timedelta(weeks=1)
#             articles = BlogPost.objects.filter(created_on__range=[start_week, end_week])
#         elif request.POST.get('previous'):
#             week = int(request.POST.get('previous')) - 1
#             today += timedelta(weeks=week)
#             start_week = today - timedelta(today.weekday())
#             end_week = start_week + timedelta(weeks=1)
#             articles = BlogPost.objects.filter(created_on__range=[start_week, end_week])
#     if request.user.is_authenticated:
#         articles = articles.order_by('-created_on')
#     else:
#         articles = articles.filter(is_public=True).order_by('-created_on')
#     context = {'today': today, 'articles': articles, 'filters': test, 'week': week}
#     return render(request, 'app4_ehpad_base/blog.html', context)


def show_blog(request):
    try:
        request.session.pop('resident_id')
    except KeyError:
        pass
    test = FilterBlog()
    if request.POST:
        articles = BlogPost.objects.all()
        if request.POST.get('created_on') and request.POST.get('category'):
            articles = BlogPost.objects.filter(created_on=request.POST.get('created_on'),
                                               category=request.POST.get('category'))
        if request.POST.get('created_on'):
            articles = BlogPost.objects.filter(created_on=request.POST.get('created_on'))
        elif request.POST.get('category'):
            articles = BlogPost.objects.filter(category=request.POST.get('category'))
    else:
        articles = BlogPost.objects.all()
    if request.user.is_authenticated:
        articles = articles.order_by('-created_on')
    else:
        articles = articles.filter(is_public=True).order_by('-created_on')
    today = date.today()
    paginator = Paginator(articles, 9)  # Show 9 articles per pages
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {'today': today, 'page_obj': page_obj, 'filters': test}
    return render(request, 'app4_ehpad_base/blog.html', context)


def show_post_image(request):
    if request.POST:
        img = request.POST.get('full_url')
        post_id = request.POST.get('post_id')
    context = {'img': img, 'post_id': post_id}
    return render(request, 'app4_ehpad_base/show_post_image.html', context)


def get_api_blog(request):
    articles = serializers.serialize("json", BlogPost.objects.all().order_by('-created_on')[:10])
    return HttpResponse(articles)
