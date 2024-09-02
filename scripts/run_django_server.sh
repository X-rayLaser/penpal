#!/bin/bash

set -e

if [ "$ENV" = 'DEV' ]; then
  echo "Running Development Server"
  exec python3 -u manage.py runserver 0.0.0.0:8000
elif [ "$ENV" = 'TEST' ]; then
  echo "Running Test Server"
  export DJANGO_SETTINGS_MODULE="mysite.test_settings"
  if [ -e /data/test_db.sqlite3 ]; then
    rm /data/test_db.sqlite3
    echo "Deleted existing test database file"
  fi
  python3 manage.py migrate
  exec python3 manage.py runserver 0.0.0.0:8000
else
  echo "Running Production Server"
  export DJANGO_SETTINGS_MODULE="mysite.production_settings"
  exec gunicorn mysite.wsgi -b 0.0.0.0:8000
fi