"""
Onde vive o perfil de compatibilidade e a localización de cada persoa.

- Se a persoa entrou cunha conta de adoptante, gárdanse no seu PerfilAdoptante.
- Se é un visitante, gárdanse na sesión. Cando cree a conta ou entre, pásanse ao
  perfil (función `transferir_sesion`), así non ten que repetir o test.

O resto da aplicación só usa `perfil_de(request)` e `localizacion_de(request)` e non
precisa saber de onde saen os datos.
"""

from dataclasses import asdict

from compatibilidade.calculo import (
    HorasSo,
    Nivel,
    OutrosAnimais,
    PerfilAdoptante,
    PreferenciaTamano,
    Vivenda,
)

CLAVE_TEST = "perfil_test"
CLAVE_LOCALIZACION = "localizacion"


def _perfil_modelo(request):
    """PerfilAdoptante (modelo) da persoa que entrou, ou None."""
    usuario = request.user
    if usuario.is_authenticated and usuario.es_adoptante:
        return getattr(usuario, "perfil", None)
    return None


def perfil_de(request) -> PerfilAdoptante | None:
    """Perfil para o cálculo de compatibilidade (da conta ou da sesión), ou None."""
    modelo = _perfil_modelo(request)
    if modelo is not None:
        return modelo.como_perfil()
    datos = request.session.get(CLAVE_TEST)
    return perfil_desde_dict(datos) if datos else None


def perfil_desde_dict(datos) -> PerfilAdoptante:
    return PerfilAdoptante(
        vivenda=Vivenda(datos["vivenda"]),
        tamano=PreferenciaTamano(datos["tamano"]),
        horas_so=HorasSo(datos["horas_so"]),
        ten_nenos=bool(datos["ten_nenos"]),
        outros_animais=OutrosAnimais(datos["outros_animais"]),
        actividade=Nivel(datos["actividade"]),
        experiencia=bool(datos["experiencia"]),
    )


def gardar_perfil(request, perfil: PerfilAdoptante):
    """Garda as respostas do test na conta (se é adoptante) ou na sesión."""
    from contas.models import PerfilAdoptante as Modelo

    datos = {
        clave: (valor.value if hasattr(valor, "value") else valor)
        for clave, valor in asdict(perfil).items()
    }
    usuario = request.user
    if usuario.is_authenticated and usuario.es_adoptante:
        Modelo.objects.update_or_create(usuario=usuario, defaults=datos)
        request.session.pop(CLAVE_TEST, None)
    else:
        request.session[CLAVE_TEST] = datos


def localizacion_de(request):
    """(latitude, lonxitude) da persoa, ou None se aínda non a indicou."""
    modelo = _perfil_modelo(request)
    if modelo is not None and modelo.latitude is not None:
        return modelo.latitude, modelo.lonxitude
    datos = request.session.get(CLAVE_LOCALIZACION)
    if datos:
        return datos["latitude"], datos["lonxitude"]
    return None


def descricion_localizacion(request):
    """Texto para a interface: «Vigo» ou «A túa localización» (GPS), ou None."""
    modelo = _perfil_modelo(request)
    if modelo is not None and modelo.latitude is not None:
        return modelo.concello.nome if modelo.concello else "A túa localización"
    datos = request.session.get(CLAVE_LOCALIZACION)
    return datos.get("descricion") if datos else None


def gardar_localizacion(request, latitude, lonxitude, concello=None):
    """Garda a localización na conta (se ten perfil) e sempre na sesión."""
    descricion = concello.nome if concello else "A túa localización"
    request.session[CLAVE_LOCALIZACION] = {
        "latitude": latitude,
        "lonxitude": lonxitude,
        "descricion": descricion,
    }
    modelo = _perfil_modelo(request)
    if modelo is not None:
        modelo.latitude, modelo.lonxitude, modelo.concello = latitude, lonxitude, concello
        modelo.save(update_fields=["latitude", "lonxitude", "concello", "data_actualizacion"])


def transferir_sesion(request, usuario):
    """Ao entrar ou crear conta: pasa o test e a localización da sesión ao perfil."""
    from contas.models import PerfilAdoptante as Modelo

    if not usuario.es_adoptante:
        return
    datos = request.session.pop(CLAVE_TEST, None)
    if datos:
        Modelo.objects.update_or_create(usuario=usuario, defaults=datos)
    localizacion = request.session.get(CLAVE_LOCALIZACION)
    perfil = getattr(usuario, "perfil", None) if not datos else Modelo.objects.get(usuario=usuario)
    if localizacion and perfil is not None and perfil.latitude is None:
        perfil.latitude = localizacion["latitude"]
        perfil.lonxitude = localizacion["lonxitude"]
        perfil.save(update_fields=["latitude", "lonxitude", "data_actualizacion"])
