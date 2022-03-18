FROM tiangolo/uwsgi-nginx-flask:python3.10

LABEL maintainer="Matt Soucy <first@msoucy.me>"

COPY ./requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

ENV MODULE_NAME signinapp.webapp
ENV CS_SIGNIN_DB /appdata/signin.db
ENV STATIC_PATH /app/signinapp/static

COPY ./uwsgi.ini /app/uwsgi.ini
COPY ./init-db /app/init-db
COPY ./signinapp /app/signinapp
