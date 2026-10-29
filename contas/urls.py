"""Rutas de contas (entrar, saír, rexistro, recuperar contrasinal)."""

from django.urls import path

from . import views

app_name = "contas"

urlpatterns = [
    path("entrar/", views.Entrar.as_view(), name="entrar"),
    path("sair/", views.Sair.as_view(), name="sair"),
    path("rexistro/", views.rexistro, name="rexistro"),
    path("rexistro/protectora/", views.alta_protectora, name="alta_protectora"),
    path("contrasinal/recuperar/", views.recuperar, name="recuperar"),
    path("contrasinal/enviado/", views.recuperar_enviado, name="recuperar_enviado"),
    path(
        "contrasinal/novo/<uidb64>/<token>/",
        views.recuperar_confirmar,
        name="recuperar_confirmar",
    ),
    path("contrasinal/feito/", views.recuperar_feito, name="recuperar_feito"),
]
