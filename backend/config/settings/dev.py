"""
Django settings - DEVELOPMENT
"""
from .base import *

# Debug
DEBUG = True

# Allowed hosts
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

# Database
# Используем DATABASE_URL если есть, иначе настройки из base.py
import dj_database_url
db_from_env = dj_database_url.config(conn_max_age=0, ssl_require=False)
if db_from_env:
    DATABASES['default'].update(db_from_env)

# Email - выводить в консоль
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Django Debug Toolbar
INSTALLED_APPS += [
    'debug_toolbar',
    'django_extensions',
]

MIDDLEWARE += [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

INTERNAL_IPS = [
    '127.0.0.1',
]

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
