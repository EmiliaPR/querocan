"""Probas do listado, da ficha e das consultas de cans."""

from datetime import date, timedelta

import pytest
from django.urls import reverse

from animais.consultas import aplicar_filtros, cans_publicados
from animais.filtros import ler_filtros
from animais.models import Can

pytestmark = pytest.mark.django_db


def test_o_listado_so_amosa_cans_dispoñibles_de_protectoras_activas(
    client, crear_can, crear_protectora
):
    crear_can(nome="Visible")
    for estado in ("reservado", "adoptado", "retirado"):
        crear_can(nome=f"Oculto-{estado}", estado=estado)
    crear_can(nome="DeInactiva", protectora=crear_protectora(estado="pendente"))
    html = client.get(reverse("animais:listado")).content.decode()
    assert "Visible" in html
    assert "Oculto" not in html
    assert "DeInactiva" not in html


def test_ler_filtros_ignora_valores_raros():
    assert (
        ler_filtros({"tamano": "xigante", "idade": "x", "distancia": "7", "urxentes": "si"}) == {}
    )
    assert ler_filtros({"tamano": "grande", "distancia": "50", "urxentes": "1"}) == {
        "tamano": "grande",
        "distancia": 50,
        "urxentes": True,
    }


def test_filtros_de_idade_tamano_e_urxencia(crear_can):
    hoxe = date(2026, 10, 29)
    crear_can(nome="Cachorro", data_nacemento=hoxe - timedelta(days=100))
    crear_can(nome="Adulto", data_nacemento=hoxe - timedelta(days=365 * 4), urxente=True)
    crear_can(nome="Maior", data_nacemento=hoxe - timedelta(days=365 * 10), tamano="grande")

    def nomes(filtros):
        return {c.nome for c in aplicar_filtros(cans_publicados(), filtros, hoxe)}

    assert nomes({"idade": "cachorro"}) == {"Cachorro"}
    assert nomes({"idade": "adulto"}) == {"Adulto"}
    assert nomes({"idade": "maior"}) == {"Maior"}
    assert nomes({"tamano": "grande"}) == {"Maior"}
    assert nomes({"urxentes": True}) == {"Adulto"}


def test_os_filtros_mantenense_na_url(client, crear_can):
    crear_can()
    html = client.get(reverse("animais:listado") + "?tamano=pequeno&urxentes=1").content.decode()
    assert '<option value="pequeno" selected>' in html
    assert 'name="urxentes" value="1" id="f-urxentes" checked' in html


def test_filtro_de_distancia(client, crear_can, crear_protectora, outro_concello, concello):
    crear_can(nome="EnVigo")
    crear_can(nome="EnSantiago", protectora=crear_protectora(concello=outro_concello))
    client.post(reverse("compatibilidade:localizacion"), {"concello": concello.pk})
    html = client.get(reverse("animais:listado") + "?distancia=25").content.decode()
    assert "EnVigo" in html
    assert "EnSantiago" not in html
    html = client.get(reverse("animais:listado")).content.decode()
    assert "EnSantiago" in html and "A 72 km" in html


def test_con_perfil_ordena_por_compatibilidade(client, adoptante, crear_perfil, crear_can):
    crear_perfil(adoptante, ten_nenos=True)
    crear_can(nome="SenNenos", convive_nenos="non", urxente=True)
    crear_can(nome="ConNenos", convive_nenos="si")
    client.force_login(adoptante)
    html = client.get(reverse("animais:listado")).content.decode()
    assert html.index("ConNenos") < html.index("SenNenos")
    assert "100%" in html and "40%" in html


def test_sen_perfil_urxentes_primeiro_e_sen_porcentaxe(client, crear_can):
    crear_can(nome="Normal")
    crear_can(nome="Urxente", urxente=True)
    html = client.get(reverse("animais:listado")).content.decode()
    assert html.index("Urxente,") < html.index("Normal,")
    assert "% de compatibilidade" not in html


def test_paxinacion(client, crear_can):
    for numero in range(14):
        crear_can(nome=f"Can{numero:02d}")
    html = client.get(reverse("animais:listado")).content.decode()
    assert "Páxina 1 de 2" in html
    assert client.get(reverse("animais:listado") + "?paxina=2").status_code == 200


def test_listado_sen_resultados(client):
    assert (
        "Non hai cans con estes filtros" in client.get(reverse("animais:listado")).content.decode()
    )


# --- Ficha ----------------------------------------------------------------------------


def test_ficha_publica_sen_porcentaxe_para_quen_non_fixo_o_test(client, crear_can):
    can = crear_can(nome="Luna", etiquetas="Tranquila, Cariñosa")
    html = client.get(reverse("animais:ficha", args=[can.pk])).content.decode()
    assert "Luna" in html and "Tranquila" in html
    assert "de compatibilidade contigo" not in html
    assert "Fai o test" in html


def test_ficha_con_perfil_amosa_porcentaxe_e_motivos(client, adoptante_con_perfil, crear_can):
    can = crear_can()
    client.force_login(adoptante_con_perfil)
    html = client.get(reverse("animais:ficha", args=[can.pk])).content.decode()
    assert "100%" in html
    assert "Adáptase á túa vivenda" in html


def test_ficha_dun_can_retirado_e_404_agás_para_a_protectora(client, crear_can, protectora):
    can = crear_can(estado="retirado")
    assert client.get(reverse("animais:ficha", args=[can.pk])).status_code == 404
    client.force_login(protectora.usuario)
    assert client.get(reverse("animais:ficha", args=[can.pk])).status_code == 200


def test_ficha_dun_can_reservado_non_ofrece_adoptar(client, crear_can):
    can = crear_can(estado=Can.Estado.RESERVADO)
    html = client.get(reverse("animais:ficha", args=[can.pk])).content.decode()
    assert "Reservado" in html
    assert ">Adoptar</button>" not in html


def test_ficha_amosa_a_solicitude_en_curso(client, adoptante_con_perfil, crear_can):
    from adopcions import estados

    can = crear_can()
    estados.crear_solicitude(adoptante_con_perfil, can)
    client.force_login(adoptante_con_perfil)
    html = client.get(reverse("animais:ficha", args=[can.pk])).content.decode()
    assert "Xa tes unha solicitude" in html


def test_ficha_amosa_cans_parecidos(client, crear_can):
    can = crear_can(nome="Principal", tamano="grande")
    crear_can(nome="Parecido", tamano="grande")
    crear_can(nome="Diferente", tamano="pequeno")
    html = client.get(reverse("animais:ficha", args=[can.pk])).content.decode()
    assert "Parecido" in html
    assert "Diferente" not in html


def test_ficha_ten_botons_non_implementados(client, crear_can):
    html = client.get(reverse("animais:ficha", args=[crear_can().pk])).content.decode()
    assert html.count("data-non-implementado") >= 2
    assert "Apadriñar" in html and "Apadrinar" not in html
