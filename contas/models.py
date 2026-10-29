"""
Modelos de contas de QueroCan.

Usamos un modelo de usuario propio (en lugar do de Django) por dous motivos:
  1. As persoas entran co correo electrónico, non cun nome de usuario.
  2. Cada conta ten un único rol (adoptante, protectora ou superadmin), gardado nun
     campo simple. É máis doado de ler e explicar ca os grupos e permisos de Django.
"""

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

from compatibilidade.calculo import (
    HorasSo,
    Nivel,
    OutrosAnimais,
    PreferenciaTamano,
    Vivenda,
    opcions,
)
from compatibilidade.calculo import PerfilAdoptante as PerfilCalculo


class XestorUsuarios(BaseUserManager):
    """Crea usuarios identificados polo correo (usado por createsuperuser e o rexistro)."""

    use_in_migrations = True

    def _crear(self, email, password, **campos):
        if not email:
            raise ValueError("O correo electrónico é obrigatorio.")
        usuario = self.model(email=self.normalize_email(email), **campos)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_user(self, email, password=None, **campos):
        campos.setdefault("rol", Usuario.Rol.ADOPTANTE)
        campos.setdefault("is_staff", False)
        campos.setdefault("is_superuser", False)
        return self._crear(email, password, **campos)

    def create_superuser(self, email, password=None, **campos):
        """O superusuario de Django é sempre o rol «superadmin» de QueroCan."""
        campos["rol"] = Usuario.Rol.SUPERADMIN
        campos["is_staff"] = True
        campos["is_superuser"] = True
        return self._crear(email, password, **campos)


class Usuario(AbstractUser):
    """Persoa usuaria de QueroCan. O campo `rol` decide a que partes da web pode entrar."""

    class Rol(models.TextChoices):
        ADOPTANTE = "adoptante", "Persoa adoptante"
        PROTECTORA = "protectora", "Protectora"
        SUPERADMIN = "superadmin", "Superadministración"

    # Quitamos o nome de usuario de Django: identificamos as contas polo correo
    username = None
    email = models.EmailField("correo electrónico", unique=True)
    nome = models.CharField("nome", max_length=150)
    rol = models.CharField("rol", max_length=20, choices=Rol.choices, default=Rol.ADOPTANTE)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nome"]

    objects = XestorUsuarios()

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"

    def __str__(self):
        return f"{self.nome} <{self.email}>"

    # Atallos para as plantillas e as vistas: usuario.es_adoptante, etc.
    @property
    def es_adoptante(self):
        return self.rol == self.Rol.ADOPTANTE

    @property
    def es_protectora(self):
        return self.rol == self.Rol.PROTECTORA

    @property
    def es_superadmin(self):
        return self.rol == self.Rol.SUPERADMIN


class Protectora(models.Model):
    """Datos da entidade protectora. Cada protectora ten unha conta co rol «protectora».

    Unha protectora nova queda pendente ata que o superadmin a valida; mentres tanto
    non pode publicar cans.
    """

    class Estado(models.TextChoices):
        PENDENTE_VALIDACION = "pendente", "Pendente de validación"
        ACTIVA = "activa", "Activa"
        REXEITADA = "rexeitada", "Rexeitada"
        DESACTIVADA = "desactivada", "Desactivada"

    usuario = models.OneToOneField(
        Usuario, on_delete=models.CASCADE, related_name="protectora", verbose_name="conta"
    )
    nome = models.CharField("nome da protectora", max_length=150)
    cif = models.CharField("CIF", max_length=12, unique=True)
    concello = models.ForeignKey(
        "compatibilidade.Concello", on_delete=models.PROTECT, verbose_name="concello"
    )
    enderezo = models.CharField("enderezo", max_length=200, blank=True)
    telefono = models.CharField("teléfono", max_length=20)
    email_contacto = models.EmailField("correo de contacto")
    web = models.URLField("web", blank=True)
    descricion = models.TextField("descrición", blank=True)
    estado = models.CharField(
        "estado", max_length=12, choices=Estado.choices, default=Estado.PENDENTE_VALIDACION
    )
    data_alta = models.DateTimeField("data de alta", auto_now_add=True)
    data_validacion = models.DateTimeField("data de validación", null=True, blank=True)

    class Meta:
        verbose_name = "protectora"
        verbose_name_plural = "protectoras"
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    @property
    def activa(self):
        return self.estado == self.Estado.ACTIVA

    @property
    def latitude(self):
        return self.concello.latitude

    @property
    def lonxitude(self):
        return self.concello.lonxitude


class PerfilAdoptante(models.Model):
    """Respostas do test de compatibilidade e localización dunha persoa adoptante.

    Créase cando a persoa completa o test (con conta, ou ao crear a conta se o fixo
    antes sen ela). Sen perfil non se poden enviar solicitudes de adopción.
    """

    usuario = models.OneToOneField(
        Usuario, on_delete=models.CASCADE, related_name="perfil", verbose_name="conta"
    )
    # As seis dimensións do test (os valores veñen de compatibilidade/calculo.py)
    vivenda = models.CharField("vivenda", max_length=20, choices=opcions(Vivenda))
    tamano = models.CharField("tamaño que busca", max_length=12, choices=opcions(PreferenciaTamano))
    horas_so = models.CharField("horas só", max_length=12, choices=opcions(HorasSo))
    ten_nenos = models.BooleanField("hai nenos na casa")
    outros_animais = models.CharField(
        "outros animais na casa", max_length=14, choices=opcions(OutrosAnimais)
    )
    actividade = models.CharField("ritmo de vida", max_length=6, choices=opcions(Nivel))
    experiencia = models.BooleanField("xa tivo can")

    # Localización: do GPS do navegador ou do concello escollido
    concello = models.ForeignKey(
        "compatibilidade.Concello", on_delete=models.SET_NULL, null=True, blank=True
    )
    latitude = models.FloatField(null=True, blank=True)
    lonxitude = models.FloatField(null=True, blank=True)

    data_actualizacion = models.DateTimeField("última actualización", auto_now=True)

    class Meta:
        verbose_name = "perfil de adoptante"
        verbose_name_plural = "perfís de adoptante"

    def __str__(self):
        return f"Perfil de {self.usuario.nome}"

    def como_perfil(self) -> PerfilCalculo:
        """Converte o modelo no obxecto que entende compatibilidade/calculo.py."""
        return PerfilCalculo(
            vivenda=Vivenda(self.vivenda),
            tamano=PreferenciaTamano(self.tamano),
            horas_so=HorasSo(self.horas_so),
            ten_nenos=self.ten_nenos,
            outros_animais=OutrosAnimais(self.outros_animais),
            actividade=Nivel(self.actividade),
            experiencia=self.experiencia,
        )
