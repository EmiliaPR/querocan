"""
Control de acceso por rol.

Cada vista privada decórase con @require_rol indicando que roles poden entrar:

    @require_rol(Usuario.Rol.PROTECTORA)
    def os_meus_cans(request): ...

Se a persoa non entrou, mándase ao formulario de entrada (e despois volve á vista).
Se entrou pero co rol equivocado, recibe un erro 403 (acceso denegado).
"""

from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied


def require_rol(*roles):
    """Permite o acceso só ás persoas que entraron cun dos `roles` indicados."""

    def decorador(vista):
        @wraps(vista)
        def envoltorio(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if request.user.rol not in roles:
                raise PermissionDenied("Esta sección non está dispoñible para a túa conta.")
            return vista(request, *args, **kwargs)

        return envoltorio

    return decorador
