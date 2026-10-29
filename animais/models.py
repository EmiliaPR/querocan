"""
Modelos dos cans en adopción.

Cada can pertence a unha protectora e garda dous tipos de información:
  - a ficha pública (nome, idade, fotos, carácter, saúde...);
  - as súas necesidades nas seis dimensións de compatibilidade, que a protectora
    enche obrigatoriamente e que se comparan co perfil de cada persoa adoptante.
"""

from datetime import date

from django.db import models

from compatibilidade.calculo import (
    Convivencia,
    Espazo,
    NecesidadesCan,
    Nivel,
    Tamano,
    Tolerancia,
    opcions,
)


class Can(models.Model):
    """Un can publicado por unha protectora."""

    class Estado(models.TextChoices):
        # O ciclo de vida completo está en adopcions/estados.py
        DISPONIBLE = "disponible", "Dispoñible"
        RESERVADO = "reservado", "Reservado"
        ADOPTADO = "adoptado", "Adoptado"
        RETIRADO = "retirado", "Retirado"

    class Sexo(models.TextChoices):
        MACHO = "macho", "Macho"
        FEMIA = "femia", "Femia"

    protectora = models.ForeignKey(
        "contas.Protectora",
        on_delete=models.CASCADE,
        related_name="cans",
        verbose_name="protectora",
    )
    estado = models.CharField(
        "estado", max_length=12, choices=Estado.choices, default=Estado.DISPONIBLE, db_index=True
    )

    # --- Ficha pública ----------------------------------------------------------------
    nome = models.CharField("nome", max_length=60)
    sexo = models.CharField("sexo", max_length=6, choices=Sexo.choices)
    data_nacemento = models.DateField(
        "data de nacemento (aproximada)",
        help_text="Se non se sabe con exactitude, unha data aproximada abonda.",
    )
    tamano = models.CharField("tamaño", max_length=10, choices=opcions(Tamano))
    peso_kg = models.DecimalField(
        "peso (kg)", max_digits=4, decimal_places=1, null=True, blank=True
    )
    raza = models.CharField("raza", max_length=60, blank=True, help_text="Por exemplo: mestizo.")
    etiquetas = models.CharField(
        "carácter",
        max_length=120,
        blank=True,
        help_text="Ata catro palabras separadas por comas. Por exemplo: Tranquila, Cariñosa.",
    )
    descricion = models.TextField(
        "historia e carácter", help_text="Como é, de onde vén, que lle gusta e que non."
    )
    urxente = models.BooleanField(
        "adopción urxente", default=False, help_text="Destácase nas tarxetas e nos filtros."
    )
    vacinado = models.BooleanField("vacinado", default=False)
    desparasitado = models.BooleanField("desparasitado", default=False)
    microchip = models.BooleanField("identificado con microchip", default=False)
    esterilizado = models.BooleanField("esterilizado", default=False)

    # --- Necesidades (as seis dimensións de compatibilidade) ----------------------------
    espazo = models.CharField("espazo que necesita", max_length=20, choices=opcions(Espazo))
    tolerancia_soidade = models.CharField(
        "canto tempo soporta estar só", max_length=10, choices=opcions(Tolerancia)
    )
    convive_nenos = models.CharField(
        "convive con nenos", max_length=12, choices=opcions(Convivencia)
    )
    convive_cans = models.CharField("convive con cans", max_length=12, choices=opcions(Convivencia))
    convive_gatos = models.CharField(
        "convive con gatos", max_length=12, choices=opcions(Convivencia)
    )
    enerxia = models.CharField("nivel de enerxía", max_length=6, choices=opcions(Nivel))
    require_experiencia = models.BooleanField(
        "recoméndase experiencia previa con cans", default=False
    )

    data_publicacion = models.DateTimeField("data de publicación", auto_now_add=True)
    data_actualizacion = models.DateTimeField("última modificación", auto_now=True)

    class Meta:
        verbose_name = "can"
        verbose_name_plural = "cans"
        ordering = ["-urxente", "-data_publicacion"]

    def __str__(self):
        return self.nome

    # --- Datos calculados para a interface ----------------------------------------------

    def idade_en_meses(self, hoxe=None):
        hoxe = hoxe or date.today()
        meses = (hoxe.year - self.data_nacemento.year) * 12 + hoxe.month - self.data_nacemento.month
        if hoxe.day < self.data_nacemento.day:
            meses -= 1
        return max(meses, 0)

    def idade_texto(self, hoxe=None):
        """«5 meses», «1 ano», «3 anos»."""
        meses = self.idade_en_meses(hoxe)
        if meses < 12:
            return "1 mes" if meses == 1 else f"{meses} meses"
        anos = meses // 12
        return "1 ano" if anos == 1 else f"{anos} anos"

    @property
    def lista_etiquetas(self):
        return [e.strip() for e in self.etiquetas.split(",") if e.strip()][:4]

    @property
    def saude_texto(self):
        partes = [
            ("vacinado", self.vacinado),
            ("desparasitado", self.desparasitado),
            ("identificado", self.microchip),
            ("esterilizado", self.esterilizado),
        ]
        feitas = [nome for nome, feito in partes if feito]
        return ", ".join(feitas).capitalize() if feitas else "Sen datos"

    @property
    def convivencia_texto(self):
        """Resumo para a ficha: «Nenos, cans» ou «Non convive con outros animais»."""
        con = [
            nome
            for nome, valor in (
                ("nenos", self.convive_nenos),
                ("cans", self.convive_cans),
                ("gatos", self.convive_gatos),
            )
            if valor == Convivencia.SI
        ]
        return ", ".join(con).capitalize() if con else "Hai que valoralo"

    @property
    def foto_principal(self):
        """Foto para tarxetas: a marcada como principal ou, se non hai, a primeira."""
        fotos = list(self.fotos.all())  # aproveita prefetch_related("fotos") se se usou
        return next((f for f in fotos if f.principal), fotos[0] if fotos else None)

    # --- Ponte co cálculo de compatibilidade --------------------------------------------

    def necesidades(self) -> NecesidadesCan:
        """Converte os campos do modelo no obxecto que entende compatibilidade/calculo.py."""
        return NecesidadesCan(
            espazo=Espazo(self.espazo),
            tamano=Tamano(self.tamano),
            tolerancia_soidade=Tolerancia(self.tolerancia_soidade),
            convive_nenos=Convivencia(self.convive_nenos),
            convive_cans=Convivencia(self.convive_cans),
            convive_gatos=Convivencia(self.convive_gatos),
            enerxia=Nivel(self.enerxia),
            require_experiencia=self.require_experiencia,
        )

    @property
    def pode_retirarse(self):
        """Un can reservado (cunha solicitude aceptada) ou xa adoptado non se pode retirar."""
        return self.estado == self.Estado.DISPONIBLE


def _ruta_foto(foto, nome_ficheiro):
    """As fotos gárdanse en media/cans/<id do can>/<nome aleatorio>.jpg."""
    return f"cans/{foto.can_id}/{nome_ficheiro}"


class FotoCan(models.Model):
    """Foto dun can. Unha delas é a principal (a que sae nas tarxetas)."""

    MAXIMO_POR_CAN = 6  # a principal e ata cinco máis

    can = models.ForeignKey(Can, on_delete=models.CASCADE, related_name="fotos")
    imaxe = models.ImageField("foto", upload_to=_ruta_foto)
    principal = models.BooleanField("foto principal", default=False)
    orde = models.PositiveSmallIntegerField("orde", default=0)

    class Meta:
        verbose_name = "foto"
        verbose_name_plural = "fotos"
        ordering = ["-principal", "orde", "pk"]

    def __str__(self):
        return f"Foto de {self.can.nome}"
