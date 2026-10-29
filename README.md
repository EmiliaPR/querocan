# QueroCan

**Un pequeno xesto, un amor para sempre.**

QueroCan é unha plataforma web de adopción de cans que funciona coma unha app de citas.
A persoa adoptante fai un test sobre a súa vida (vivenda, horas fóra, nenos, outros
animais, ritmo de vida). Despois ve as fichas dos cans de varias protectoras ordenadas
por **compatibilidade explicable**, e decide deslizando á dereita («Gústame») ou á
esquerda («Non é para min»). Se a protectora tamén di que si (*match*), a persoa completa
un compromiso de responsabilidade e acepta o contrato de adopción en liña.

Proxecto académico. A especificación completa está en [`SPEC.md`](SPEC.md) e o plan de
traballo en [`docs/plan.md`](docs/plan.md). A orixe da idea e as decisións de deseño están en
[`docs/ideas/querocan.md`](docs/ideas/querocan.md).

---

## Arrancar o proxecto

Só se necesita **Docker** (con Docker Compose).

```bash
cp .env.exemplo .env          # e axusta PORTO_WEB se o 8000 está ocupado
docker compose up --build -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py cargar_demo
```

Abre <http://localhost:8000> (ou o porto que puxeses en `PORTO_WEB`).

### Contas de demostración

Todas teñen o contrasinal **`querocan-demo`**.

| Rol | Correo | Que se pode probar |
|---|---|---|
| Superadmin | `admin@demo.querocan.gal` | Panel de xestión: validar protectoras, usuarios, funil, contido e contrato |
| Protectora | `palleiros@demo.querocan.gal` | Os seus cans e as solicitudes (hai algunhas pendentes de aceptar) |
| Protectora | `compostela@demo.querocan.gal`, `lugo@demo.querocan.gal` | Outras dúas protectoras activas |
| Protectora pendente | `nova@demo.querocan.gal` | Como se ve unha protectora sen validar |
| Adoptante | `estudante@demo.querocan.gal` | Persoa nun piso, moitas horas fóra; ten un *match* para completar |
| Adoptante | `familia@demo.querocan.gal` | Casa con patio, nenos e outro can; xa adoptou a Bruno |
| Adoptante | `xubilada@demo.querocan.gal` | Persoa tranquila, sempre na casa e con gatos |

Para crear unha conta de superadmin propia: `docker compose exec web python manage.py createsuperuser`.

## Ordes habituais

```bash
docker compose up -d                                         # arrancar
docker compose logs -f web                                   # ver o servidor (e os correos, que saen pola consola)
docker compose exec web python manage.py makemigrations      # tras cambiar un modelo
docker compose exec web python manage.py expirar_solicitudes # caducidade (o servizo «tarefas» faino cada hora)

docker compose exec web pytest                               # todas as probas (contra MySQL)
docker compose exec web pytest --cov --cov-report=term-missing
docker compose exec web ruff check .
docker compose exec web ruff format .
```

---

## Percorrido guiado polo código

Esta sección é para quen chega ao proxecto sen coñecelo. Recomendamos lelo nesta orde.
Todo o código está comentado en galego.

### 1. O cálculo de compatibilidade: `compatibilidade/calculo.py`

É o corazón do proxecto e é **Python puro**: non depende de Django nin da base de datos.

- A persoa e o can descríbense coas **mesmas seis dimensións**: vivenda, tamaño, horas só,
  nenos, outros animais e actividade/experiencia. Os valores posibles son os enums do
  principio do ficheiro.
- Hai unha función `_avaliar_*` por dimensión. Cada unha devolve unha puntuación (1, 0,5 ou 0)
  e un **motivo** que a explica («✓ Tes o patio que lle convén», «⚠ Non convive con gatos»).
- `calcular()` fai a media ponderada cos `PESOS`. Se hai unha incompatibilidade forte,
  limita o resultado ao `TOPE_INCOMPATIBILIDADE` (40 %).
- As probas en `compatibilidade/tests/test_calculo.py` cobren todas as ramas e explican
  cada regra cun exemplo.

### 2. O fluxo de adopción: `adopcions/estados.py`

Todas as mudanzas de estado dunha solicitude (e do can) pasan por este único módulo:

```
PENDENTE ──aceptar──▶ ACEPTADA ──checklist + contrato──▶ COMPLETADA
   │  ▲                  │
   │  └── EN_ESPERA ◀────┤   (as outras solicitudes do mesmo can agardan)
   ▼                     ▼
REXEITADA / CANCELADA    CADUCADA (7 días) / CANCELADA → o can volve estar dispoñible
```

- Cada función comproba **quen** fai a acción e **se o estado a permite**. Ademais, bloquea o can con
  `select_for_update` para que dúas aceptacións simultáneas non o reserven dúas veces. Hai
  unha proba con dous fíos contra MySQL que o demostra.
- Cada cambio queda en `HistorialSolicitude`, que tamén alimenta o funil do superadmin.
- As vistas (`adopcions/views_*.py`, `animais/api.py`) **nunca** cambian o campo `estado`
  directamente: chaman a estas funcións.

### 3. De onde saen os datos da persoa: `compatibilidade/perfil.py`

O test pódese facer **sen conta**:
- As respostas gárdanse na sesión e pasan ao perfil ao entrar ou crear a conta. Faino un sinal en `compatibilidade/apps.py`.
- O resto da aplicación só usa `perfil_de(request)` e `localizacion_de(request)`.

### 4. Ordenar os cans: `animais/consultas.py`

Fai tres cousas:
1. Aplica os filtros na base de datos.
2. Calcula a compatibilidade e a distancia para cada can (Haversine, en `compatibilidade/distancia.py`).
3. Ordena os resultados.

Úsano o listado, a ficha, o resultado do test e o deck.

### 5. O deck de swipe: `static/js/deck.js` + `static/js/deck-app.js` + `animais/api.py`

- `deck.js` non sabe nada do servidor. Recibe as funcións `cargar`, `decidir` e `desfacer`.
- Os xestos (Pointer Events), os botóns e o teclado (← → ↑ Z) chaman todos a `decidir()`.
- `deck-app.js` conéctao coa API JSON (`animais/api.py`), que leva o token CSRF.
- A páxina `/proba-deck/` usa datos falsos para probar o xesto en móbil (só en desenvolvemento).

### 6. Roles e permisos: `contas/`

- `Usuario` ten un campo `rol` (adoptante, protectora ou superadmin) e entra co correo.
- Os decoradores de `contas/decoradores.py` protexen as vistas privadas:
  - `@require_rol(...)` comproba o rol;
  - `@require_protectora_activa` comproba ademais que o superadmin validase a protectora.

### 7. O contrato: `adopcions/contrato.py`

- O texto sae dun modelo común con versións (`ModeloContrato`).
- Ao aceptalo gárdase unha copia exacta e o seu **hash SHA-256** nunha `AceptacionContrato`, que non se pode modificar.
- O PDF xérase con WeasyPrint.

### Mapa de carpetas

```
querocan/         configuración (settings, urls), saúde e comando cargar_demo
contas/           usuarios, roles, protectoras, perfís, rexistro e entrada
compatibilidade/  cálculo, distancia, test, localización e concellos de Galicia
animais/          cans, fotos, listado, ficha, deck (vistas + API) e panel de cans da protectora
adopcions/        solicitudes, máquina de estados, checklist, contrato, PDF e caducidade
contido/          landing, Finais felices, manual, enlaces, protectoras, privacidade e contacto
xestion/          panel do superadmin: protectoras, usuarios, funil e contido editable
templates/        base.html e compoñentes compartidos
static/           css (tokens.css = cores e tipografía), js, fontes e vendor (Chart.js)
docs/             idea, plan, probas manuais e referencias de deseño
```

---

## Probas

- **Unitarias:**
  - o cálculo de compatibilidade e a distancia;
  - a máquina de estados, coa cobertura de ramas ao 100 % e unha proba de concorrencia en MySQL.
- **Integración:**
  - permisos por rol, rexistro, test, listado, ficha, API do deck, panel da protectora, checklist, contrato e PDF;
  - funil e contido editable;
  - o **fluxo completo de punta a punta** (`adopcions/tests/test_fluxo.py`).
- **Manuais:** [`docs/probas-manuais.md`](docs/probas-manuais.md), co swipe en móbil, o teclado, a xeolocalización e Lighthouse.

## Despregue da demo (servidor con dominio)

```bash
# No .env do servidor:
#   DJANGO_DEBUG=0
#   DJANGO_SECRET_KEY=<unha clave longa e aleatoria>
#   DJANGO_ALLOWED_HOSTS=querocan.exemplo.gal
#   DOMINIO=querocan.exemplo.gal
#   SITIO_URL=https://querocan.exemplo.gal
#   PORTO_WEB=127.0.0.1:8000
docker compose -f compose.yaml -f compose.prod.yaml up --build -d
docker compose exec web python manage.py cargar_demo   # opcional
```

- Caddy obtén o certificado HTTPS automaticamente e serve as fotos.
- Django corre con Gunicorn e WhiteNoise.
- A xeolocalización do navegador só funciona con HTTPS (ou en `localhost`).
- `manage.py check --deploy` só avisa de `SECURE_HSTS_PRELOAD`. Déixase desactivado a propósito, porque é un compromiso a longo prazo co dominio.

## Decisións e limitacións conscientes

- **Só cans e só adopción.** Os botóns «Apadriñar», «Acollida» e favoritos vense, pero avisan de que aínda non están implementados.
- **Contrato:** é unha aceptación rexistrada e verificable (texto e hash), non unha sinatura dixital con validez legal plena.
- **Non hai chat, pagamentos nin notificacións en tempo real.** Os avisos van por correo.
- **Só concellos de Galicia** para a localización sen GPS.

## Créditos

- Tipografías Nunito e DM Sans (SIL Open Font License): [`static/fontes/LICENZA.md`](static/fontes/LICENZA.md).
- Chart.js (MIT): [`static/vendor/LEEME.md`](static/vendor/LEEME.md).
- Concellos de Galicia de Wikidata (CC0): [`compatibilidade/fixtures/LEEME.md`](compatibilidade/fixtures/LEEME.md).
- Fotos de demostración de Wikimedia Commons (dominio público e CC0): [`media/demo/LEEME.md`](media/demo/LEEME.md).
- Identidade visual: [`docs/referencias/QueroCan-proposta-identidade-grafica.html`](docs/referencias/QueroCan-proposta-identidade-grafica.html).
