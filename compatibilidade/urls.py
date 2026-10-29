"""Rutas do test de compatibilidade e da localización."""

from django.urls import path

from . import views

app_name = "compatibilidade"

urlpatterns = [
    path("test/", views.test, name="test"),
    path("test/resultado/", views.resultado, name="resultado"),
    path("localizacion/", views.localizacion, name="localizacion"),
]
