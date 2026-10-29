from django.apps import AppConfig


class CompatibilidadeConfig(AppConfig):
    """Cálculo de compatibilidade, distancia, test e concellos."""

    name = "compatibilidade"
    verbose_name = "Compatibilidade"

    def ready(self):
        # Ao entrar ou crear conta, o test feito sen conta pasa ao perfil
        from django.contrib.auth.signals import user_logged_in

        from .perfil import transferir_sesion

        def _ao_entrar(sender, request, user, **kwargs):
            if request is not None:
                transferir_sesion(request, user)

        # weak=False: a función é local e, se non, o recolector de lixo borraríaa
        user_logged_in.connect(_ao_entrar, weak=False, dispatch_uid="querocan_transferir_test")
