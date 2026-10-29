"""Contido editable polo superadmin: testemuños de Finais felices e enlaces de interese."""

from django.db import models


class Testemuno(models.Model):
    """Historia dunha persoa que adoptou («Finais felices»)."""

    nome_persoa = models.CharField(
        "persoa", max_length=80, help_text="Por exemplo: Marta (42 anos)"
    )
    nome_can = models.CharField("can", max_length=60)
    texto = models.TextField("testemuño")
    foto = models.ImageField("foto", upload_to="testemunos/", blank=True)
    publicado = models.BooleanField("publicado", default=True)
    orde = models.PositiveSmallIntegerField("orde", default=0)

    class Meta:
        verbose_name = "testemuño"
        verbose_name_plural = "testemuños"
        ordering = ["orde", "-pk"]

    def __str__(self):
        return f"{self.nome_persoa} e {self.nome_can}"


class Enlace(models.Model):
    """Ligazón da páxina «Enlaces de interese»."""

    titulo = models.CharField("título", max_length=120)
    url = models.URLField("enderezo", max_length=300)
    descricion = models.CharField("descrición", max_length=250, blank=True)
    orde = models.PositiveSmallIntegerField("orde", default=0)

    class Meta:
        verbose_name = "enlace"
        verbose_name_plural = "enlaces"
        ordering = ["orde", "titulo"]

    def __str__(self):
        return self.titulo
