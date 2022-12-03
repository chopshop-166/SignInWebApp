# syntax=docker/dockerfile:1

FROM python:3.10-slim

LABEL maintainer="Matt Soucy <first@msoucy.me>"

ENV MODULE_NAME signinapp.webapp
ENV CS_SIGNIN_DB /appdata/signin.db
ENV STATIC_PATH /app/signinapp/static

COPY . /app

RUN apt update && apt install -y --no-install-recommends locales; rm -rf /var/lib/apt/lists/*; sed -i '/^#.* en_US.UTF-8 /s/^#//' /etc/locale.gen; locale-gen

RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

WORKDIR /app

CMD ["gunicorn", "--bind", "0.0.0.0:8100", "--workers", "2", "signinapp:app"]