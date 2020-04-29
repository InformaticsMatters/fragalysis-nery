FROM python:3.8.2-alpine3.11

# Labels
LABEL maintainer='Alan Christie <achristie@informaticsmatters.com>'

# Force the binary layer of the stdout and stderr streams
# to be unbuffered
ENV PYTHONUNBUFFERED 1

# Base directory for the application
# Also used for user directory
ENV APP_ROOT /home/nery

# Containers should NOT run as root
# (as good practice)
# Also, add Alpine build tools, like gcc, ffi
# (needed for some of our requirements)
RUN adduser -D -h ${APP_ROOT} -s /bin/sh nery && \
    chown -R nery.nery ${APP_ROOT} && \
    apk add --no-cache openssl-dev libffi-dev build-base

COPY requirements.txt ${APP_ROOT}/
RUN /usr/local/bin/python -m pip install --upgrade pip && \
    pip install -r ${APP_ROOT}/requirements.txt

COPY nery.py ${APP_ROOT}/
COPY logging.yaml ${APP_ROOT}/
COPY wsgi.py ${APP_ROOT}/

USER nery
ENV HOME ${APP_ROOT}
WORKDIR ${APP_ROOT}

CMD gunicorn --workers 1 \
             --timeout 30 \
             --bind 0.0.0.0:8080 \
             wsgi:APP
