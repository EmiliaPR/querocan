"""Punto de entrada WSGI (o que usa Gunicorn en produción)."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "querocan.settings")
application = get_wsgi_application()
