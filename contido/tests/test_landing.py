"""Probas da landing e do compoñente de aviso de funcionalidades non implementadas."""

import re
from pathlib import Path

import pytest
from django.conf import settings


@pytest.mark.django_db
def test_a_landing_responde_e_usa_o_lema(client):
    resposta = client.get("/")
    assert resposta.status_code == 200
    assert "Un pequeno xesto," in resposta.content.decode()


@pytest.mark.django_db
def test_a_landing_non_promete_contacto_directo_como_paso_final(client):
    """Decisión 4: o fluxo remata en match, checklist e contrato, non en «contacto directo»."""
    html = client.get("/").content.decode().lower()
    assert "contacto directo" not in html


@pytest.mark.django_db
def test_a_base_inclue_a_rexion_do_aviso(client):
    html = client.get("/").content.decode()
    assert 'id="aviso-flotante"' in html
    assert 'role="status"' in html


def test_o_css_so_usa_cores_dos_tokens():
    """Ningún CSS fóra de tokens.css pode ter cores hexadecimais soltas."""
    directorio = Path(settings.BASE_DIR) / "static" / "css"
    for ficheiro in directorio.glob("*.css"):
        if ficheiro.name == "tokens.css":
            continue
        cores = re.findall(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(", ficheiro.read_text())
        assert cores == [], f"{ficheiro.name} ten cores fóra dos tokens: {cores}"
