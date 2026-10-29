"""
Vistas da protectora para xestionar os seus cans.

Todas usan @require_protectora_activa: só entra unha protectora validada, e
request.protectora é a súa. Cada consulta filtra por esa protectora, así que unha
protectora nunca pode ver nin editar cans doutra (recibe un 404).
"""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from contas.decoradores import require_protectora_activa

from .forms import FormularioCan, FormularioFoto
from .models import Can, FotoCan


def _can_da_protectora(request, pk):
    return get_object_or_404(Can, pk=pk, protectora=request.protectora)


@require_protectora_activa
def lista(request):
    """Os cans da protectora agrupados por estado."""
    cans = request.protectora.cans.all().order_by("estado", "-data_publicacion")
    return render(request, "animais/protectora/lista.html", {"cans": cans, "seccion": "cans"})


@require_protectora_activa
def novo(request):
    formulario = FormularioCan(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        can = formulario.save(commit=False)
        can.protectora = request.protectora
        can.save()
        messages.success(request, f"Publicaches a ficha de {can.nome}. Engade agora as súas fotos.")
        return redirect("animais:protectora_fotos", pk=can.pk)
    return render(
        request, "animais/protectora/formulario.html", {"formulario": formulario, "seccion": "cans"}
    )


@require_protectora_activa
def editar(request, pk):
    can = _can_da_protectora(request, pk)
    formulario = FormularioCan(request.POST or None, instance=can)
    if request.method == "POST" and formulario.is_valid():
        formulario.save()
        messages.success(request, f"Gardaches os cambios de {can.nome}.")
        return redirect("animais:protectora_cans")
    return render(
        request,
        "animais/protectora/formulario.html",
        {"formulario": formulario, "can": can, "seccion": "cans"},
    )


@require_protectora_activa
@require_POST
def retirar(request, pk):
    """Retira un can dispoñible (deixa de verse). Non se pode se está reservado ou adoptado."""
    can = _can_da_protectora(request, pk)
    if not can.pode_retirarse:
        messages.error(request, f"{can.nome} ten unha adopción en curso e non se pode retirar.")
    else:
        can.estado = Can.Estado.RETIRADO
        can.save(update_fields=["estado", "data_actualizacion"])
        messages.success(request, f"Retiraches a {can.nome}.")
    return redirect("animais:protectora_cans")


@require_protectora_activa
@require_POST
def republicar(request, pk):
    """Volve publicar un can retirado."""
    can = _can_da_protectora(request, pk)
    if can.estado == Can.Estado.RETIRADO:
        can.estado = Can.Estado.DISPONIBLE
        can.save(update_fields=["estado", "data_actualizacion"])
        messages.success(request, f"{can.nome} volve estar publicado.")
    return redirect("animais:protectora_cans")


@require_protectora_activa
def fotos(request, pk):
    """Fotos dun can: subir, escoller a principal e borrar."""
    can = _can_da_protectora(request, pk)
    fotos_can = can.fotos.all()
    formulario = FormularioFoto(request.POST or None, request.FILES or None)
    if request.method == "POST":
        if fotos_can.count() >= FotoCan.MAXIMO_POR_CAN:
            messages.error(request, f"Cada can pode ter como moito {FotoCan.MAXIMO_POR_CAN} fotos.")
        elif formulario.is_valid():
            FotoCan.objects.create(
                can=can,
                imaxe=formulario.cleaned_data["imaxe"],
                principal=not fotos_can.exists(),  # a primeira foto é a principal
                orde=fotos_can.count(),
            )
            messages.success(request, "Engadiches a foto.")
            return redirect("animais:protectora_fotos", pk=can.pk)
    return render(
        request,
        "animais/protectora/fotos.html",
        {"can": can, "fotos": fotos_can, "formulario": formulario, "seccion": "cans"},
    )


@require_protectora_activa
@require_POST
def foto_principal(request, pk, foto_pk):
    can = _can_da_protectora(request, pk)
    foto = get_object_or_404(FotoCan, pk=foto_pk, can=can)
    can.fotos.update(principal=False)
    foto.principal = True
    foto.save(update_fields=["principal"])
    return redirect("animais:protectora_fotos", pk=can.pk)


@require_protectora_activa
@require_POST
def foto_borrar(request, pk, foto_pk):
    can = _can_da_protectora(request, pk)
    foto = get_object_or_404(FotoCan, pk=foto_pk, can=can)
    era_principal = foto.principal
    foto.imaxe.delete(save=False)  # borra tamén o ficheiro do disco
    foto.delete()
    if era_principal and (seguinte := can.fotos.first()):
        seguinte.principal = True
        seguinte.save(update_fields=["principal"])
    messages.success(request, "Borraches a foto.")
    return redirect("animais:protectora_fotos", pk=can.pk)
