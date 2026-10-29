"""Rutas dos cans."""

from django.urls import path

from . import views

app_name = "animais"

urlpatterns = [
    path("animais/", views.listado, name="listado"),
    path("descubrir/", views.deck, name="deck"),
    path("proba-deck/", views.proba_deck, name="proba_deck"),
    path("protectora/cans/", views.protectora_cans, name="protectora_cans"),
]
