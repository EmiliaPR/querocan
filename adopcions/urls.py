"""Rutas do fluxo de adopción."""

from django.urls import path

from . import views_adoptante, views_protectora

app_name = "adopcions"

urlpatterns = [
    path("solicitar/<int:pk>/", views_adoptante.solicitar, name="solicitar"),
    path("solicitar/continuar/", views_adoptante.continuar, name="continuar"),
    path("solicitudes/", views_adoptante.minas_solicitudes, name="minas_solicitudes"),
    path("protectora/solicitudes/", views_protectora.solicitudes, name="protectora_solicitudes"),
]
