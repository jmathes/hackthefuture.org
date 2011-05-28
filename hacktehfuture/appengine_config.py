"""Configuration."""

import logging
import os

logging.info('Loading %s from %s', __name__, __file__)

# Declare the Django version we need.
from google.appengine.dist import use_library
use_library('django', '1.2')

# Fail early if we can't import Django 1.x.  Log identifying information.
import django
logging.info('django.__file__ = %r, django.VERSION = %r',
             django.__file__, django.VERSION)
assert django.VERSION[0] >= 1, "This Django version is too old"

# Custom Django configuration.
# NOTE: All "main" scripts must import webapp.template before django.
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from django.conf import settings
settings._target = None
