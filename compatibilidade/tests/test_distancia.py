"""Probas do cálculo de distancias e da fixture de concellos."""

import pytest

from compatibilidade.distancia import distancia_km, texto_distancia
from compatibilidade.models import Concello


def test_distancia_vigo_santiago_e_uns_80_km():
    # Coordenadas aproximadas dos centros de Vigo e Santiago de Compostela
    km = distancia_km(42.2406, -8.7207, 42.8782, -8.5448)
    assert 70 <= km <= 74  # en liña recta (por estrada son uns 90)


def test_distancia_dun_punto_a_si_mesmo_e_cero():
    assert distancia_km(42.0, -8.0, 42.0, -8.0) == 0


def test_distancia_e_simetrica():
    ida = distancia_km(43.36, -8.41, 42.34, -7.86)
    volta = distancia_km(42.34, -7.86, 43.36, -8.41)
    assert ida == pytest.approx(volta)


@pytest.mark.parametrize(
    ("km", "texto"), [(None, ""), (0.3, "menos de 1 km"), (12.4, "12 km"), (12.6, "13 km")]
)
def test_texto_distancia(km, texto):
    assert texto_distancia(km) == texto


@pytest.mark.django_db
def test_a_fixture_carga_os_313_concellos(django_db_blocker):
    from django.core.management import call_command

    call_command("loaddata", "concellos", verbosity=0)
    assert Concello.objects.count() == 313
    vigo = Concello.objects.get(pk=36057)
    assert vigo.nome == "Vigo"
    assert vigo.provincia == "Pontevedra"
    santiago = Concello.objects.get(nome="Santiago de Compostela")
    assert (
        70
        <= distancia_km(vigo.latitude, vigo.lonxitude, santiago.latitude, santiago.lonxitude)
        <= 80
    )
