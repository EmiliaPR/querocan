"""Rutas do panel do superadmin."""

from django.urls import path

from . import views

app_name = "xestion"

urlpatterns = [
    path("", views.inicio, name="inicio"),
]
