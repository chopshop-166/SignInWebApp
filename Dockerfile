# syntax=docker/dockerfile:1

FROM tiangolo/uwsgi-nginx-flask:python3.10

LABEL maintainer="Matt Soucy <first@msoucy.me>"

ENV MODULE_NAME signinapp.webapp
ENV CS_SIGNIN_DB /appdata/signin.db
ENV STATIC_PATH /app/signinapp/static

COPY ./requirements.txt ./ewsgi.ini ./init-db ./signinapp /app/

RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt
