"""
Carga datos de demostración para ver QueroCan funcionando.

    docker compose exec web python manage.py cargar_demo

Crea (sen duplicar se se executa varias veces):
  - os 313 concellos de Galicia, os compromisos do checklist e o contrato inicial;
  - unha conta superadmin, tres protectoras validadas e unha pendente;
  - 30 cans con fotos de dominio público (créditos en media/demo/LEEME.md);
  - tres persoas adoptantes con perfís moi distintos, para comprobar que a orde por
    compatibilidade ten sentido;
  - solicitudes en varios estados, para que o funil do superadmin teña datos;
  - testemuños de Finais felices e enlaces de interese.

Todas as contas teñen o contrasinal CONTRASINAL_DEMO.
"""

from datetime import date, timedelta
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from adopcions import contrato, estados
from adopcions.models import ModeloContrato, Solicitude
from animais.models import Can, FotoCan
from compatibilidade.models import Concello
from contas.models import PerfilAdoptante, Protectora, Usuario
from contido.models import Enlace, Testemuno

CONTRASINAL_DEMO = "querocan-demo"
DOMINIO = "demo.querocan.gal"
FOTOS = Path(settings.BASE_DIR) / "media" / "demo"

PROTECTORAS = [
    # clave, nome, CIF, concello (código INE), descrición
    (
        "palleiros",
        "Os Palleiros",
        "G36000001",
        36038,
        "Asociación de acollida e adopción de cans de Pontevedra.",
    ),
    (
        "compostela",
        "Patas Composteláns",
        "G15000002",
        15078,
        "Refuxio de cans abandonados na comarca de Santiago.",
    ),
    (
        "lugo",
        "Amigos do Miño",
        "G27000003",
        27028,
        "Protectora de animais de Lugo con casas de acollida.",
    ),
]

# Necesidades por defecto; cada can cambia só o que o fai especial
BASE_CAN = {
    "espazo": "indiferente",
    "tolerancia_soidade": "media",
    "convive_nenos": "si",
    "convive_cans": "si",
    "convive_gatos": "desconecido",
    "enerxia": "medio",
    "require_experiencia": False,
    "vacinado": True,
    "desparasitado": True,
    "microchip": True,
}

# nome, foto, protectora, sexo, idade (meses), tamaño, carácter, urxente, descrición, cambios
CANS = [
    (
        "Chispa",
        "01",
        "palleiros",
        "femia",
        26,
        "pequeno",
        "Alegre, Xogoneira",
        False,
        "Unha bóla de enerxía que adora correr detrás da pelota. Independente: leva ben "
        "quedar soa unhas horas.",
        {"tolerancia_soidade": "alta", "enerxia": "alto", "convive_gatos": "non"},
    ),
    (
        "Neve",
        "03",
        "palleiros",
        "femia",
        4,
        "mediano",
        "Cachorra, Curiosa",
        False,
        "Chegou á protectora con dous meses. Aprende rápido e lévase ben con todo o mundo.",
        {"tolerancia_soidade": "baixa", "convive_gatos": "si"},
    ),
    (
        "Trasno",
        "04",
        "compostela",
        "macho",
        5,
        "grande",
        "Cachorro, Forte",
        False,
        "Vai ser un can grande e con moita forza. Necesita unha familia con experiencia "
        "que o eduque con paciencia.",
        {"espazo": "patio_necesario", "enerxia": "alto", "require_experiencia": True},
    ),
    (
        "Canela",
        "05",
        "lugo",
        "femia",
        6,
        "mediano",
        "Cariñosa, Tímida",
        True,
        "Moi doce pero aínda tímida cos descoñecidos. Busca un fogar tranquilo.",
        {"convive_gatos": "si"},
    ),
    (
        "Bruno",
        "06",
        "palleiros",
        "macho",
        62,
        "grande",
        "Noble, Tranquilo",
        False,
        "Un xigante bo. Adora os nenos e durmir ao sol no xardín.",
        {"espazo": "patio_recomendado", "convive_gatos": "non"},
    ),
    (
        "Lúa",
        "07",
        "compostela",
        "femia",
        36,
        "mediano",
        "Intelixente, Activa",
        False,
        "Can pastor que necesita traballo mental e moito exercicio todos os días.",
        {"enerxia": "alto", "require_experiencia": True, "espazo": "patio_recomendado"},
    ),
    (
        "Sombra",
        "08",
        "lugo",
        "macho",
        30,
        "mediano",
        "Listo, Incansable",
        False,
        "Border collie que se aburre se non ten algo que facer. Ideal para xente deportista "
        "con casa e terreo.",
        {"espazo": "patio_necesario", "enerxia": "alto", "require_experiencia": True},
    ),
    (
        "Pinta",
        "09",
        "palleiros",
        "femia",
        74,
        "grande",
        "Tranquila, Sociable",
        False,
        "Dálmata adulta e moi equilibrada. Pasea ben coa correa e convive con gatos.",
        {"convive_gatos": "si"},
    ),
    (
        "Rufus",
        "11",
        "palleiros",
        "macho",
        48,
        "mediano",
        "Noble, Obediente",
        False,
        "Intelixente, doce e agarimoso pero tamén tímido e reservado. Prefire a compañía "
        "de persoas adultas.",
        {"convive_nenos": "desconecido"},
    ),
    (
        "Nina",
        "12",
        "compostela",
        "femia",
        14,
        "mediano",
        "Enérxica, Xogoneira",
        True,
        "Moza e chea de vida. Necesita paseos longos e alguén que xogue con ela.",
        {"enerxia": "alto", "tolerancia_soidade": "alta"},
    ),
    (
        "Oso",
        "13",
        "lugo",
        "macho",
        100,
        "grande",
        "Tranquilo, Maior",
        True,
        "Leva dous anos na protectora. Só pide unha manta, paseos tranquilos e cariño.",
        {"enerxia": "baixo", "convive_gatos": "si"},
    ),
    (
        "Café",
        "14",
        "compostela",
        "macho",
        16,
        "mediano",
        "Activo, Curioso",
        False,
        "Perdigueiro novo que necesita correr no monte cada día.",
        {"enerxia": "alto", "espazo": "patio_recomendado"},
    ),
    (
        "Luna",
        "15",
        "palleiros",
        "femia",
        38,
        "mediano",
        "Tranquila, Boa con nenos",
        True,
        "Tranquila e moi paciente cos nenos. Encántalle esconderse nos seus refuxios.",
        {"convive_gatos": "si"},
    ),
    (
        "Brisa",
        "17",
        "lugo",
        "femia",
        86,
        "grande",
        "Galga, Tranquila",
        False,
        "Galga retirada da caza. Dentro da casa é un sofá con patas.",
        {"enerxia": "baixo", "convive_gatos": "non", "tolerancia_soidade": "alta"},
    ),
    (
        "Mouro",
        "19",
        "compostela",
        "macho",
        40,
        "mediano",
        "Cariñoso, Xogón",
        False,
        "Can negro, que adoita ser o último en ser adoptado. Merece unha oportunidade.",
        {"convive_cans": "non"},
    ),
    (
        "Mel",
        "20",
        "palleiros",
        "femia",
        50,
        "grande",
        "Sociable, Boa con cans",
        False,
        "Sociable e risoña. Lévase ben con outros cans e con nenos.",
        {},
    ),
    (
        "Toxo",
        "21",
        "lugo",
        "macho",
        60,
        "grande",
        "Agarimoso, Teimudo",
        False,
        "Moi agarimoso coas persoas pero non tolera outros cans.",
        {"convive_cans": "non", "convive_gatos": "non", "require_experiencia": True},
    ),
    (
        "Xeada",
        "25",
        "compostela",
        "femia",
        70,
        "grande",
        "Independente, Activa",
        False,
        "Mestura de husky. Adora o frío e necesita moito exercicio.",
        {"enerxia": "alto", "espazo": "patio_necesario", "convive_gatos": "non"},
    ),
    (
        "Kiko",
        "26",
        "palleiros",
        "macho",
        28,
        "pequeno",
        "Independente, Limpo",
        False,
        "Pequeno, limpo e moi independente. Perfecto para un piso.",
        {"tolerancia_soidade": "alta", "convive_nenos": "desconecido"},
    ),
    (
        "Pirata",
        "28",
        "lugo",
        "macho",
        50,
        "mediano",
        "Leal, Vixiante",
        False,
        "Moi fiel á súa persoa. Necesita un tempo para coller confianza.",
        {},
    ),
    (
        "Sol",
        "30",
        "palleiros",
        "macho",
        110,
        "grande",
        "Maior, Tranquilo",
        True,
        "Golden de idade avanzada. Só quere pasar os seus últimos anos nun fogar.",
        {"enerxia": "baixo", "convive_gatos": "si", "tolerancia_soidade": "alta"},
    ),
    (
        "Lobo",
        "31",
        "compostela",
        "macho",
        64,
        "grande",
        "Protector, Obediente",
        False,
        "Pastor alemán adestrado. Necesita unha persoa con experiencia.",
        {"require_experiencia": True, "espazo": "patio_recomendado", "enerxia": "alto"},
    ),
    (
        "Cobre",
        "32",
        "lugo",
        "macho",
        34,
        "grande",
        "Alegre, Bo con nenos",
        False,
        "Sempre de bo humor. Encántanlle os nenos e as pelotas.",
        {"convive_gatos": "si"},
    ),
    (
        "Tito",
        "33",
        "palleiros",
        "macho",
        46,
        "grande",
        "Xogón, Bo con nenos",
        False,
        "Bóxer cheo de enerxía e paciencia cos pequenos da casa.",
        {"enerxia": "alto", "espazo": "patio_recomendado"},
    ),
    (
        "Pinto",
        "34",
        "compostela",
        "macho",
        3,
        "pequeno",
        "Cachorro, Xogón",
        False,
        "Cachorro que o rompe todo xogando. Necesita alguén na casa boa parte do día.",
        {"tolerancia_soidade": "baixa", "convive_gatos": "si"},
    ),
    (
        "Bico",
        "35",
        "lugo",
        "macho",
        24,
        "pequeno",
        "Curioso, Sociable",
        False,
        "Beagle que segue todos os rastros. Moi sociable con persoas e cans.",
        {"enerxia": "alto"},
    ),
    (
        "Fusco",
        "37",
        "palleiros",
        "macho",
        72,
        "mediano",
        "Tranquilo, Nobre",
        False,
        "Adulto tranquilo que se adapta a calquera rutina.",
        {"enerxia": "baixo", "tolerancia_soidade": "alta"},
    ),
    (
        "Nube",
        "39",
        "compostela",
        "femia",
        50,
        "grande",
        "Activa, Escapista",
        False,
        "Husky preciosa e moi escapista: necesita un patio ben pechado.",
        {"enerxia": "alto", "espazo": "patio_necesario", "require_experiencia": True},
    ),
    (
        "Cuca",
        "40",
        "lugo",
        "femia",
        84,
        "pequeno",
        "Tranquila, Cariñosa",
        False,
        "Pequena e tranquila, ideal para unha persoa maior. Convive con gatos.",
        {"enerxia": "baixo", "convive_gatos": "si", "tolerancia_soidade": "baixa"},
    ),
    (
        "Mimo",
        "42",
        "palleiros",
        "macho",
        124,
        "pequeno",
        "Maior, Cariñoso",
        True,
        "Yorkshire de dez anos que perdeu á súa dona. Busca colo e tranquilidade.",
        {
            "enerxia": "baixo",
            "convive_gatos": "si",
            "convive_nenos": "non",
            "tolerancia_soidade": "baixa",
        },
    ),
]

ADOPTANTES = [
    # clave, nome, concello, respostas do test
    (
        "estudante",
        "Antía (estudante nun piso)",
        36057,
        {
            "vivenda": "piso",
            "tamano": "pequeno",
            "horas_so": "de_4_a_6",
            "ten_nenos": False,
            "outros_animais": "ningun",
            "actividade": "alto",
            "experiencia": False,
        },
    ),
    (
        "familia",
        "Familia Castro (casa con nenos)",
        15078,
        {
            "vivenda": "casa_con_patio",
            "tamano": "indiferente",
            "horas_so": "de_2_a_4",
            "ten_nenos": True,
            "outros_animais": "cans",
            "actividade": "medio",
            "experiencia": True,
        },
    ),
    (
        "xubilada",
        "Rosa (xubilada)",
        27028,
        {
            "vivenda": "piso",
            "tamano": "pequeno",
            "horas_so": "menos_de_2",
            "ten_nenos": False,
            "outros_animais": "gatos",
            "actividade": "baixo",
            "experiencia": True,
        },
    ),
]

TESTEMUNOS = [
    (
        "Marta (42 anos)",
        "Russ",
        "marta-e-russ.jpg",
        "Sempre me gustaron os cans, pero cando me mudei co meu marido e os meus fillos ao "
        "campo sabiamos que non poderiamos convivir con calquera. En QueroCan atopamos a Russ, "
        "xusto o que precisabamos: coida da finca e segue o noso ritmo cando imos de sendeirismo.",
    ),
    (
        "Rosa (67 anos)",
        "Pupa",
        "rosa-e-pupa.jpg",
        "Desde que morreu o meu marido sentíame moi soa. Os meus fillos querían regalarme un "
        "can, pero eu negábame: criar un cachorro á miña idade? Coa compatibilidade de QueroCan "
        "atopei a Pupa, xa adulta, e agora as dúas somos felices xuntas.",
    ),
]

ENLACES = [
    (
        "Fundación Affinity",
        "https://www.fundacion-affinity.org",
        "Estudos e recursos sobre o vínculo entre persoas e animais.",
    ),
    ("Manual de boas maneiras de QueroCan", "/manual/", "Consellos para unha convivencia feliz."),
]


class Command(BaseCommand):
    help = "Carga datos de demostración (contas, protectoras, cans, solicitudes e contido)."

    @transaction.atomic
    def handle(self, *args, **options):
        call_command("loaddata", "concellos", verbosity=0)
        if not ModeloContrato.objects.exists():
            call_command("loaddata", "adopcion_inicial", verbosity=0)

        self.superadmin = self._conta("admin", "Equipo QueroCan", Usuario.Rol.SUPERADMIN)
        self.protectoras = {datos[0]: self._protectora(*datos) for datos in PROTECTORAS}
        self._protectora_pendente()
        self.cans = {datos[0]: self._can(*datos) for datos in CANS}
        self.adoptantes = {
            clave: self._adoptante(clave, nome, concello, respostas)
            for clave, nome, concello, respostas in ADOPTANTES
        }
        self._solicitudes()
        self._contido()

        self.stdout.write(self.style.SUCCESS("Datos de demostración listos."))
        self.stdout.write(f"Contrasinal de todas as contas: {CONTRASINAL_DEMO}")
        for usuario in Usuario.objects.filter(email__endswith=DOMINIO).order_by("rol", "email"):
            self.stdout.write(f"  {usuario.get_rol_display():<22} {usuario.email}")

    # --- Contas e protectoras ---------------------------------------------------------

    def _conta(self, clave, nome, rol):
        email = f"{clave}@{DOMINIO}"
        usuario = Usuario.objects.filter(email=email).first()
        if usuario is None:
            crear = (
                Usuario.objects.create_superuser
                if rol == Usuario.Rol.SUPERADMIN
                else Usuario.objects.create_user
            )
            extra = {} if rol == Usuario.Rol.SUPERADMIN else {"rol": rol}
            usuario = crear(email=email, password=CONTRASINAL_DEMO, nome=nome, **extra)
        return usuario

    def _protectora(self, clave, nome, cif, concello, descricion):
        usuario = self._conta(clave, nome, Usuario.Rol.PROTECTORA)
        protectora, _ = Protectora.objects.update_or_create(
            usuario=usuario,
            defaults={
                "nome": nome,
                "cif": cif,
                "concello": Concello.objects.get(pk=concello),
                "telefono": "986000000",
                "email_contacto": usuario.email,
                "descricion": descricion,
                "estado": Protectora.Estado.ACTIVA,
                "data_validacion": timezone.now(),
            },
        )
        return protectora

    def _protectora_pendente(self):
        usuario = self._conta("nova", "Refuxio Novo", Usuario.Rol.PROTECTORA)
        Protectora.objects.get_or_create(
            usuario=usuario,
            defaults={
                "nome": "Refuxio Novo",
                "cif": "G32000004",
                "concello": Concello.objects.get(pk=32054),
                "telefono": "988000000",
                "email_contacto": usuario.email,
            },
        )

    # --- Cans -------------------------------------------------------------------------

    def _can(self, nome, foto, protectora, sexo, meses, tamano, etiquetas, urxente, texto, cambios):
        datos = {
            **BASE_CAN,
            "sexo": sexo,
            "data_nacemento": date.today() - timedelta(days=round(meses * 30.4)),
            "tamano": tamano,
            "etiquetas": etiquetas,
            "urxente": urxente,
            "descricion": texto,
            **cambios,
        }
        can, creado = Can.objects.get_or_create(
            protectora=self.protectoras[protectora], nome=nome, defaults=datos
        )
        if not can.fotos.exists():
            with open(FOTOS / "cans" / f"{foto}.jpg", "rb") as ficheiro:
                FotoCan.objects.create(
                    can=can, imaxe=File(ficheiro, name=f"{foto}.jpg"), principal=True
                )
        return can

    # --- Adoptantes e solicitudes -----------------------------------------------------

    def _adoptante(self, clave, nome, concello, respostas):
        usuario = self._conta(clave, nome, Usuario.Rol.ADOPTANTE)
        lugar = Concello.objects.get(pk=concello)
        PerfilAdoptante.objects.update_or_create(
            usuario=usuario,
            defaults={
                **respostas,
                "concello": lugar,
                "latitude": lugar.latitude,
                "lonxitude": lugar.lonxitude,
            },
        )
        return usuario

    def _solicitudes(self):
        """Solicitudes en varios estados (só a primeira vez) para que o funil teña datos."""
        if Solicitude.objects.filter(adoptante__email__endswith=DOMINIO).exists():
            return
        a, c = self.adoptantes, self.cans
        protectora = {clave: p.usuario for clave, p in self.protectoras.items()}

        # Adopción completada: a familia adoptou a Bruno
        bruno = estados.crear_solicitude(a["familia"], c["Bruno"])
        estados.aceptar(bruno, protectora["palleiros"])
        estados.completar_checklist(bruno, a["familia"])
        contrato.aceptar(
            bruno,
            a["familia"],
            {
                "nome": "Iria Castro Vilar",
                "nif": "12345678Z",
                "enderezo": "Rúa do Vilar 3, Santiago",
                "telefono": "600123456",
                "email": a["familia"].email,
            },
        )

        # Match pendente de completar: a estudante con Kiko
        kiko = estados.crear_solicitude(a["estudante"], c["Kiko"])
        estados.aceptar(kiko, protectora["palleiros"])

        # Pendentes de revisar pola protectora
        estados.crear_solicitude(a["xubilada"], c["Mimo"])
        estados.crear_solicitude(a["xubilada"], c["Cuca"])
        estados.crear_solicitude(a["familia"], c["Tito"])

        # Rexeitada, retirada e caducada
        estados.rexeitar(estados.crear_solicitude(a["estudante"], c["Sombra"]), protectora["lugo"])
        estados.retirar(estados.crear_solicitude(a["familia"], c["Lúa"]), a["familia"])
        caducada = estados.aceptar(
            estados.crear_solicitude(a["estudante"], c["Nina"]), protectora["compostela"]
        )
        estados.caducar(caducada, timezone.now() + timedelta(days=estados.PRAZO_DIAS + 1))

    # --- Contido ----------------------------------------------------------------------

    def _contido(self):
        for orde, (persoa, can, foto, texto) in enumerate(TESTEMUNOS):
            testemuno, creado = Testemuno.objects.get_or_create(
                nome_persoa=persoa, nome_can=can, defaults={"texto": texto, "orde": orde}
            )
            if creado:
                with open(FOTOS / "testemunos" / foto, "rb") as ficheiro:
                    testemuno.foto.save(foto, File(ficheiro), save=True)
        for orde, (titulo, url, descricion) in enumerate(ENLACES):
            Enlace.objects.get_or_create(
                titulo=titulo, defaults={"url": url, "descricion": descricion, "orde": orde}
            )
