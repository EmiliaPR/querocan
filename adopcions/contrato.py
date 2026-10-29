"""
Contrato de adopción: texto final, hash e PDF.

O contrato é un modelo común (ModeloContrato) cos datos de cada adopción. Ao
aceptalo gardamos o texto final exacto e o seu hash SHA-256 nunha AceptacionContrato
que xa non se pode modificar, e completamos a adopción na mesma transacción.

Limitación consciente (documentada en SPEC.md): non é unha sinatura dixital con
validez legal plena; é unha aceptación rexistrada e verificable.
"""

import hashlib
import re

from django.db import transaction
from django.template.loader import render_to_string
from django.utils import formats, timezone

from . import estados
from .models import AceptacionContrato, ModeloContrato

LETRAS_DNI = "TRWAGMYFPDXBNJZSQVHLCKE"


def nif_valido(nif):
    """Comproba a letra dun DNI (12345678Z) ou NIE (X1234567L)."""
    nif = nif.upper().replace("-", "").replace(" ", "")
    if not re.fullmatch(r"[XYZ0-9]\d{7}[A-Z]", nif):
        return False
    numero = nif[:-1].replace("X", "0").replace("Y", "1").replace("Z", "2")
    return LETRAS_DNI[int(numero) % 23] == nif[-1]


def texto_final(modelo, solicitude, datos, data=None):
    """Substitúe os marcadores do modelo cos datos desta adopción."""
    data = data or timezone.localdate()
    valores = {
        "nome": datos["nome"],
        "nif": datos["nif"],
        "enderezo": datos["enderezo"],
        "telefono": datos["telefono"],
        "email": datos["email"],
        "can": solicitude.can.nome,
        "protectora": solicitude.can.protectora.nome,
        "data": formats.date_format(data, "j \\d\\e F \\d\\e Y").lower(),
    }
    texto = modelo.texto
    for clave, valor in valores.items():
        texto = texto.replace("{" + clave + "}", str(valor))
    return texto


def calcular_hash(texto):
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


@transaction.atomic
def aceptar(solicitude, actor, datos, ip=None):
    """Garda o contrato aceptado e completa a adopción (todo ou nada)."""
    modelo = ModeloContrato.actual()
    if modelo is None:
        raise estados.TransicionInvalida("Non hai ningún modelo de contrato activo.")
    texto = texto_final(modelo, solicitude, datos)
    estados.completar_adopcion(solicitude, actor)
    return AceptacionContrato.objects.create(
        solicitude=solicitude,
        modelo=modelo,
        texto_final=texto,
        hash_sha256=calcular_hash(texto),
        ip=ip,
        **{campo: datos[campo] for campo in ("nome", "nif", "enderezo", "telefono", "email")},
    )


def xerar_pdf(aceptacion):
    """PDF do contrato aceptado (WeasyPrint a partir dunha plantilla HTML)."""
    from weasyprint import HTML

    html = render_to_string("adopcions/contrato_pdf.html", {"aceptacion": aceptacion})
    return HTML(string=html).write_pdf()
