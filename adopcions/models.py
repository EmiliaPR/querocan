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


class ItemChecklist(models.Model):
    """Un compromiso de responsabilidade que a persoa ten que marcar antes do contrato.

    Os textos saen do Manual de boas maneiras e pódeos editar o superadmin.
    """

    texto = models.CharField("compromiso", max_length=250)
    orde = models.PositiveSmallIntegerField("orde", default=0)
    activo = models.BooleanField("activo", default=True)

    class Meta:
        verbose_name = "compromiso do checklist"
        verbose_name_plural = "compromisos do checklist"
        ordering = ["orde", "pk"]

    def __str__(self):
        return self.texto


class ModeloContrato(models.Model):
    """Texto común do contrato de adopción. Cada edición crea unha versión nova.

    O texto admite marcadores entre chaves que se substitúen ao aceptar:
    {nome}, {nif}, {enderezo}, {telefono}, {email}, {can}, {protectora}, {data}.
    """

    version = models.PositiveIntegerField("versión", unique=True)
    texto = models.TextField("texto do contrato")
    activo = models.BooleanField("en uso", default=False)
    data_creacion = models.DateTimeField("data", auto_now_add=True)

    class Meta:
        verbose_name = "modelo de contrato"
        verbose_name_plural = "modelos de contrato"
        ordering = ["-version"]

    def __str__(self):
        return f"Contrato v{self.version}"

    @classmethod
    def actual(cls):
        return cls.objects.filter(activo=True).order_by("-version").first()


class ContratoInmutable(Exception):
    """Unha aceptación de contrato xa gardada non se pode modificar nin borrar."""


class AceptacionContrato(models.Model):
    """Copia exacta do contrato que aceptou a persoa, co seu hash SHA-256.

    Non se pode modificar despois de creada: así sempre se pode demostrar que o
    texto gardado é o que se aceptou (o hash dun texto cambiado non coincidiría).
    """

    solicitude = models.OneToOneField(Solicitude, on_delete=models.PROTECT, related_name="contrato")
    modelo = models.ForeignKey(ModeloContrato, on_delete=models.PROTECT, related_name="aceptacions")
    texto_final = models.TextField("texto aceptado")
    hash_sha256 = models.CharField("hash SHA-256", max_length=64)
    nome = models.CharField("nome e apelidos", max_length=150)
    nif = models.CharField("NIF/NIE", max_length=9)
    enderezo = models.CharField("enderezo", max_length=250)
    telefono = models.CharField("teléfono", max_length=20)
    email = models.EmailField("correo electrónico")
    data = models.DateTimeField("data de aceptación", auto_now_add=True)
    ip = models.GenericIPAddressField("IP", null=True, blank=True)

    class Meta:
        verbose_name = "contrato aceptado"
        verbose_name_plural = "contratos aceptados"

    def __str__(self):
        return f"Contrato de {self.solicitude.can.nome} ({self.nome})"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ContratoInmutable("Un contrato aceptado non se pode modificar.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ContratoInmutable("Un contrato aceptado non se pode borrar.")
