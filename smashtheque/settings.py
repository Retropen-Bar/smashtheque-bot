import os

SECRET_KEY = os.environ['DJANGO_SECRET_KEY']

DATABASES = {
  'default': {
    'ENGINE': 'django.db.backends.postgresql',
    'HOST': os.environ['DATABASE_HOST'],
    'PORT': os.environ['DATABASE_PORT'],
    'NAME': os.environ['DATABASE_NAME'],
    'USER': os.environ['DATABASE_USER'],
    'PASSWORD': os.environ['DATABASE_PASSWORD'],
  }
}

INSTALLED_APPS = [
  'smashtheque.apps.SmashthequeConfig',
]

DEBUG = True
