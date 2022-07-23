# syntax=docker/dockerfile:1

FROM python:3.10

LABEL maintainer="Matt Soucy <first@msoucy.me>"

ENV MODULE_NAME signinapp.webapp
ENV CS_SIGNIN_DB /appdata/signin.db
ENV STATIC_PATH /app/signinapp/static

COPY . /app

RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

WORKDIR /app
