"""Rutas das páxinas públicas de contido."""

from django.urls import path

from . import views

app_name = "contido"

urlpatterns = [
    path("", views.landing, name="landing"),
    path("finais-felices/", views.finais_felices, name="finais_felices"),
    path("enlaces/", views.enlaces, name="enlaces"),
    path("protectoras/", views.protectoras, name="protectoras"),
    path("manual/", views.paxina("manual"), name="manual"),
    path("privacidade/", views.paxina("privacidade"), name="privacidade"),
    path("contacto/", views.paxina("contacto"), name="contacto"),
]
