"""Modelos da app de compatibilidade."""

from django.db import models


class Concello(models.Model):
    """Concello de Galicia coas coordenadas do seu centro.

    Serve para situar protectoras e adoptantes cando non se usa o GPS e para calcular
    a distancia ata cada can. A clave primaria é o código INE (p. ex. 36057 = Vigo).
    Os datos cárganse coa fixture «concellos».
    """

    codigo_ine = models.PositiveIntegerField("código INE", primary_key=True)
    nome = models.CharField("nome", max_length=100)
    provincia = models.CharField("provincia", max_length=20)
    latitude = models.FloatField("latitude")
    lonxitude = models.FloatField("lonxitude")

    class Meta:
        verbose_name = "concello"
        verbose_name_plural = "concellos"
        ordering = ["nome"]

    def __str__(self):
        return f"{self.nome} ({self.provincia})"
