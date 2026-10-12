"""Isolated tests: no PostgreSQL server or SMTP credentials are required."""

from .settings import *  # noqa: F403

DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
DEFAULT_FROM_EMAIL = 'no-reply@example.com'
DEBUG = False
DEBUG_TOOLBAR_ENABLED = False
INSTALLED_APPS = [app for app in INSTALLED_APPS if app != 'debug_toolbar']
MIDDLEWARE = [middleware for middleware in MIDDLEWARE if not middleware.startswith('debug_toolbar.')]
