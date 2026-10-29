"""Rutas das páxinas públicas de contido."""

from django.urls import path

from . import views

app_name = "contido"

urlpatterns = [
    path("", views.landing, name="landing"),
]
