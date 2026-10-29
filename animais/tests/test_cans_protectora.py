"""Probas da xestión de cans e fotos pola protectora."""

import io
from datetime import date

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from animais.models import Can, FotoCan
from compatibilidade.calculo import Espazo, NecesidadesCan

pytestmark = pytest.mark.django_db


def datos_can(**cambios):
    datos = {
        "nome": "Rufus",
        "sexo": "macho",
        "data_nacemento": "2022-03-01",
        "tamano": "mediano",
        "etiquetas": "Cariñoso, Tímido",
        "descricion": "Noble e obediente.",
        "espazo": "patio_recomendado",
        "tolerancia_soidade": "media",
        "convive_nenos": "si",
        "convive_cans": "si",
        "convive_gatos": "non",
        "enerxia": "medio",
    }
    datos.update(cambios)
    return datos


def imaxe(ancho=400, alto=300, formato="JPEG", nome="foto.jpg"):
    saida = io.BytesIO()
    Image.new("RGB", (ancho, alto), "#902124").save(saida, format=formato)
    return SimpleUploadedFile(nome, saida.getvalue(), content_type="image/jpeg")


# --- Ficha do can ---------------------------------------------------------------------


def test_publicar_un_can(client, protectora):
    client.force_login(protectora.usuario)
    resposta = client.post(reverse("animais:protectora_can_novo"), datos_can())
    can = Can.objects.get(nome="Rufus")
    assert can.protectora == protectora
    assert can.estado == Can.Estado.DISPONIBLE
    assert resposta.url == reverse("animais:protectora_fotos", args=[can.pk])


def test_as_seis_necesidades_son_obrigatorias(client, protectora):
    client.force_login(protectora.usuario)
    datos = datos_can()
    del datos["convive_gatos"]
    resposta = client.post(reverse("animais:protectora_can_novo"), datos)
    assert resposta.status_code == 200
    assert not Can.objects.exists()


def test_o_formulario_non_ofrece_opcion_baleira_nas_necesidades(client, protectora):
    client.force_login(protectora.usuario)
    html = client.get(reverse("animais:protectora_can_novo")).content.decode()
    assert "---------" not in html


def test_maximo_catro_etiquetas(client, protectora):
    client.force_login(protectora.usuario)
    resposta = client.post(
        reverse("animais:protectora_can_novo"), datos_can(etiquetas="a, b, c, d, e")
    )
    assert "Como moito, catro" in resposta.content.decode()


def test_data_de_nacemento_no_futuro_rexeitase(client, protectora):
    client.force_login(protectora.usuario)
    resposta = client.post(
        reverse("animais:protectora_can_novo"), datos_can(data_nacemento="2999-01-01")
    )
    assert "no futuro" in resposta.content.decode()


def test_unha_protectora_non_ve_cans_doutra(client, crear_protectora, crear_can):
    can_alleo = crear_can()  # da protectora por defecto
    outra = crear_protectora()
    client.force_login(outra.usuario)
    assert (
        client.get(reverse("animais:protectora_can_editar", args=[can_alleo.pk])).status_code == 404
    )
    url = reverse("animais:protectora_can_retirar", args=[can_alleo.pk])
    assert client.post(url).status_code == 404


def test_editar_un_can(client, protectora, crear_can):
    can = crear_can()
    client.force_login(protectora.usuario)
    client.post(reverse("animais:protectora_can_editar", args=[can.pk]), datos_can(nome="Lúa"))
    can.refresh_from_db()
    assert can.nome == "Lúa"


def test_retirar_e_volver_publicar(client, protectora, crear_can):
    can = crear_can()
    client.force_login(protectora.usuario)
    client.post(reverse("animais:protectora_can_retirar", args=[can.pk]))
    can.refresh_from_db()
    assert can.estado == Can.Estado.RETIRADO
    client.post(reverse("animais:protectora_can_republicar", args=[can.pk]))
    can.refresh_from_db()
    assert can.estado == Can.Estado.DISPONIBLE


def test_non_se_pode_retirar_un_can_reservado(client, protectora, crear_can):
    can = crear_can(estado=Can.Estado.RESERVADO)
    client.force_login(protectora.usuario)
    client.post(reverse("animais:protectora_can_retirar", args=[can.pk]))
    can.refresh_from_db()
    assert can.estado == Can.Estado.RESERVADO


def test_a_lista_so_amosa_os_cans_propios(client, protectora, crear_protectora, crear_can):
    crear_can(nome="Propio")
    crear_can(nome="Alleo", protectora=crear_protectora())
    client.force_login(protectora.usuario)
    html = client.get(reverse("animais:protectora_cans")).content.decode()
    assert "Propio" in html
    assert "Alleo" not in html


# --- Modelo ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("nacemento", "texto"),
    [
        (date(2026, 9, 20), "1 mes"),
        (date(2026, 5, 1), "5 meses"),
        (date(2025, 10, 1), "1 ano"),
        (date(2023, 10, 30), "2 anos"),
        (date(2023, 10, 29), "3 anos"),
    ],
)
def test_idade_texto(crear_can, nacemento, texto):
    can = crear_can(data_nacemento=nacemento)
    assert can.idade_texto(hoxe=date(2026, 10, 29)) == texto


def test_necesidades_converte_o_modelo_para_o_calculo(crear_can):
    necesidades = crear_can(espazo="patio_necesario", require_experiencia=True).necesidades()
    assert isinstance(necesidades, NecesidadesCan)
    assert necesidades.espazo is Espazo.PATIO_NECESARIO
    assert necesidades.require_experiencia is True


def test_textos_de_saude_e_convivencia(crear_can):
    can = crear_can(vacinado=True, microchip=True, convive_gatos="non")
    assert can.saude_texto == "Vacinado, identificado"
    assert can.convivencia_texto == "Nenos, cans"
    assert (
        crear_can(convive_nenos="non", convive_cans="non").convivencia_texto == "Hai que valoralo"
    )
    assert crear_can().saude_texto == "Sen datos"
    assert can.get_espazo_display() == "Adáptase a calquera vivenda"


def test_lista_etiquetas(crear_can):
    assert crear_can(etiquetas="Tranquila, , Boa con nenos").lista_etiquetas == [
        "Tranquila",
        "Boa con nenos",
    ]


# --- Fotos ----------------------------------------------------------------------------


def test_subir_foto_redimensiona_a_1600(client, protectora, crear_can):
    can = crear_can()
    client.force_login(protectora.usuario)
    client.post(reverse("animais:protectora_fotos", args=[can.pk]), {"imaxe": imaxe(4000, 3000)})
    foto = can.fotos.get()
    assert foto.principal
    with Image.open(foto.imaxe.path) as gardada:
        assert gardada.size == (1600, 1200)
        assert gardada.format == "JPEG"


def test_png_con_transparencia_convertese_a_jpeg(client, protectora, crear_can):
    can = crear_can()
    saida = io.BytesIO()
    Image.new("RGBA", (100, 100), (255, 0, 0, 0)).save(saida, format="PNG")
    client.force_login(protectora.usuario)
    client.post(
        reverse("animais:protectora_fotos", args=[can.pk]),
        {"imaxe": SimpleUploadedFile("t.png", saida.getvalue(), content_type="image/png")},
    )
    assert can.fotos.get().imaxe.name.endswith(".jpg")


def test_foto_de_mais_de_5_mb_rexeitase(client, protectora, crear_can):
    can = crear_can()
    grande = SimpleUploadedFile("g.jpg", b"0" * (5 * 1024 * 1024 + 1), content_type="image/jpeg")
    client.force_login(protectora.usuario)
    resposta = client.post(reverse("animais:protectora_fotos", args=[can.pk]), {"imaxe": grande})
    assert not can.fotos.exists()
    assert resposta.status_code == 200


def test_un_exe_renomeado_rexeitase(client, protectora, crear_can):
    can = crear_can()
    falso = SimpleUploadedFile(
        "virus.jpg", b"MZ\x90\x00" + b"\x00" * 200, content_type="image/jpeg"
    )
    client.force_login(protectora.usuario)
    resposta = client.post(reverse("animais:protectora_fotos", args=[can.pk]), {"imaxe": falso})
    assert not can.fotos.exists()
    assert "imaxe" in resposta.content.decode()


def test_formato_non_permitido_rexeitase():
    from django.core.exceptions import ValidationError

    from animais.imaxes import preparar_imaxe

    saida = io.BytesIO()
    Image.new("RGB", (10, 10)).save(saida, format="GIF")
    with pytest.raises(ValidationError, match="JPEG, PNG ou WebP"):
        preparar_imaxe(SimpleUploadedFile("a.gif", saida.getvalue()))


def test_cambiar_principal_e_borrar(client, protectora, crear_can):
    can = crear_can()
    client.force_login(protectora.usuario)
    url = reverse("animais:protectora_fotos", args=[can.pk])
    client.post(url, {"imaxe": imaxe()})
    client.post(url, {"imaxe": imaxe()})
    primeira, segunda = can.fotos.order_by("pk")
    client.post(reverse("animais:protectora_foto_principal", args=[can.pk, segunda.pk]))
    assert can.foto_principal == segunda
    client.post(reverse("animais:protectora_foto_borrar", args=[can.pk, segunda.pk]))
    primeira.refresh_from_db()
    assert primeira.principal
    assert can.fotos.count() == 1


def test_maximo_seis_fotos(client, protectora, crear_can):
    can = crear_can()
    for _ in range(FotoCan.MAXIMO_POR_CAN):
        FotoCan.objects.create(can=can, imaxe="cans/x.jpg")
    client.force_login(protectora.usuario)
    client.post(reverse("animais:protectora_fotos", args=[can.pk]), {"imaxe": imaxe()})
    assert can.fotos.count() == FotoCan.MAXIMO_POR_CAN


def test_sen_fotos_non_hai_principal(crear_can):
    assert crear_can().foto_principal is None
