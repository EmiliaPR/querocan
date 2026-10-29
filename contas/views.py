"""
Vistas de contas: entrar, saír, crear conta e recuperar o contrasinal.
"""

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme

from .decoradores import require_rol
from .forms import FormularioEntrada, FormularioProtectora, FormularioRexistro
from .models import Usuario


def destino_tras_entrar(usuario):
    """Páxina á que vai cada rol despois de entrar (se non viña doutra páxina)."""
    if usuario.es_superadmin:
        return reverse("xestion:inicio")
    if usuario.es_protectora:
        return reverse("animais:protectora_cans")
    return reverse("animais:deck")


def _seguinte_seguro(request):
    """Devolve o parámetro ?next= só se apunta a este mesmo sitio (evita redireccións abertas)."""
    seguinte = request.POST.get("next") or request.GET.get("next")
    if seguinte and url_has_allowed_host_and_scheme(
        seguinte, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return seguinte
    return None


class Entrar(auth_views.LoginView):
    """Formulario de entrada co correo electrónico."""

    template_name = "contas/entrar.html"
    authentication_form = FormularioEntrada
    redirect_authenticated_user = True

    def get_success_url(self):
        return _seguinte_seguro(self.request) or destino_tras_entrar(self.request.user)


class Sair(auth_views.LogoutView):
    """Pecha a sesión (só por POST, como esixe Django) e volve á landing."""

    next_page = reverse_lazy("contido:landing")


def rexistro(request):
    """Crear conta. As protectoras continúan cun segundo paso cos datos da entidade."""
    if request.user.is_authenticated:
        return redirect(destino_tras_entrar(request.user))

    formulario = FormularioRexistro(
        request.POST or None, rol_inicial=request.GET.get("rol", Usuario.Rol.ADOPTANTE)
    )
    if request.method == "POST" and formulario.is_valid():
        usuario = formulario.save()
        login(request, usuario, backend="django.contrib.auth.backends.ModelBackend")
        if usuario.es_protectora:
            return redirect("contas:alta_protectora")
        messages.success(request, f"Benvida/o a QueroCan, {usuario.nome}!")
        return redirect(_seguinte_seguro(request) or destino_tras_entrar(usuario))

    return render(request, "contas/rexistro.html", {"formulario": formulario})


@require_rol(Usuario.Rol.PROTECTORA)
def alta_protectora(request):
    """Segundo paso do rexistro: datos da entidade. Despois queda pendente de validación."""
    if hasattr(request.user, "protectora"):
        return redirect("animais:protectora_cans")

    formulario = FormularioProtectora(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        protectora = formulario.save(commit=False)
        protectora.usuario = request.user
        protectora.save()
        avisar_superadmins_protectora_nova(protectora)
        return redirect("animais:protectora_cans")
    return render(request, "contas/alta_protectora.html", {"formulario": formulario})


def avisar_superadmins_protectora_nova(protectora):
    """Envía un correo ás persoas superadmin para que validen a protectora nova."""
    destinatarios = list(
        Usuario.objects.filter(rol=Usuario.Rol.SUPERADMIN, is_active=True).values_list(
            "email", flat=True
        )
    )
    if destinatarios:
        send_mail(
            "QueroCan: nova protectora pendente de validación",
            f"A protectora «{protectora.nome}» ({protectora.concello.nome}) rexistrouse e "
            "agarda a túa validación no panel de xestión.",
            None,
            destinatarios,
        )


# Recuperación do contrasinal: usamos as vistas de Django coas nosas plantillas
recuperar = auth_views.PasswordResetView.as_view(
    template_name="contas/recuperar.html",
    email_template_name="contas/correo_recuperar.txt",
    subject_template_name="contas/correo_recuperar_asunto.txt",
    success_url=reverse_lazy("contas:recuperar_enviado"),
)
recuperar_enviado = auth_views.PasswordResetDoneView.as_view(
    template_name="contas/recuperar_enviado.html"
)
recuperar_confirmar = auth_views.PasswordResetConfirmView.as_view(
    template_name="contas/recuperar_confirmar.html",
    success_url=reverse_lazy("contas:recuperar_feito"),
)
recuperar_feito = auth_views.PasswordResetCompleteView.as_view(
    template_name="contas/recuperar_feito.html"
)
