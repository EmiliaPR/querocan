"""
Modelos do fluxo de adopción.

IMPORTANTE: o campo `estado` das solicitudes (e o do can) só se cambia desde
adopcions/estados.py. Alí están todas as regras do fluxo nun único sitio.
"""

from django.conf import settings
from django.db import models


class Solicitude(models.Model):
    """Unha persoa quere adoptar un can (deslizou á dereita ou premeu «Adoptar»)."""

    class Estado(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        EN_ESPERA = "en_espera", "En espera"
        ACEPTADA = "aceptada", "Aceptada"
        REXEITADA = "rexeitada", "Rexeitada"
        CANCELADA = "cancelada", "Cancelada"
        CADUCADA = "caducada", "Caducada"
        COMPLETADA = "completada", "Adopción completada"

    # Estados nos que a solicitude segue viva (só pode haber unha por persoa e can)
    ACTIVAS = (Estado.PENDENTE, Estado.EN_ESPERA, Estado.ACEPTADA)

    adoptante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="solicitudes",
        verbose_name="persoa adoptante",
    )
    can = models.ForeignKey(
        "animais.Can", on_delete=models.CASCADE, related_name="solicitudes", verbose_name="can"
    )
    estado = models.CharField(
        "estado", max_length=12, choices=Estado.choices, default=Estado.PENDENTE, db_index=True
    )
    # Compatibilidade no momento de solicitar (para o panel e as métricas)
    porcentaxe = models.PositiveSmallIntegerField("compatibilidade (%)", null=True, blank=True)

    data_creacion = models.DateTimeField("data da solicitude", auto_now_add=True)
    data_aceptacion = models.DateTimeField("data de aceptación", null=True, blank=True)
    data_checklist = models.DateTimeField("data do compromiso", null=True, blank=True)
    data_peche = models.DateTimeField("data de peche", null=True, blank=True)

    class Meta:
        verbose_name = "solicitude"
        verbose_name_plural = "solicitudes"
        ordering = ["-data_creacion"]

    def __str__(self):
        return f"{self.adoptante.nome} → {self.can.nome} ({self.get_estado_display()})"

    @property
    def activa(self):
        return self.estado in self.ACTIVAS

    @property
    def checklist_feito(self):
        return self.data_checklist is not None


class HistorialSolicitude(models.Model):
    """Rexistro de cada cambio de estado: quen, cando e de que estado a cal.

    Serve para o funil de métricas do superadmin e para saber que pasou con cada
    solicitude. Só se escribe desde adopcions/estados.py.
    """

    solicitude = models.ForeignKey(Solicitude, on_delete=models.CASCADE, related_name="historial")
    estado_anterior = models.CharField(max_length=12, blank=True)
    estado_novo = models.CharField(max_length=12)
    # Marca especial para o checklist (non cambia o estado pero é unha etapa do funil)
    evento = models.CharField(max_length=20, blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    data = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "cambio de estado"
        verbose_name_plural = "historial de solicitudes"
        ordering = ["data", "pk"]


class Descarte(models.Model):
    """A persoa deslizou á esquerda: non lle volvemos amosar ese can no deck."""

    adoptante = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="descartes"
    )
    can = models.ForeignKey("animais.Can", on_delete=models.CASCADE, related_name="descartes")
    data = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "descarte"
        verbose_name_plural = "descartes"
        constraints = [models.UniqueConstraint(fields=["adoptante", "can"], name="descarte_unico")]
