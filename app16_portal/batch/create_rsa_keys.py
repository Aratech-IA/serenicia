import os
import sys


# Because this script have to be run in a separate process from manage.py
# you need to set up a Django environnement to use the Class defined in
# the Django models. It is necesssary to interact witht the Django database
# ------------------------------------------------------------------------------
# to get the projet.settings it is necessary to add the parent directory
# to the python path
try:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
except NameError:
    sys.path.append(os.path.abspath('../..'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "projet.settings.settings")
import django

django.setup()

from app16_portal.models import Key

from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend as crypto_default_backend


def generate_keys():
    key = rsa.generate_private_key(
        backend=crypto_default_backend(),
        public_exponent=65537,
        key_size=2048
    )

    private_key = key.private_bytes(
        crypto_serialization.Encoding.PEM,
        crypto_serialization.PrivateFormat.PKCS8,
        crypto_serialization.NoEncryption()
    )

    public_key = key.public_key().public_bytes(
        crypto_serialization.Encoding.OpenSSH,
        crypto_serialization.PublicFormat.OpenSSH
    )

    return private_key, public_key


def create_key(key, is_public):
    key_obj = Key(key=key, is_local=True, is_public=is_public)
    key_obj.save()


def create_rsa_keys():
    if Key.objects.filter(is_local=True).count() == 2:
        print(f'RSA KEYS ALREADY EXISTS')
    else:
        private_key, public_key = generate_keys()
        create_key(private_key, False)
        create_key(public_key, True)
        print(f'RSA KEYS REGISTERED IN DATABASE')


create_rsa_keys()
