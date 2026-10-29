"""Rutas do panel do superadmin."""

from django.urls import path

from . import views

app_name = "xestion"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("protectoras/", views.protectoras, name="protectoras"),
    path(
        "protectoras/<int:pk>/<str:accion>/",
        views.cambiar_estado_protectora,
        name="cambiar_estado_protectora",
    ),
]
