"""
Panel do superadmin.

Interface propia coa estética de QueroCan (non se usa o admin de Django). Só pode
entrar o rol superadmin.
"""

from django.contrib import messages
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Count, Max, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from adopcions.models import ItemChecklist, ModeloContrato, Solicitude
from animais.models import Can
from contas.decoradores import require_rol
from contas.models import Protectora, Usuario
from contido.models import Enlace, Testemuno

from . import metricas
from .forms import (
    FormularioContrato,
    FormularioEnlace,
    FormularioItemChecklist,
    FormularioPeriodo,
    FormularioTestemuno,
)

so_superadmin = require_rol(Usuario.Rol.SUPERADMIN)


@so_superadmin
def inicio(request):
    """Portada do panel: resumo e accesos ás seccións."""
    resumo = {
        "pendentes": Protectora.objects.filter(
            estado=Protectora.Estado.PENDENTE_VALIDACION
        ).count(),
        "protectoras": Protectora.objects.filter(estado=Protectora.Estado.ACTIVA).count(),
        "cans": Can.objects.filter(estado=Can.Estado.DISPONIBLE).count(),
        "adoptantes": Usuario.objects.filter(rol=Usuario.Rol.ADOPTANTE).count(),
        "activas": Solicitude.objects.filter(estado__in=Solicitude.ACTIVAS).count(),
        "adopcions": Solicitude.objects.filter(estado=Solicitude.Estado.COMPLETADA).count(),
    }
    return render(request, "xestion/inicio.html", {**resumo, "seccion": "inicio"})


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


# ---------------------------------------------------------------------------------------
# Usuarios
# ---------------------------------------------------------------------------------------


@so_superadmin
def usuarios(request):
    """Busca de usuarios por nome ou correo e filtro por rol."""
    consulta = Usuario.objects.order_by("-date_joined")
    busca = request.GET.get("q", "").strip()
    if busca:
        consulta = consulta.filter(Q(nome__icontains=busca) | Q(email__icontains=busca))
    rol = request.GET.get("rol")
    if rol in Usuario.Rol.values:
        consulta = consulta.filter(rol=rol)
    return render(
        request,
        "xestion/usuarios.html",
        {
            "usuarios": consulta[:200],
            "busca": busca,
            "rol": rol,
            "roles": Usuario.Rol.choices,
            "seccion": "usuarios",
        },
    )


@so_superadmin
@require_POST
def cambiar_activo_usuario(request, pk):
    """Activa ou desactiva unha conta. Unha conta desactivada non pode entrar."""
    usuario = get_object_or_404(Usuario, pk=pk)
    if usuario == request.user:
        messages.error(request, "Non podes desactivar a túa propia conta.")
    else:
        usuario.is_active = not usuario.is_active
        usuario.save(update_fields=["is_active"])
        # Se é unha protectora, os seus cans deixan de verse ao desactivala
        protectora = getattr(usuario, "protectora", None)
        if protectora is not None and not usuario.is_active:
            protectora.estado = Protectora.Estado.DESACTIVADA
            protectora.save(update_fields=["estado"])
        estado = "activada" if usuario.is_active else "desactivada"
        messages.success(request, f"Conta de {usuario.nome} {estado}.")
    return redirect(request.POST.get("volver") or "xestion:usuarios")


# ---------------------------------------------------------------------------------------
# Funil de métricas
# ---------------------------------------------------------------------------------------


@so_superadmin
def funil(request):
    """Funil de adopción (gráfica + táboa) por protectora e período."""
    formulario = FormularioPeriodo(request.GET or None)
    protectora = desde = ata = None
    if formulario.is_valid():
        protectora = formulario.cleaned_data["protectora"]
        desde = formulario.cleaned_data["desde"]
        ata = formulario.cleaned_data["ata"]
    datos = metricas.funil(protectora, desde, ata)
    protectoras = (
        [protectora] if protectora else Protectora.objects.filter(estado=Protectora.Estado.ACTIVA)
    )
    return render(
        request,
        "xestion/funil.html",
        {
            "formulario": formulario,
            "funil": datos,
            "por_protectora": metricas.funil_por_protectora(protectoras, desde, ata),
            "datos_grafica": {
                "etiquetas": [e["nome"] for e in datos["etapas"]],
                "valores": [e["total"] for e in datos["etapas"]],
            },
            "seccion": "funil",
        },
    )


# ---------------------------------------------------------------------------------------
# Contido editable: testemuños, enlaces, checklist e contrato
# ---------------------------------------------------------------------------------------

# Cada tipo de contido: modelo, formulario, nome en plural e campo que se amosa na lista
CONTIDOS = {
    "testemunos": (Testemuno, FormularioTestemuno, "Testemuños (Finais felices)"),
    "enlaces": (Enlace, FormularioEnlace, "Enlaces de interese"),
    "checklist": (ItemChecklist, FormularioItemChecklist, "Compromisos do checklist"),
}


def _tipo_contido(tipo):
    if tipo not in CONTIDOS:
        raise Http404
    return CONTIDOS[tipo]


@so_superadmin
def contido_lista(request, tipo):
    modelo, _, titulo = _tipo_contido(tipo)
    return render(
        request,
        "xestion/contido_lista.html",
        {"obxectos": modelo.objects.all(), "titulo": titulo, "tipo": tipo, "seccion": tipo},
    )


@so_superadmin
def contido_editar(request, tipo, pk=None):
    modelo, Formulario, titulo = _tipo_contido(tipo)
    obxecto = get_object_or_404(modelo, pk=pk) if pk else None
    formulario = Formulario(request.POST or None, request.FILES or None, instance=obxecto)
    if request.method == "POST" and formulario.is_valid():
        formulario.save()
        messages.success(request, "Gardado.")
        return redirect("xestion:contido_lista", tipo=tipo)
    return render(
        request,
        "xestion/contido_formulario.html",
        {
            "formulario": formulario,
            "titulo": titulo,
            "tipo": tipo,
            "obxecto": obxecto,
            "seccion": tipo,
        },
    )


@so_superadmin
@require_POST
def contido_borrar(request, tipo, pk):
    modelo, _, _ = _tipo_contido(tipo)
    get_object_or_404(modelo, pk=pk).delete()
    messages.success(request, "Borrado.")
    return redirect("xestion:contido_lista", tipo=tipo)


@so_superadmin
def contrato(request):
    """Modelo de contrato: ao gardar créase unha versión nova e pasa a ser a activa."""
    actual = ModeloContrato.actual()
    formulario = FormularioContrato(
        request.POST or None, initial={"texto": actual.texto if actual else ""}
    )
    if request.method == "POST" and formulario.is_valid():
        with transaction.atomic():
            ultima = ModeloContrato.objects.aggregate(Max("version"))["version__max"] or 0
            ModeloContrato.objects.update(activo=False)
            ModeloContrato.objects.create(
                version=ultima + 1, texto=formulario.cleaned_data["texto"], activo=True
            )
        messages.success(request, f"Gardaches a versión {ultima + 1} do contrato.")
        return redirect("xestion:contrato")
    return render(
        request,
        "xestion/contrato.html",
        {
            "formulario": formulario,
            "actual": actual,
            "versions": ModeloContrato.objects.annotate(usos=Count("aceptacions")),
            "seccion": "contrato",
        },
    )
