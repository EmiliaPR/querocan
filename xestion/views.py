"""
Panel do superadmin.

Interface propia coa estética de QueroCan (non se usa o admin de Django). Só pode
entrar o rol superadmin.
"""

from django.contrib import messages
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from contas.decoradores import require_rol
from contas.models import Protectora, Usuario

so_superadmin = require_rol(Usuario.Rol.SUPERADMIN)


@so_superadmin
def inicio(request):
    """Portada do panel: resumo e accesos ás seccións."""
    pendentes = Protectora.objects.filter(estado=Protectora.Estado.PENDENTE_VALIDACION).count()
    return render(request, "xestion/inicio.html", {"pendentes": pendentes, "seccion": "inicio"})


@so_superadmin
def protectoras(request):
    """Listado de protectoras con filtro por estado (por defecto, as pendentes)."""
    estado = request.GET.get("estado", Protectora.Estado.PENDENTE_VALIDACION)
    consulta = Protectora.objects.select_related("concello", "usuario")
    if estado != "todas":
        consulta = consulta.filter(estado=estado)
    return render(
        request,
        "xestion/protectoras.html",
        {
            "protectoras": consulta,
            "estado": estado,
            "estados": Protectora.Estado.choices,
            "seccion": "protectoras",
        },
    )


@so_superadmin
@require_POST
def cambiar_estado_protectora(request, pk, accion):
    """Valida, rexeita, desactiva ou reactiva unha protectora e avisa por correo."""
    protectora = get_object_or_404(Protectora, pk=pk)
    novos_estados = {
        "validar": Protectora.Estado.ACTIVA,
        "rexeitar": Protectora.Estado.REXEITADA,
        "desactivar": Protectora.Estado.DESACTIVADA,
        "reactivar": Protectora.Estado.ACTIVA,
    }
    if accion not in novos_estados:
        return redirect("xestion:protectoras")

    protectora.estado = novos_estados[accion]
    if accion == "validar":
        protectora.data_validacion = timezone.now()
    protectora.save()
    _avisar_protectora(protectora, accion)
    messages.success(request, f"{protectora.nome}: {protectora.get_estado_display().lower()}.")
    return redirect(request.POST.get("volver") or "xestion:protectoras")


def _avisar_protectora(protectora, accion):
    textos = {
        "validar": "A túa protectora xa está validada en QueroCan. Xa podes publicar os teus cans.",
        "reactivar": "A túa protectora volve estar activa en QueroCan.",
        "rexeitar": "Non puidemos validar a túa protectora en QueroCan. Contacta connosco "
        "se cres que é un erro.",
        "desactivar": "A túa protectora foi desactivada en QueroCan. Contacta connosco para "
        "máis información.",
    }
    send_mail(
        f"QueroCan: {protectora.nome}",
        textos[accion],
        None,
        [protectora.usuario.email],
    )
