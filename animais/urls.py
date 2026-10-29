"""Rutas dos cans: públicas, do adoptante (deck) e da protectora."""

from django.urls import path

from . import api, views, views_protectora

app_name = "animais"

urlpatterns = [
    path("animais/", views.listado, name="listado"),
    path("animais/<int:pk>/", views.ficha, name="ficha"),
    path("descubrir/", views.deck, name="deck"),
    path("api/deck/", api.tanda, name="api_deck"),
    path("api/deck/decision/", api.decision, name="api_decision"),
    path("api/deck/desfacer/", api.desfacer, name="api_desfacer"),
    path("proba-deck/", views.proba_deck, name="proba_deck"),
    # Xestión da protectora
    path("protectora/cans/", views_protectora.lista, name="protectora_cans"),
    path("protectora/cans/novo/", views_protectora.novo, name="protectora_can_novo"),
    path("protectora/cans/<int:pk>/", views_protectora.editar, name="protectora_can_editar"),
    path(
        "protectora/cans/<int:pk>/retirar/", views_protectora.retirar, name="protectora_can_retirar"
    ),
    path(
        "protectora/cans/<int:pk>/republicar/",
        views_protectora.republicar,
        name="protectora_can_republicar",
    ),
    path("protectora/cans/<int:pk>/fotos/", views_protectora.fotos, name="protectora_fotos"),
    path(
        "protectora/cans/<int:pk>/fotos/<int:foto_pk>/principal/",
        views_protectora.foto_principal,
        name="protectora_foto_principal",
    ),
    path(
        "protectora/cans/<int:pk>/fotos/<int:foto_pk>/borrar/",
        views_protectora.foto_borrar,
        name="protectora_foto_borrar",
    ),
]
