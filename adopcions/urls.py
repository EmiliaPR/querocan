"""Rutas do fluxo de adopción."""

from django.urls import path

from . import views_adoptante, views_protectora

app_name = "adopcions"

urlpatterns = [
    # Persoa adoptante
    path("solicitar/<int:pk>/", views_adoptante.solicitar, name="solicitar"),
    path("solicitar/continuar/", views_adoptante.continuar, name="continuar"),
    path("solicitudes/", views_adoptante.minas_solicitudes, name="minas_solicitudes"),
    path("solicitudes/<int:pk>/retirar/", views_adoptante.retirar, name="retirar"),
    path("solicitudes/<int:pk>/compromiso/", views_adoptante.checklist, name="checklist"),
    path("solicitudes/<int:pk>/contrato/", views_adoptante.contrato, name="contrato"),
    path(
        "solicitudes/<int:pk>/parabens/",
        views_adoptante.adopcion_completada,
        name="adopcion_completada",
    ),
    path("solicitudes/<int:pk>/contrato.pdf", views_adoptante.contrato_pdf, name="contrato_pdf"),
    # Protectora
    path("protectora/solicitudes/", views_protectora.solicitudes, name="protectora_solicitudes"),
    path(
        "protectora/solicitudes/<int:pk>/<str:nome>/",
        views_protectora.accion,
        name="protectora_accion",
    ),
]
