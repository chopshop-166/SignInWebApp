FROM tiangolo/meinheld-gunicorn-flask:python3.9

LABEL maintainer="Matt Soucy <first@msoucy.me>"

COPY ./requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

COPY ./signinapp /app
ENV MODULE_NAME signinapp.webapp