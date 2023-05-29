# How to make the Docker image for the server

## 1 - Clone the repo to have the Dockerfile
    git clone https://github.com/Protecia/djangovision.git
    cd djangogovision/docker

## 2 - Run the docker build with the version you want:
    bash build.sh 3.0

## 3 - Install djangovision
    docker run -it --name first roboticia/nnvision_server:3.0 bash
    git clone https://github.com/Protecia/djangovision.git

## 4 - Give the domain name to postfix
     echo "serenicia.net" > /etc/mailname

If postfix is not working correctly, you can enable log system for the mail :
    
    apt install rsyslog
    nano /etc/rsyslog.conf

Comment the line :

    #module(load="imklog" permitnonkernelfacility="on")
Start the logging system :

    service rsyslogstart

Now you have the mail log in /var/log/mail.log
Enabled the log only if there is a problem because it is a huge file.

## 5 - Install opendkim
You need to generate the keys if not already in a volume.
See opendkim.conf and documentation to know how to proceed.


## 6 - Make starting script
First you should enabled the right configuration for apache : 
    
    service apache2 start
    bash ssl-serenicia.sh
    a2ensite serenicia-ssl-dev
    service apache2 reload

You need to adapt the start.sh script with your needs. For example:

    #!/bin/bash
    service postgresql start
    sleep 5
    service cron start
    #service postfix start
    #service opendkim start
    service apache2 start
    #python3 /NNvision/django/app1_base/telegramBot.py &
    #python3 /NNvision/django/app1_base/check_client_connection.py &
    cd django && /NNvision/django/asgi.sh

Copie the asgi script and adapt to your needs, dev or prod.

    cd djangovision
    cp asgi_base.sh asgi.sh
For example:

    #!/bin/bash
    
    # daphne doesn't work with websockets so do not use
    #daphne -b 0.0.0.0 -p 80 projet.asgi:application
    #daphne -b 0.0.0.0 -e ssl:443:privateKey=/etc/letsencrypt/live/dev.serenicia.fr/privkey.pem:certKey=/etc/letsencrypt/live/dev.serenicia.fr/cert.pem projet.asgi:appli>
    
    # uvicorn is good for developpement environnement with --reload
    uvicorn --ssl-keyfile /etc/letsencrypt/live/dev.serenicia.fr/privkey.pem \
            --ssl-certfile /etc/letsencrypt/live/dev.serenicia.fr/fullchain.pem \
            --ws  auto --host 0.0.0.0 --port 443 --reload projet.asgi:application
    
    # gunicorn is suitable for production with process management
    #gunicorn  --keyfile=/etc/letsencrypt/live/prod.serenicia.fr/privkey.pem \
    #          --certfile=/etc/letsencrypt/live/prod.serenicia.fr/fullchain.pem \
    #          -b 0.0.0.0:443 \
    #          -w 4 -k uvicorn.workers.UvicornWorker projet.asgi:application

Make you script executable.

    chmod +x ./start.sh
    chmod +x  djangovision/asgi.sh
### eventually there is a hack to restart automatically the server on code change.
It can be useful on the dev server. 

Allow auto reload in Uvicorn : uvicorn/main.py
https://github.com/encode/uvicorn/issues/675

here the code to force reload line 552 of uvicorn/main.py

    if config.should_reload:
        server.force_exit = True
        sock = config.bind_socket()
        ChangeReload(config, target=server.run, sockets=[sock]).run()

Commit to save your changes :

    docker commit first roboticia/nnvision_server:3.0


## 7 - Use the script in start folder to start correctly the server
    cp start/run_nnvision_server_protecia.sh ~/start.sh

## 8 - Update djangovision
    python3 manage.py makemigrations
    python3 manage.py migrate
    python3 manage.py collectstatic

