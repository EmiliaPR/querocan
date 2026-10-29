# Spec: QueroCan

> Documento vivo. Se unha decisión cambia, actualízase aquí **antes** de tocar o código.
> Orixe: `docs/ideas/querocan.md` (idea refinada e decisións) e
> `docs/referencias/QueroCan-proposta-identidade-grafica.html` (identidade visual).

## Objective

QueroCan é unha plataforma web de adopción de cans, *mobile-first*, que xunta protectoras e
persoas adoptantes. Funciona coma unha app de citas: a persoa adoptante ve unha ficha a pantalla
completa e desliza á dereita ("Gústame") ou á esquerda ("Non é para min"). As fichas ordénanse
por **compatibilidade explicable** entre as condicións de vida da persoa e as necesidades do can.
O fluxo complétase dentro da plataforma: solicitude → aceptación da protectora (*match*) →
checklist de responsabilidade → contrato.

**Contexto:** proxecto académico. O tribunal avalía que o fluxo funcione de punta a punta cos
tres roles e que o código, comentado en galego, sexa doado de explorar por unha persoa allea.

### Roles e historias de usuario

**Visitante (sen conta)**
- V1. Ve a landing, o listado de cans, as fichas, *Finais felices*, o Manual de boas maneiras e
  os Enlaces de interese.
  - *Aceptación:* ningunha destas páxinas pide autenticación.
- V2. Fai o test de compatibilidade sen conta.
  - *Aceptación:* as respostas gárdanse na sesión; o resultado amosa os 3 cans máis compatibles
    con porcentaxe e motivos; ao crear conta, as respostas pasan ao perfil sen repetir o test.
- V3. Usa o deck de tarxetas.
  - *Aceptación:* pode descartar (esquerda); ao deslizar á dereita ou pulsar "Adoptar" aparece
    un aviso que o leva a entrar ou crear conta, e o can queda pendente de solicitar tras o login.

**Adoptante**
- A1. Rexístrase escollendo o rol "Persoa que quere adoptar" e acepta a política de privacidade.
- A2. Completa ou edita o seu perfil de compatibilidade (as 6 dimensións do test) e a súa
  localización (GPS do navegador ou concello).
  - *Aceptación:* sen perfil completo non pode enviar solicitudes; o sistema indícao e leva ao test.
- A3. Explora o deck ordenado por compatibilidade (desc.) e filtrable por distancia (25/50/100 km
  ou calquera), tamaño, idade e "só urxentes".
  - *Aceptación:* cada tarxeta amosa nome, idade, distancia, protectora, etiquetas de carácter,
    porcentaxe e ata 3 motivos (✓ encaixe / ⚠ aviso). Os cans xa decididos non volven aparecer.
  - *Aceptación:* xesto e botóns fan o mesmo (← "Non é para min", → "Gústame", ↑ "Ver ficha",
    Z "Desfacer"); funciona con rato, táctil e teclado.
- A4. Alterna entre vista de tarxetas e de grella.
- A5. Desliza á dereita / pulsa "Adoptar" → créase unha solicitude `PENDENTE`.
- A6. Ve "As miñas solicitudes" co estado de cada unha e pode retirar as `PENDENTE`/`EN_ESPERA`.
- A7. Cando unha solicitude está `ACEPTADA`: completa o checklist de responsabilidade e despois
  acepta o contrato (nome, NIF, enderezo, teléfono, correo) dentro do prazo de 7 días.
  - *Aceptación:* tras aceptar, pode descargar o contrato en PDF; a solicitude pasa a `COMPLETADA`.
- A8. Pulsa "Apadriñar", o filtro "Acollida" ou o corazón de favoritos → amósase a mensaxe
  "Esta funcionalidade aínda non está implementada". Non se garda nada.

**Protectora**
- P1. Rexístrase co rol "Protectora" (nome, CIF, concello, contacto). Queda `PENDENTE_VALIDACION`
  e non pode publicar ata que o superadmin a valide.
- P2. Crea, edita e retira cans: datos básicos, fotos (1 principal + ata 5), etiquetas de
  carácter, urxente, descrición e as **necesidades** nas 6 dimensións (todas obrigatorias,
  con "indiferente" como valor explícito).
- P3. Ve o panel de solicitudes (lista filtrable por can e estado) coa compatibilidade e os
  motivos de cada adoptante; acepta ou rexeita.
- P4. Pode cancelar unha solicitude `ACEPTADA` antes de que se complete.

**Superadmin**
- S1. Valida ou rexeita protectoras pendentes; pode desactivar protectoras e usuarios.
- S2. Ve o funil por protectora e período: solicitudes → aceptadas → checklist → contratos
  (completadas), máis caducadas/canceladas (gráficas con Chart.js).
- S3. Xestiona o contido estático: testemuños de *Finais felices*, enlaces de interese,
  modelo de contrato (versionado) e elementos do checklist.

## Domain

### Máquina de estados

**Can:** `DISPONIBLE` → `RESERVADO` → `ADOPTADO`; `RESERVADO` → `DISPONIBLE` (caducidade ou
cancelación); calquera → `RETIRADO` (pola protectora, se non hai solicitude `ACEPTADA`).

**Solicitude:**

| Desde | Evento | Ata | Efectos |
|---|---|---|---|
| — | adoptante desliza á dereita / "Adoptar" | `PENDENTE` | aviso por correo á protectora |
| `PENDENTE` | protectora acepta | `ACEPTADA` | can → `RESERVADO`; outras `PENDENTE` do can → `EN_ESPERA`; empeza o prazo de 7 días |
| `PENDENTE` / `EN_ESPERA` | protectora rexeita | `REXEITADA` | — |
| `PENDENTE` / `EN_ESPERA` | adoptante retira | `CANCELADA` | — |
| `ACEPTADA` | adoptante completa checklist | `ACEPTADA` (con `data_checklist`) | habilita o contrato |
| `ACEPTADA` + checklist | adoptante acepta contrato | `COMPLETADA` | can → `ADOPTADO`; `EN_ESPERA` do can → `REXEITADA` |
| `ACEPTADA` | pasan 7 días | `CADUCADA` | can → `DISPONIBLE`; `EN_ESPERA` → `PENDENTE` |
| `ACEPTADA` | protectora ou adoptante cancela | `CANCELADA` | can → `DISPONIBLE`; `EN_ESPERA` → `PENDENTE` |

- Toda transición pasa por **un único módulo** (`adopcions/estados.py`) dentro dunha transacción
  (`transaction.atomic` + `select_for_update` sobre o can). As vistas nunca cambian `estado` directamente.
- Unha persoa só pode ter unha solicitude activa (`PENDENTE`/`EN_ESPERA`/`ACEPTADA`) por can.
- Cada transición rexístrase en `HistorialSolicitude` (estado anterior, novo, quen, cando) para o
  funil e para depurar.
- Desliza á esquerda → `Descarte` (adoptante, can). "Desfacer" elimina a última decisión do
  deck (descarte ou solicitude aínda `PENDENTE`).

### Compatibilidade

Función pura en `compatibilidade/calculo.py`: recibe un perfil de adoptante e as necesidades dun
can (obxectos simples, sen ORM) e devolve `Resultado(porcentaxe: int, motivos: list[Motivo])`.

| Dimensión | Adoptante | Can | Peso |
|---|---|---|---|
| Vivenda | piso / casa sen patio / casa con patio | espazo: indiferente / patio recomendado / patio necesario | 3 |
| Tamaño | pequeno / mediano / grande / indiferente | pequeno / mediano / grande | 1 |
| Horas só | < 2 / 2–4 / 4–6 / > 6 | tolerancia á soidade: baixa / media / alta | 3 |
| Nenos | si / non | convive con nenos: si / non / descoñecido | 3 |
| Outros animais | ningún / cans / gatos / cans e gatos | convive con cans e con gatos: si / non / descoñecido | 2 |
| Actividade e experiencia | actividade baixa / media / alta + experiencia previa si / non | enerxía baixa / media / alta + require experiencia si / non | 2 |

- Cada dimensión puntúa 0, 0,5 ou 1; porcentaxe = Σ(peso × puntos) / Σ(pesos) × 100, redondeado.
- **Incompatibilidade forte** (p. ex. o can non convive con nenos e hai nenos; patio necesario e
  vive en piso): a porcentaxe límitase a 40 % máximo e o motivo márcase ⚠.
- Os pesos e as regras son constantes nomeadas no mesmo módulo, comentadas unha a unha.
- Quen non fixo o test ve o deck ordenado por urxencia e distancia, sen porcentaxe.

### Distancia

Protectoras e adoptantes gardan latitude e lonxitude. A localización do adoptante vén do GPS do
navegador ou dun concello escollido dunha lista (fixture cos 313 concellos de Galicia e as súas
coordenadas). A distancia calcúlase con Haversine en Python (`compatibilidade/distancia.py`) sobre
os cans xa filtrados; non se usan mapas.

### Contrato

- `ModeloContrato`: texto común (as 7 cláusulas da referencia, con marcadores para os datos),
  versionado; só hai un activo e é editable polo superadmin.
- `AceptacionContrato`: copia exacta do texto final aceptado, versión do modelo, hash SHA-256
  dese texto, datos do adoptante, data e IP. Non se modifica nunca despois de creada.
- PDF xerado baixo demanda con WeasyPrint a partir da mesma plantilla HTML.
- Limitación documentada: non é unha sinatura dixital con validez legal plena.

## Tech Stack

| Peza | Versión | Notas |
|---|---|---|
| Python | 3.12 | |
| Django | 5.2 LTS | plantillas no servidor, auth de sesión |
| MySQL | 8.4 LTS | conector `mysqlclient` |
| WeasyPrint | 66.x | PDF do contrato |
| Pillow | última estable | requirida por `ImageField`; redimensionado de fotos |
| Gunicorn + WhiteNoise | últimas estables | só en produción |
| Caddy | 2.x | HTTPS e ficheiros media na demo |
| pytest + pytest-django | 8.x / 4.x | tests |
| Ruff | última estable | lint e formato |
| JavaScript | ES2020 sen framework | swipe con *pointer events* |
| Chart.js | 4.4.x | gardado en `static/vendor/`, só no panel do superadmin |
| Tipografías | Nunito 800, DM Sans 400/500/700 | ficheiros `woff2` en `static/fontes/` |

Configuración por variables de contorno (`.env`, lido con `os.environ`); hai un `.env.exemplo` versionado.

## Commands

```bash
# Primeira vez
cp .env.exemplo .env
docker compose up --build -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py cargar_demo        # concellos, checklist, contrato, ~30 cans, 3 perfís
docker compose exec web python manage.py createsuperuser    # crea un usuario con rol superadmin

# Día a día
docker compose up -d                                         # http://localhost:8000
docker compose logs -f web
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py expirar_solicitudes # tamén o executa o servizo «tarefas» cada hora

# Calidade
docker compose exec web pytest                               # todos os tests
docker compose exec web pytest --cov --cov-report=term-missing
docker compose exec web ruff check .
docker compose exec web ruff format .

# Demo/produción (VPS con dominio)
docker compose -f compose.yaml -f compose.prod.yaml up --build -d
```

## Project Structure

```
querocan/
├── SPEC.md                    → esta especificación
├── README.md                  → como arrancar o proxecto e percorrido guiado polo código
├── compose.yaml               → web (Django runserver), db (MySQL), tarefas (expiración)
├── compose.prod.yaml          → gunicorn + caddy (HTTPS)
├── Dockerfile
├── .env.exemplo
├── requirements.txt
├── pyproject.toml             → configuración de ruff e pytest
├── manage.py
├── querocan/                  → configuración do proxecto (settings, urls, wsgi)
├── contas/                    → Usuario (con rol), PerfilAdoptante, Protectora, rexistro/login, decoradores de rol
├── animais/                   → Can, FotoCan, listado, ficha, deck (vistas + API JSON do swipe)
├── compatibilidade/           → calculo.py e distancia.py (Python puro), test sen conta, Concello
├── adopcions/                 → Solicitude, estados.py, checklist, contrato, PDF, panel da protectora
├── contido/                   → landing, Finais felices, manual, enlaces, páxinas legais
├── xestion/                   → panel do superadmin: validación, usuarios, funil, contido
├── templates/                 → base.html e compoñentes compartidos (cabeceira, tarxeta, aviso)
├── static/
│   ├── css/                   → tokens.css (paleta e tipografía), base.css, compoñentes
│   ├── js/                    → deck.js (swipe), test.js, xeolocalizacion.js, aviso-non-implementado.js
│   ├── fontes/
│   └── vendor/                → chart.js
├── media/                     → fotos subidas (non versionado)
├── tests/                     → se a proba cruza apps; os tests de cada app van en <app>/tests/
└── docs/
    ├── ideas/querocan.md
    ├── referencias/
    └── probas-manuais.md      → checklist de probas en móbil real e accesibilidade
```

## Code Style

- **Idioma:** identificadores, comentarios, docstrings, mensaxes de commit e textos da interface
  en galego. Identificadores só en ASCII (`tamano`, `disponible`); os textos visibles levan a
  ortografía correcta (`Tamaño`, `Dispoñible`).
- **Comentarios:** cada módulo comeza cun bloque que explica que fai e como encaixa no fluxo;
  cada función pública ten docstring. Coméntase o *porqué*, non o que xa di o código.
- **Python:** Ruff (formato tipo Black, liña de 100). Lóxica de negocio fóra das vistas:
  `estados.py` e `calculo.py`. Vistas baseadas en funcións, curtas e explícitas.
- **JS:** módulos ES, sen variables globais; funcións pequenas; os xestos e os botóns chaman á
  mesma función.
- **CSS:** só tokens de `tokens.css` (paleta da prancha Marca); *mobile-first* con `min-width`;
  respéctase `prefers-reduced-motion`.

```python
# adopcions/estados.py
"""
Máquina de estados das solicitudes de adopción.

Toda mudanza de estado dunha solicitude (e do can asociado) pasa por este módulo.
Así as regras do fluxo (match, checklist, contrato, caducidade) están nun único sitio
e as vistas limítanse a chamar a estas funcións.
"""
from django.db import transaction

from animais.models import Can
from .models import Solicitude


@transaction.atomic
def aceptar_solicitude(solicitude: Solicitude, protectora_usuario) -> Solicitude:
    """A protectora acepta unha solicitude: o can queda reservado para esta persoa.

    As demais solicitudes pendentes do mesmo can pasan a «en espera» para que
    poidan reactivarse se esta adopción non chega a completarse.
    """
    # Bloqueamos o can para que dúas aceptacións simultáneas non o reserven dúas veces
    can = Can.objects.select_for_update().get(pk=solicitude.can_id)
    if can.estado != Can.Estado.DISPONIBLE:
        raise TransicionInvalida("O can xa non está dispoñible.")
    ...
```

```js
// static/js/deck.js
// Xestos e botóns comparten a mesma función: quen non pode deslizar usa os botóns ou o teclado.
function decidir(decision) {
  const tarxeta = deck.tarxetaActual();
  ...
}
```

## Accessibility & UX rules

- Contraste WCAG AA; o rosa empoulado `#C2858C` só en elementos grandes ou como fondo de texto escuro.
- Todo o que se fai cun xesto tamén se fai con botóns `<button>` e co teclado (← → ↑ Z).
- Botóns de funcionalidades non implementadas (Apadriñar, Acollida, favoritos): visibles e accesibles;
  amosan un aviso (`role="status"`) co texto "Esta funcionalidade aínda non está implementada".
- Deseño responsive: o adoptante prioriza móbil (390 px); o panel da protectora e o do superadmin
  priorizan escritorio pero non rompen en móbil.

## Testing Strategy

- **Unitarios (pytest):** `compatibilidade/calculo.py` e `distancia.py` (cobertura de ramas 100 %,
  incluídos os 3 perfís da demo e as incompatibilidades fortes); `adopcions/estados.py` (cada fila
  da táboa de transicións e cada transición inválida).
- **Integración (pytest-django + cliente de Django):** permisos por rol (cada vista protexida
  devolve 302/403 ao rol incorrecto); fluxo completo swipe → aceptar → checklist → contrato → PDF;
  caducidade con `expirar_solicitudes` e datas simuladas; paso das respostas do test anónimo ao perfil.
- **Concorrencia:** test de dúas aceptacións sobre o mesmo can (só unha ten éxito).
- **Manual:** `docs/probas-manuais.md` — swipe en Android e iOS reais, teclado, lector de pantalla,
  xeolocalización con permiso aceptado e denegado.
- **Cobertura mínima global:** 80 % (`pytest --cov`). Os tests corren contra MySQL en Docker, non SQLite.

## Boundaries

- **Always:**
  - Pasar `pytest` e `ruff check` antes de cada commit.
  - Cambiar estados só a través de `adopcions/estados.py`.
  - Comentar en galego cada módulo e función pública.
  - Validar no servidor todo formulario e comprobar o rol en cada vista (decoradores de `contas`).
  - Protexer con CSRF as chamadas JSON do deck.
  - Usar os tokens de cor e tipografía; nada de cores soltas no CSS.
- **Ask first:**
  - Engadir dependencias (Python ou JS).
  - Cambiar o modelo de datos dun xeito que non estea neste documento.
  - Cambiar pesos ou regras de compatibilidade.
  - Engadir rutas de API públicas.
  - Tocar `compose.prod.yaml` ou a configuración de seguridade.
- **Never:**
  - Versionar `.env`, credenciais ou fotos de `media/`.
  - Modificar unha `AceptacionContrato` despois de creada.
  - Implementar apadriñamento, acollida, favoritos, tenda, chat ou pagamentos sen actualizar antes esta especificación.
  - Usar o `django.contrib.admin` como interface do superadmin (só como ferramenta de desenvolvemento).
  - Borrar ou desactivar tests que fallan sen aprobación.

## Success Criteria

1. `docker compose up` + `migrate` + `cargar_demo` deixan a aplicación funcionando en
   `localhost:8000` nunha máquina limpa, só con Docker.
2. Na demo complétase o fluxo de punta a punta sen tocar a base de datos a man:
   - unha visitante fai o test e crea a conta;
   - a protectora recibe a solicitude e acéptaa;
   - a adoptante completa o checklist, acepta o contrato e descarga o PDF;
   - o superadmin ve a adopción reflectida no funil.
3. Cos datos da demo, o top 3 de cada un dos 3 perfís contrastados é coherente e os motivos
   explican a orde.
4. O deck úsase enteiro sen xestos (só botóns ou só teclado) e cos xestos en móbil real.
5. Cada rol só accede ao seu: probado con tests de permisos.
6. Unha solicitude aceptada e sen completar caduca aos 7 días e o can volve estar dispoñible.
7. Os tests pasan, a cobertura é ≥ 80 % e `ruff check` non dá erros.
8. Unha persoa allea, guiada polo README, explica o fluxo de solicitude e o cálculo de
   compatibilidade lendo só o código e os seus comentarios.

## Open Questions

- **Ámbito xeográfico:** só Galicia (fixture de 313 concellos) ou toda España? (supoñemos Galicia)
- **Solicitudes simultáneas:** pode unha persoa ter varias solicitudes `ACEPTADA` á vez para cans
  distintos? (supoñemos que si; a protectora ve as outras solicitudes activas da persoa)
- **Fotos:** límite de tamaño e redimensionado ao subilas (supoñemos máx. 5 MB, redimensionadas a 1600 px)
- **Dominio e VPS da demo:** pendentes; sen eles a demo faise en `localhost`, onde a xeolocalización funciona sen HTTPS.
