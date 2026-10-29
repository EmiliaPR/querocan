"""
Fixtures de pytest compartidas por todas as apps.

Crean persoas usuarias de cada rol para non repetir o mesmo código en cada test.
"""

import pytest

from contas.models import Usuario

CONTRASINAL = "unha-clave-segura-123"


@pytest.fixture
def crear_usuario(db):
    """Fábrica: crear_usuario(rol=..., email=...) devolve un Usuario gardado."""
    contador = {"n": 0}

    def _crear(rol=Usuario.Rol.ADOPTANTE, **campos):
        contador["n"] += 1
        campos.setdefault("email", f"{rol}{contador['n']}@exemplo.gal")
        campos.setdefault("nome", f"Persoa {contador['n']}")
        if rol == Usuario.Rol.SUPERADMIN:
            return Usuario.objects.create_superuser(password=CONTRASINAL, **campos)
        return Usuario.objects.create_user(password=CONTRASINAL, rol=rol, **campos)

    return _crear


@pytest.fixture
def adoptante(crear_usuario):
    return crear_usuario(Usuario.Rol.ADOPTANTE)


@pytest.fixture
def usuario_protectora(crear_usuario):
    return crear_usuario(Usuario.Rol.PROTECTORA)


@pytest.fixture
def superadmin(crear_usuario):
    return crear_usuario(Usuario.Rol.SUPERADMIN)


@pytest.fixture(autouse=True)
def _contrasinais_rapidos(settings):
    """Nas probas usamos un hash de contrasinais rápido (o real é lento a propósito)."""
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@pytest.fixture
def concello(db):
    from compatibilidade.models import Concello

    return Concello.objects.create(
        codigo_ine=36057, nome="Vigo", provincia="Pontevedra", latitude=42.2406, lonxitude=-8.7207
    )


@pytest.fixture
def outro_concello(db):
    from compatibilidade.models import Concello

    return Concello.objects.create(
        codigo_ine=15078,
        nome="Santiago de Compostela",
        provincia="A Coruña",
        latitude=42.8782,
        lonxitude=-8.5448,
    )


@pytest.fixture
def crear_protectora(crear_usuario, concello):
    """Fábrica: crear_protectora(estado=...) devolve unha Protectora coa súa conta."""
    from contas.models import Protectora

    contador = {"n": 0}

    def _crear(estado=Protectora.Estado.ACTIVA, **campos):
        contador["n"] += 1
        usuario = crear_usuario(Usuario.Rol.PROTECTORA)
        campos.setdefault("nome", f"Protectora {contador['n']}")
        campos.setdefault("cif", f"G3600000{contador['n']}")
        campos.setdefault("concello", concello)
        campos.setdefault("telefono", "986000000")
        campos.setdefault("email_contacto", f"contacto{contador['n']}@protectora.gal")
        return Protectora.objects.create(usuario=usuario, estado=estado, **campos)

    return _crear


@pytest.fixture
def protectora(crear_protectora):
    """Unha protectora xa validada (activa)."""
    return crear_protectora()


@pytest.fixture(autouse=True)
def _media_temporal(settings, tmp_path):
    """As fotos subidas nas probas gárdanse nun directorio temporal."""
    settings.MEDIA_ROOT = tmp_path / "media"


@pytest.fixture
def crear_can(protectora):
    """Fábrica: crear_can(**campos) devolve un Can dispoñible con necesidades flexibles."""
    from datetime import date

    from animais.models import Can

    def _crear(**campos):
        campos.setdefault("protectora", protectora)
        campos.setdefault("nome", "Luna")
        campos.setdefault("sexo", Can.Sexo.FEMIA)
        campos.setdefault("data_nacemento", date(2023, 1, 15))
        campos.setdefault("tamano", "mediano")
        campos.setdefault("descricion", "Tranquila e cariñosa.")
        campos.setdefault("espazo", "indiferente")
        campos.setdefault("tolerancia_soidade", "media")
        campos.setdefault("convive_nenos", "si")
        campos.setdefault("convive_cans", "si")
        campos.setdefault("convive_gatos", "desconecido")
        campos.setdefault("enerxia", "medio")
        return Can.objects.create(**campos)

    return _crear
