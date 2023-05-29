"""
Django settings for specific var link to customer.
"""
import os

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', '7keyZtIlfzwXV9VO_OOX1blyjcDXr8Ef6Ycg7mXdbm4')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = (os.getenv('DEBUG', 'True') == 'True')
SEND_MAIL = (os.getenv('SEND_MAIL', 'False') == 'True')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DATABASE_NAME', ''),
        'USER': os.getenv('DATABASE_USER', ''),
        'PASSWORD': os.getenv('DATABASE_PASSWORD', ''),
        'HOST': '10.5.5.200',
        'PORT': '5432',
     }
}

# URL that your MEDIA files will be accessible through the browser.
MEDIA_URL = os.getenv('MEDIA_URL', '/media/')

PUBLIC_SITE = os.getenv('PUBLIC_SITE', '')  # Carefull without the trailing slash !
MAIL_SENDER = os.getenv('MAIL_SENDER', '')

# Ehpad Login
NOM_EHPAD = os.getenv('NOM_EHPAD', '')
IMG_LOGO_NAME = os.getenv('IMG_LOGO_NAME', '')
FACEBOOK = os.getenv('FACEBOOK', '')
SITE_INTERNET = os.getenv('SITE_INTERNET', '')
