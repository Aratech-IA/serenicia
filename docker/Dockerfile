FROM ubuntu:20.04

RUN apt update && apt install -y apt-utils && rm -rf /var/lib/apt/lists/*

# Set the locale
RUN  apt update && apt install locales && locale-gen en_US.UTF-8 && rm -rf /var/lib/apt/lists/*
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

RUN apt update && DEBIAN_FRONTEND=noninteractive apt install -y \
     tzdata wget mlocate build-essential git python3 python3-dev nano cron libpq-dev \
     python3-opencv software-properties-common curl mailutils opendkim opendkim-tools zbar-tools gettext

RUN curl https://bootstrap.pypa.io/pip/3.6/get-pip.py -o get-pip.py && python3 get-pip.py

RUN pip3 install psutil twilio Pillow  django==3.2.13 python-crontab psycopg2 reportlab html2text uvicorn gunicorn certbot \
    django_compressor geopy BeautifulSoup4 websockets docusign-esign  google-api-python-client matplotlib xlsxwriter \
    python-docx PyPDF2 django-filter xhtml2pdf gTTs django-multiselectfield graphviz PyQRCode pyzbar django-libsass \
    django-debug-toolbar django-sass-compiler

WORKDIR /App
COPY docker/ /App/

# postfix, opendkim configuration
RUN chmod +x start.sh &&\
    mv postfix_main.cf /etc/postfix/main.cf &&\
    mv opendkim.conf /etc/opendkim.conf &&\
    mkdir /etc/opendkim && mkdir /etc/opendkim/keys && mv trusted.hosts /etc/opendkim/trusted.hosts &&\
    rm Dockerfile && rm build.sh

# open port 587 in postfix
RUN line='submission inet n       -       y       -       -       smtpd'; sed -i "/^#$line/ c$line" /etc/postfix/master.cf
ADD "https://api.github.com/repos/aratech-IA/serenicia/commits/main" latest_commit
RUN git clone https://github.com/Aratech-IA/Serenicia.git
RUN cd Serenicia && python3 manage.py collectstatic

RUN sed -i  '/config.should_reload:/a  \ \ \ \ \ \ \ \ server.force_exit = True' /usr/local/lib/python3.8/dist-packages/uvicorn/main.py

USER root

CMD ["/App/start.sh"]
