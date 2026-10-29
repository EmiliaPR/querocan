"""Rutas dos cans."""

from django.urls import path

from . import views

app_name = "animais"

urlpatterns = [
    path("descubrir/", views.deck, name="deck"),
    path("protectora/cans/", views.protectora_cans, name="protectora_cans"),
]
