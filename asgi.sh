#!/bin/bash

# daphne doesn't work with websockets so do not use
#daphne -b 0.0.0.0 -p 80 projet.asgi:application
#daphne -b 0.0.0.0 -e ssl:443:privateKey=/etc/letsencrypt/live/dev.serenicia.fr/privkey.pem:certKey=/etc/letsencrypt/live/dev.serenicia.fr/cert.pem projet.asgi:application

# uvicorn is good for developpement environnement with --reload
uvicorn --ws auto  --host 0.0.0.0 --port 9090 --reload projet.asgi:application

# gunicorn is suitable for production with process management
#gunicorn  -b 0.0.0.0:9090 -w 4 -k uvicorn.workers.UvicornWorker projet.asgi:application