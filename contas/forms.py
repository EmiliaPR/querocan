"""Formularios de rexistro e entrada."""

from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm

from .models import Usuario


class FormularioRexistro(forms.ModelForm):
    """Alta dunha conta nova. A persoa escolle se é adoptante ou protectora («Son…»)."""

    ROLES_PERMITIDOS = [
        (Usuario.Rol.ADOPTANTE, "Persoa que quere adoptar"),
        (Usuario.Rol.PROTECTORA, "Protectora"),
    ]

    password = forms.CharField(
        label="Contrasinal",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="Polo menos 8 caracteres; non pode ser só números nin moi común.",
    )
    rol = forms.ChoiceField(label="Son…", choices=ROLES_PERMITIDOS, widget=forms.RadioSelect)
    acepta_privacidade = forms.BooleanField(
        label="Acepto a política de privacidade",
        error_messages={"required": "Tes que aceptar a política de privacidade."},
    )

    class Meta:
        model = Usuario
        fields = ["nome", "email", "password", "rol"]
        widgets = {
            "nome": forms.TextInput(attrs={"autocomplete": "name"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
        }

    def __init__(self, *args, rol_inicial=None, **kwargs):
        super().__init__(*args, **kwargs)
        if rol_inicial:
            self.fields["rol"].initial = rol_inicial

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if Usuario.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Xa hai unha conta con ese correo.")
        return email

    def clean(self):
        datos = super().clean()
        contrasinal = datos.get("password")
        if contrasinal:
            # Validamos co usuario provisional para detectar contrasinais parecidos ao nome
            provisional = Usuario(email=datos.get("email", ""), nome=datos.get("nome", ""))
            try:
                password_validation.validate_password(contrasinal, provisional)
            except forms.ValidationError as erro:
                self.add_error("password", erro)
        return datos

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.set_password(self.cleaned_data["password"])
        if commit:
            usuario.save()
        return usuario


class FormularioEntrada(AuthenticationForm):
    """Entrada co correo e o contrasinal (o campo «username» de Django é o correo)."""

    username = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={"autocomplete": "email", "autofocus": True}),
    )
    error_messages = {
        "invalid_login": "O correo ou o contrasinal non son correctos.",
        "inactive": "Esta conta está desactivada.",
    }
