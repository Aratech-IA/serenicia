#!/bin/bash
service cron start
python3 /App/Serenicia/app4_ehpad_base/batch/install_cron.py > /App/log_install_cron-$(date +"%Y_%m_%d_%T").log
#service postfix start
#service opendkim start
#python3 /NNvision/django/app1_base/telegramBot.py &
#python3 /NNvision/django/app1_base/check_client_connection.py &
python3 /App/Serenicia/manage.py migrate > /App/log_migrate-$(date +"%Y_%m_%d_%T").log
python3 /App/Serenicia/manage.py collectstatic --noinput > /App/log_collect_static-$(date +"%Y_%m_%d_%T").log
cd Serenicia && /App/Serenicia/asgi.sh
