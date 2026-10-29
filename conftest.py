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
