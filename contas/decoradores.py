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


def require_protectora_activa(vista):
    """Só para protectoras xa validadas polo superadmin.

    - Se a conta aínda non completou os datos da protectora, mándaa a facelo.
    - Se está pendente de validación (ou rexeitada/desactivada), amósalle o seu estado.
    A vista recibe a protectora en `request.protectora`.
    """
    from django.shortcuts import redirect, render

    from .models import Usuario

    @require_rol(Usuario.Rol.PROTECTORA)
    @wraps(vista)
    def envoltorio(request, *args, **kwargs):
        protectora = getattr(request.user, "protectora", None)
        if protectora is None:
            return redirect("contas:alta_protectora")
        if not protectora.activa:
            return render(request, "contas/protectora_estado.html", {"protectora": protectora})
        request.protectora = protectora
        return vista(request, *args, **kwargs)

    return envoltorio
