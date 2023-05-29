"""
ASGI config for hello_async project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from projet.middelware import mywebsockets

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'projet.settings.settings')

application = get_asgi_application()
application = mywebsockets(application)

        

# using daphne : daphne -e ssl:8443:
    #privateKey=/etc/letsencrypt/live/my.domain.net/privkey.pem:
    #certKey=/etc/letsencrypt/live/my.domain.net/fullchain.pem 
    #project.asgi:channel_layer -p 8000 -b 0.0.0.0