#!/bin/bash

set -e

if [ "$ENV" = 'DEV' ]; then
  echo "Running Development Server"
  exec python3 manage.py runserver 0.0.0.0:8000
else
  echo "Running Production Server"
  export DJANGO_SETTINGS_MODULE="mysite.production_settings"
  exec gunicorn mysite.wsgi -b 0.0.0.0:8000
fi