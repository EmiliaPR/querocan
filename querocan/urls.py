"""Rutas principais de QueroCan. Cada app define as súas no seu propio urls.py."""

from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

from . import views

urlpatterns = [
    path("saude/", views.saude, name="saude"),
    path("", include("contido.urls")),
]

# En desenvolvemento Django serve as fotos subidas; en produción faino Caddy
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
