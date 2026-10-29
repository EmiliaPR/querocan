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
    path("usuarios/", views.usuarios, name="usuarios"),
    path("usuarios/<int:pk>/activo/", views.cambiar_activo_usuario, name="cambiar_activo_usuario"),
    path("funil/", views.funil, name="funil"),
    path("contrato/", views.contrato, name="contrato"),
    path("contido/<str:tipo>/", views.contido_lista, name="contido_lista"),
    path("contido/<str:tipo>/novo/", views.contido_editar, name="contido_novo"),
    path("contido/<str:tipo>/<int:pk>/", views.contido_editar, name="contido_editar"),
    path("contido/<str:tipo>/<int:pk>/borrar/", views.contido_borrar, name="contido_borrar"),
]
