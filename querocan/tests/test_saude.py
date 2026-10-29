"""Proba de fume: a aplicación arranca e chega á base de datos MySQL."""

import pytest
from django.db import connection


@pytest.mark.django_db
def test_saude_responde_ok(client):
    resposta = client.get("/saude/")
    assert resposta.status_code == 200
    assert resposta.json() == {"estado": "ok", "base_de_datos": "mysql"}


def test_weasyprint_xera_un_pdf():
    """WeasyPrint necesita librarías do sistema; se faltan na imaxe, falla aquí."""
    from weasyprint import HTML

    pdf = HTML(string="<h1>Ola mundo</h1>").write_pdf()
    assert pdf.startswith(b"%PDF")


@pytest.mark.django_db
def test_os_tests_corren_contra_mysql():
    assert connection.vendor == "mysql"
