"""
Preparación das fotos que suben as protectoras.

Antes de gardar unha foto comprobamos que é de verdade unha imaxe (non basta coa
extensión do ficheiro), limitamos o tamaño e reducímola a 1600 px no lado máis
longo. Así as fichas cargan rápido no móbil e o disco non se enche.
"""

import io
import uuid

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

TAMANO_MAXIMO_BYTES = 5 * 1024 * 1024  # 5 MB
LADO_MAXIMO_PX = 1600
FORMATOS_PERMITIDOS = {"JPEG", "PNG", "WEBP"}


def preparar_imaxe(ficheiro):
    """Valida e redimensiona unha imaxe subida. Devolve un ContentFile en JPEG.

    Lanza ValidationError (con mensaxe en galego) se o ficheiro non serve.
    """
    if ficheiro.size > TAMANO_MAXIMO_BYTES:
        raise ValidationError("A foto non pode pesar máis de 5 MB.")

    try:
        imaxe = Image.open(ficheiro)
        imaxe.verify()  # detecta ficheiros corruptos ou que non son imaxes
    except (UnidentifiedImageError, OSError, SyntaxError) as erro:
        raise ValidationError("O ficheiro non é unha imaxe válida.") from erro

    # verify() deixa a imaxe inservible: hai que abrila de novo para traballar con ela
    ficheiro.seek(0)
    imaxe = Image.open(ficheiro)
    if imaxe.format not in FORMATOS_PERMITIDOS:
        raise ValidationError("Só se admiten fotos en JPEG, PNG ou WebP.")

    imaxe = ImageOps.exif_transpose(imaxe)  # respecta a orientación das fotos do móbil
    imaxe = imaxe.convert("RGB")  # JPEG non admite transparencia
    imaxe.thumbnail((LADO_MAXIMO_PX, LADO_MAXIMO_PX))

    saida = io.BytesIO()
    imaxe.save(saida, format="JPEG", quality=85, optimize=True)
    return ContentFile(saida.getvalue(), name=f"{uuid.uuid4().hex}.jpg")
