# Plan de implementación: QueroCan

## Visión xeral
Implementación do MVP descrito en `SPEC.md`: plataforma Django + MySQL en Docker con tres roles,
deck de swipe ordenado por compatibilidade e fluxo de adopción completo (solicitude → match →
checklist → contrato). O plan avanza en **fatias verticais**: cada tarefa deixa algo que funciona
e se pode probar de punta a punta, e as pezas de máis risco van primeiro.

## Decisións de arquitectura
- **Primeiro o risco.** As tres incógnitas que poden tumbar o proxecto adiántanse:
  - o swipe en móbil real (T5);
  - o algoritmo de compatibilidade (T4);
  - a máquina de estados con concorrencia (T11).

  WeasyPrint instálase xa na imaxe Docker en T1, para detectar canto antes os problemas coas
  librarías do sistema.
- **A lóxica pura vai separada do ORM.** `calculo.py` e `distancia.py` traballan con
  *dataclasses* e non con modelos de Django, así que se proban sen base de datos e se len sen
  coñecer Django.
- **Un só punto para os estados.** As vistas chaman a `adopcions/estados.py` e nunca escriben
  `estado` directamente.
- **`cargar_demo` medra con cada tarefa.** Cada tarefa que crea un modelo engade os seus datos
  de proba ao comando. Así o sistema sempre se pode demostrar.
- **Definición de feito común a todas as tarefas:**
  - `pytest` en verde contra MySQL;
  - `ruff check .` sen erros;
  - módulos e funcións públicas comentados en galego;
  - migracións creadas e aplicadas;
  - `cargar_demo` actualizado se a tarefa crea un modelo;
  - un commit por tarefa.

## Grafo de dependencias

```
T1 Docker+Django ──┬── T2 Base visual ──────────────────────────────┐
                   └── T3 Usuario+roles ─┬── T6 Protectoras          │
                                         │      └── T7 Can ── T8 Fotos
T4 Compatibilidade (puro) ───────────────┤                          │
T5 Prototipo swipe (puro JS) ────────────┤                          │
                                         ├── T9 Concellos+distancia │
                                         ├── T10 Test+perfil ◄──────┘
                                         └── T11 Estados ─┐
                    T7,T9,T10 ── T12 Listado+ficha        │
                    T5,T11,T12 ── T13 Deck real ◄─────────┘
                         T13 ── T14 Panel protectora ── T15 Miñas solicitudes
                                       └── T16 Checklist ── T17 Contrato+PDF ── T18 Caducidade
                         T6 ── T19 Panel superadmin ── T20 Funil
                                       └── T21 Contido editable
                         T2,T12 ── T22 Landing e botóns non implementados
                         todo ── T23 Datos demo · T24 Accesibilidade · T25 Produción+README
```

---

## Fase 1: Cimentos

### T1: Esqueleto Docker + Django + MySQL
**Descrición:** proxecto Django 5.2 baleiro (`querocan/`), con:
- `compose.yaml`, cos servizos `web` e `db` (MySQL 8.4 con *healthcheck*);
- un `Dockerfile` coas librarías de sistema de WeasyPrint e mysqlclient;
- a configuración lida desde `.env` (e un `.env.exemplo` versionado);
- `pyproject.toml` coa configuración de ruff e pytest;
- unha vista `/saude/` que comproba a conexión coa base de datos.

**Aceptación:**
- [ ] `docker compose up --build` arranca nunha máquina limpa e `/saude/` responde 200.
- [ ] Un test de fume corre contra MySQL e pasa.
- [ ] Dentro do contedor, WeasyPrint xera un PDF «ola mundo».

**Verificación:** `docker compose exec web pytest`; `ruff check .`; abrir `localhost:8000/saude/`.
**Dependencias:** ningunha.
**Ficheiros:** `Dockerfile`, `compose.yaml`, `.env.exemplo`, `requirements.txt`, `pyproject.toml`, `querocan/settings.py`, `querocan/urls.py`, `tests/test_saude.py`.
**Tamaño:** M.

### T2: Base visual (tokens, tipografía e plantilla base)
**Descrición:** contén:
- `tokens.css`, coa paleta da prancha Marca, a escala tipográfica e os raios;
- as fontes Nunito e DM Sans servidas desde `static/fontes/`;
- `base.html`, coa cabeceira (logo C e menú hamburguesa en móbil) e o pé;
- o compoñente de aviso para as funcionalidades non implementadas;
- `contido/`, cunha landing provisional.

**Aceptación:**
- [ ] A landing provisional reprodúcese fiel á proposta a 390 px e a 1440 px.
- [ ] No CSS non hai cores fóra de `tokens.css`. Compróbase con `grep '#[0-9a-f]\{6\}' static/css --exclude tokens.css`, que non debe devolver nada.
- [ ] Un botón marcado con `data-non-implementado` amosa o aviso con `role="status"`.

**Verificación:** comprobación manual en móbil e escritorio; o test da vista da landing devolve 200.
**Dependencias:** T1.
**Ficheiros:** `static/css/tokens.css`, `static/css/base.css`, `templates/base.html`, `static/js/aviso-non-implementado.js`, `contido/views.py`.
**Tamaño:** M.

### T3: Usuario con rol, rexistro, login e decoradores
**Descrición:** contén:
- un modelo `Usuario` propio (`AUTH_USER_MODEL`), con `rol` (adoptante, protectora ou superadmin) e o correo como identificador;
- as pantallas de entrar e crear conta da proposta, coa elección de rol e a aceptación da privacidade;
- a recuperación de contrasinal, co correo pola consola en desenvolvemento;
- os decoradores `require_rol(...)`;
- que `createsuperuser` asigne o rol superadmin.

**Aceptación:**
- [ ] Pódese crear unha conta de adoptante e entrar e saír con ela.
- [ ] Unha vista protexida con `require_rol("protectora")` responde 403 a un adoptante e redirixe ao login a un visitante.
- [ ] `createsuperuser` crea un usuario co rol superadmin.

**Verificación:** `pytest contas/`, cos tests de permisos parametrizados por rol.
**Dependencias:** T1, T2 (para as plantillas).
**Ficheiros:** `contas/models.py`, `contas/forms.py`, `contas/views.py`, `contas/decoradores.py`, `templates/contas/*.html`.
**Tamaño:** M.

### Checkpoint 1: cimentos
- [ ] Todo arranca con Docker e os tests pasan contra MySQL.
- [ ] Hai rexistro e login cos tres roles.
- [ ] A identidade visual está aplicada á base.
- [ ] **Revisión humana antes de seguir.**

---

## Fase 2: Riscos principais

### T4: Algoritmo de compatibilidade (TDD)
**Descrición:** `compatibilidade/calculo.py` en Python puro. Contén:
- os *dataclasses* `PerfilAdoptante`, `NecesidadesCan`, `Resultado` e `Motivo`;
- as seis dimensións, os pesos, as incompatibilidades fortes (con tope do 40 %) e os motivos ✓/⚠, todo como indica a SPEC;
- os pesos e as regras como constantes nomeadas e comentadas.

**Aceptación:**
- [ ] A cobertura de ramas de `calculo.py` é do 100 %.
- [ ] Os tres perfís da demo (estudante nun piso, familia con nenos, xubilada) producen a orde esperada sobre un conxunto fixo de cans.
- [ ] Ningunha incompatibilidade forte supera o 40 %.

**Verificación:** `pytest compatibilidade/tests/test_calculo.py --cov=compatibilidade.calculo --cov-branch`.
**Dependencias:** ningunha (pódese facer en paralelo con T1–T3).
**Ficheiros:** `compatibilidade/calculo.py`, `compatibilidade/tests/test_calculo.py`.
**Tamaño:** S.

### T5: Prototipo illado do swipe
**Descrición:** `deck.js` e o seu CSS. Inclúe:
- unha pila de tarxetas con *pointer events*: arrastre, limiar de decisión e animación de saída;
- os botóns «Non é para min», «Gústame», «Ver ficha» e «Desfacer»;
- os atallos de teclado ← → ↑ Z;
- respecto a `prefers-reduced-motion`.

Os xestos e os botóns chaman a `decidir()`. Por agora usa datos falsos nunha páxina de proba, sen backend.

**Aceptación:**
- [ ] Funciona en Android (Chrome) e en iOS (Safari) reais: o xesto non fai *scroll* da páxina nin zoom.
- [ ] Todas as accións poden facerse só co teclado e só cos botóns.
- [ ] «Desfacer» recupera a última tarxeta.

**Verificación:** a páxina de proba en móbil real (resultado anotado en `docs/probas-manuais.md`) e revisión manual co teclado.
**Dependencias:** T2.
**Ficheiros:** `static/js/deck.js`, `static/css/deck.css`, `templates/animais/proba_deck.html`, `docs/probas-manuais.md`.
**Tamaño:** M.

### T6: Alta e validación de protectoras
**Descrición:** contén:
- o modelo `Protectora`, ligado a un usuario co rol protectora, con CIF, concello, coordenadas, contacto e estado (`PENDENTE_VALIDACION`, `ACTIVA` ou `DESACTIVADA`);
- o formulario de alta;
- unha vista mínima do superadmin para validar e rexeitar.

**Aceptación:**
- [ ] Unha protectora nova non pode acceder ás vistas de xestión de cans ata ser validada.
- [ ] O superadmin ve a cola de protectoras pendentes e pode validalas.
- [ ] A protectora recibe un correo cando a validan.

**Verificación:** `pytest contas/ xestion/`.
**Dependencias:** T3.
**Ficheiros:** `contas/models.py`, `contas/views.py`, `xestion/views.py`, `templates/xestion/protectoras.html`.
**Tamaño:** M.

### T7: Modelo Can e CRUD da protectora
**Descrición:** contén:
- o modelo `Can`, con datos básicos, etiquetas de carácter, urxente, descrición, as seis necesidades (obrigatorias e coa opción «indiferente») e o estado;
- as vistas da protectora para listar, crear, editar e retirar os seus cans;
- un adaptador `Can → NecesidadesCan` para conectar co cálculo.

**Aceptación:**
- [ ] Unha protectora só ve e edita os seus cans; un can doutra protectora devolve 404.
- [ ] O formulario rexeita gardar sen as seis necesidades.
- [ ] Non se pode retirar un can cunha solicitude `ACEPTADA` (regra preparada para T11).

**Verificación:** `pytest animais/`; manual: crear un can desde o móbil.
**Dependencias:** T4, T6.
**Ficheiros:** `animais/models.py`, `animais/forms.py`, `animais/views_protectora.py`, `templates/animais/protectora/*.html`.
**Tamaño:** M.

### T8: Fotos dos cans
**Descrición:** un modelo `FotoCan` (unha principal e ata cinco máis) que redimensiona as imaxes a 1600 px con Pillow e rexeita as de máis de 5 MB ou formatos non permitidos. Os ficheiros gárdanse en `media/`, que non se versiona.

**Aceptación:**
- [ ] Unha foto de 4000 px gárdase a 1600 px.
- [ ] Un ficheiro de 6 MB ou un `.exe` renomeado rexéitanse cunha mensaxe en galego.
- [ ] A foto principal pódese cambiar.

**Verificación:** `pytest animais/tests/test_fotos.py`.
**Dependencias:** T7.
**Ficheiros:** `animais/models.py`, `animais/imaxes.py`, `animais/forms.py`, `templates/animais/protectora/fotos.html`.
**Tamaño:** S.

### Checkpoint 2: riscos principais
- [ ] O swipe está validado en móbil real.
- [ ] O algoritmo de compatibilidade está cuberto ao 100 %.
- [ ] Unha protectora validada pode publicar cans con fotos.
- [ ] **Revisión humana: confirmar os pesos co resultado dos tres perfís.**

---

## Fase 3: Exploración do adoptante

### T9: Concellos, distancia e localización
**Descrición:** contén:
- o modelo e a fixture `Concello`, cos 313 concellos de Galicia e as súas coordenadas;
- `distancia.py`, coa fórmula de Haversine en Python puro;
- `xeolocalizacion.js`, que usa o GPS do navegador e, se se denega o permiso, ofrece o selector de concello;
- a localización gardada no perfil (adoptante) ou na sesión (visitante).

**Aceptación:**
- [ ] A distancia Vigo–Santiago dá uns 80 km (±2).
- [ ] Ao denegar o GPS aparece o selector de concello.
- [ ] A fixture carga os 313 concellos.

**Verificación:** `pytest compatibilidade/tests/test_distancia.py`; manual con o permiso aceptado e denegado.
**Dependencias:** T3.
**Ficheiros:** `compatibilidade/models.py`, `compatibilidade/distancia.py`, `compatibilidade/fixtures/concellos.json`, `static/js/xeolocalizacion.js`.
**Tamaño:** M.

### T10: Test de compatibilidade e perfil do adoptante
**Descrición:** contén:
- o test de seis preguntas, unha por pantalla, coas opcións «Atrás» e «Facelo máis tarde», tal como na proposta;
- o modelo `PerfilAdoptante`;
- para visitantes, as respostas gárdanse na sesión e pasan ao perfil ao rexistrarse;
- a pantalla de resultado, cos tres cans máis compatibles, a porcentaxe e os motivos;
- a edición do perfil.

**Aceptación:**
- [ ] Un visitante fai o test, crea a conta e o seu perfil xa está completo sen repetilo.
- [ ] O resultado ordena polo cálculo de T4 e amosa ata tres motivos.
- [ ] Un perfil incompleto marca á persoa como «sen perfil» (para bloquear solicitudes en T13).

**Verificación:** `pytest compatibilidade/tests/test_test.py`, incluído o paso da sesión ao perfil.
**Dependencias:** T4, T7, T9.
**Ficheiros:** `compatibilidade/views.py`, `compatibilidade/forms.py`, `contas/models.py`, `templates/compatibilidade/*.html`, `static/js/test.js`.
**Tamaño:** M.

### T11: Máquina de estados das solicitudes (TDD)
**Descrición:** contén:
- os modelos `Solicitude`, `HistorialSolicitude` e `Descarte`;
- `adopcions/estados.py`, cunha función por cada fila da táboa de transicións da SPEC, dentro de `transaction.atomic` e con `select_for_update` sobre o can;
- unha excepción `TransicionInvalida`.

**Aceptación:**
- [ ] Cada transición da táboa ten un test, e cada transición inválida tamén.
- [ ] Dúas aceptacións simultáneas sobre o mesmo can: só unha ten éxito. O test usa dous fíos contra MySQL.
- [ ] Toda transición crea unha entrada en `HistorialSolicitude`.

**Verificación:** `pytest adopcions/tests/test_estados.py --cov=adopcions.estados --cov-branch` (100 %).
**Dependencias:** T7.
**Ficheiros:** `adopcions/models.py`, `adopcions/estados.py`, `adopcions/tests/test_estados.py`.
**Tamaño:** M.

### T12: Listado e ficha públicos
**Descrición:** contén:
- o listado en grella, cos filtros de tamaño, idade, distancia e «só urxentes»;
- a ficha, con galería, datos, saúde, convivencia, protectora e «Animais parecidos»;
- a porcentaxe e os motivos, se hai perfil (ou test na sesión), e se non, orde por urxencia e distancia;
- o filtro de especie eliminado.

**Aceptación:**
- [ ] Os filtros combínanse e mantéñense na URL.
- [ ] Os cans `RESERVADO`, `ADOPTADO` ou `RETIRADO` non aparecen no listado.
- [ ] A ficha dun visitante sen test non amosa porcentaxe.

**Verificación:** `pytest animais/tests/test_listado.py`; revisión manual a 390 px.
**Dependencias:** T8, T9, T10.
**Ficheiros:** `animais/views.py`, `animais/consultas.py`, `templates/animais/listado.html`, `templates/animais/ficha.html`.
**Tamaño:** M.

### T13: Deck real conectado
**Descrición:** contén:
- unha API JSON con CSRF: `GET` para a seguinte tanda ordenada e filtrada, e `POST` para as decisións;
- deslizar á dereita (ou «Adoptar») crea a solicitude `PENDENTE` a través de `estados.py`;
- deslizar á esquerda crea un `Descarte`;
- «Desfacer» elimina a última decisión;
- un visitante que desliza á dereita vai ao login, e despois do login a solicitude créase;
- un adoptante sen perfil vai ao test;
- o selector tarxetas/grella.

**Aceptación:**
- [ ] Un can xa decidido non volve aparecer.
- [ ] Un visitante desliza á dereita, entra e atopa a solicitude creada.
- [ ] Unha `POST` sen token CSRF responde 403.

**Verificación:** `pytest animais/tests/test_deck_api.py`; manual en móbil real (repetir a checklist de T5).
**Dependencias:** T5, T11, T12.
**Ficheiros:** `animais/api.py`, `animais/urls.py`, `static/js/deck.js`, `templates/animais/deck.html`.
**Tamaño:** M.

### Checkpoint 3: exploración
- [ ] Unha persoa fai o test, explora o deck ordenado e crea solicitudes con xesto, botóns e teclado.
- [ ] Os tests pasan e a cobertura de `calculo` e `estados` é do 100 %.
- [ ] **Revisión humana.**

---

## Fase 4: Fluxo de adopción

### T14: Panel de solicitudes da protectora
**Descrición:** unha lista de solicitudes filtrable por can e estado. Cada solicitude amosa a compatibilidade, os motivos e as outras solicitudes activas da persoa. A protectora pode aceptar, rexeitar e cancelar (a través de `estados.py`). O adoptante recibe un correo en cada cambio.

**Aceptación:**
- [ ] Ao aceptar, o can pasa a `RESERVADO` e as demais solicitudes do can pasan a `EN_ESPERA`, e iso vese no panel.
- [ ] Unha protectora non pode actuar sobre solicitudes doutra (404).
- [ ] O panel úsase ben en escritorio e non se rompe a 390 px.

**Verificación:** `pytest adopcions/tests/test_panel_protectora.py`.
**Dependencias:** T13.
**Ficheiros:** `adopcions/views_protectora.py`, `adopcions/correos.py`, `templates/adopcions/protectora/*.html`.
**Tamaño:** M.

### T15: As miñas solicitudes (adoptante)
**Descrición:** a lista de solicitudes do adoptante, co estado, o prazo restante se está aceptada, a opción de retirar as `PENDENTE` e as `EN_ESPERA`, e o acceso ao checklist e ao contrato cando corresponda.

**Aceptación:**
- [ ] Os estados amósanse con texto en galego e unha cor accesible.
- [ ] Retirar unha solicitude cambia o estado a `CANCELADA`.
- [ ] Unha solicitude aceptada amosa os días que quedan.

**Verificación:** `pytest adopcions/tests/test_minas_solicitudes.py`.
**Dependencias:** T14.
**Ficheiros:** `adopcions/views_adoptante.py`, `templates/adopcions/adoptante/solicitudes.html`.
**Tamaño:** S.

### T16: Checklist de responsabilidade
**Descrición:** o modelo `ItemChecklist`, cunha fixture derivada do Manual de boas maneiras. Hai que marcar todos os elementos para gardar `data_checklist` na solicitude aceptada.

**Aceptación:**
- [ ] Non se pode completar o checklist sen marcar todos os elementos.
- [ ] Só se pode completar cunha solicitude propia en estado `ACEPTADA`.
- [ ] Unha vez completado, habilítase o contrato.

**Verificación:** `pytest adopcions/tests/test_checklist.py`.
**Dependencias:** T15.
**Ficheiros:** `adopcions/models.py`, `adopcions/views_adoptante.py`, `adopcions/fixtures/checklist.json`, `templates/adopcions/adoptante/checklist.html`.
**Tamaño:** S.

### T17: Contrato e PDF
**Descrición:** contén:
- os modelos `ModeloContrato` (con versións e un activo) e `AceptacionContrato` (que non se pode modificar);
- un formulario cos datos do adoptante;
- o texto final con hash SHA-256;
- `completar_adopcion` en `estados.py`;
- a descarga do PDF con WeasyPrint;
- unha fixture coas sete cláusulas da referencia.

**Aceptación:**
- [ ] Ao aceptar, a solicitude pasa a `COMPLETADA`, o can pasa a `ADOPTADO` e as solicitudes `EN_ESPERA` pasan a `REXEITADA`.
- [ ] O hash gardado coincide co SHA-256 do texto gardado, e calquera intento de gardar de novo unha aceptación lanza un erro.
- [ ] O PDF descárgase e contén os datos e o hash.

**Verificación:** `pytest adopcions/tests/test_contrato.py`; manual: abrir o PDF.
**Dependencias:** T16.
**Ficheiros:** `adopcions/models.py`, `adopcions/contrato.py`, `adopcions/views_adoptante.py`, `templates/adopcions/contrato.html`, `templates/adopcions/contrato_pdf.html`.
**Tamaño:** M.

### T18: Caducidade das solicitudes
**Descrición:** o comando `expirar_solicitudes`, que marca como `CADUCADA` as solicitudes aceptadas hai máis de 7 días a través de `estados.py`. En `compose.yaml` engádese o servizo `tarefas`, que o executa cada hora.

**Aceptación:**
- [ ] Unha solicitude aceptada hai 8 días caduca, o can volve a `DISPONIBLE` e as `EN_ESPERA` pasan a `PENDENTE`.
- [ ] Unha solicitude aceptada hai 6 días non se toca.
- [ ] Executar o comando dúas veces seguidas dá o mesmo resultado (idempotente).

**Verificación:** `pytest adopcions/tests/test_caducidade.py`, coas datas simuladas.
**Dependencias:** T11 (pódese facer en paralelo con T14–T17).
**Ficheiros:** `adopcions/management/commands/expirar_solicitudes.py`, `compose.yaml`, `adopcions/tests/test_caducidade.py`.
**Tamaño:** S.

### Checkpoint 4: fluxo completo
- [ ] Criterio de éxito 2 da SPEC: test → conta → swipe → aceptación → checklist → contrato → PDF, sen tocar a base de datos a man.
- [ ] Os tests pasan.
- [ ] **Revisión humana con demo.**

---

## Fase 5: Superadmin e contido

### T19: Panel do superadmin
**Descrición:** unha interface propia coa estética da marca (non `django.contrib.admin`). Ten a cola de protectoras, a lista de usuarios e protectoras con busca e a opción de activar e desactivar. Unha conta desactivada non pode entrar.

**Aceptación:**
- [ ] Só o rol superadmin accede (403 para os demais).
- [ ] Ao desactivar unha protectora, os seus cans deixan de verse.
- [ ] Unha persoa desactivada non pode iniciar sesión.

**Verificación:** `pytest xestion/`.
**Dependencias:** T6.
**Ficheiros:** `xestion/views.py`, `xestion/urls.py`, `templates/xestion/*.html`, `static/css/xestion.css`.
**Tamaño:** M.

### T20: Funil de métricas
**Descrición:** as consultas sobre `HistorialSolicitude` por protectora e período (solicitudes → aceptadas → checklist → completadas, máis as caducadas e as canceladas) e as gráficas con Chart.js, gardado en `static/vendor/`.

**Aceptación:**
- [ ] As cifras coinciden cun escenario de proba construído no test.
- [ ] Os filtros de protectora e período funcionan.
- [ ] As gráficas teñen unha táboa equivalente, por accesibilidade.

**Verificación:** `pytest xestion/tests/test_funil.py`; revisión manual cos datos da demo.
**Dependencias:** T18, T19.
**Ficheiros:** `xestion/metricas.py`, `xestion/views.py`, `templates/xestion/funil.html`, `static/vendor/chart.umd.min.js`.
**Tamaño:** M.

### T21: Contido editable
**Descrición:** os modelos `Testemuno` e `Enlace` e un CRUD no panel do superadmin para eles, para o modelo de contrato (cada gardado crea unha versión nova) e para os elementos do checklist. Inclúe as páxinas públicas de *Finais felices*, Enlaces de interese e Manual de boas maneiras.

**Aceptación:**
- [ ] Ao editar o contrato créase unha versión nova, e as aceptacións anteriores conservan o seu texto e o seu hash.
- [ ] Os testemuños e os enlaces que se crean no panel aparecen nas páxinas públicas.
- [ ] O manual vese ben en móbil.

**Verificación:** `pytest contido/ xestion/tests/test_contido.py`.
**Dependencias:** T17, T19.
**Ficheiros:** `contido/models.py`, `contido/views.py`, `xestion/views_contido.py`, `templates/contido/*.html`, `templates/xestion/contido/*.html`.
**Tamaño:** M.

### T22: Landing completa e botóns non implementados
**Descrición:** a landing final da proposta (escritorio e móbil). Os textos de «Como funciona» cámbianse ao fluxo de match, checklist e contrato. Os botóns «Apadriñar», o filtro «Acollida» e o corazón de favoritos colócanse en todas as tarxetas e fichas co aviso de non implementado.

**Aceptación:**
- [ ] Ningún texto promete «contacto directo» como paso final.
- [ ] Os tres tipos de botón non implementado amosan o aviso e non fan ningunha petición ao servidor.
- [ ] A landing é fiel á proposta a 390 px e a 1440 px.

**Verificación:** revisión manual; o test da landing devolve 200.
**Dependencias:** T12, T21.
**Ficheiros:** `templates/contido/landing.html`, `templates/animais/_tarxeta.html`, `templates/animais/ficha.html`, `static/css/landing.css`.
**Tamaño:** M.

### Checkpoint 5: funcionalidade completa
- [ ] Todas as historias de usuario da SPEC están implementadas.
- [ ] **Revisión humana.**

---

## Fase 6: Peche

### T23: Datos de demo completos
**Descrición:** completar `cargar_demo` con:
- 3 protectoras;
- uns 30 cans variados en todas as dimensións;
- os 3 perfís contrastados, con contas;
- solicitudes en varios estados, para que o funil teña datos;
- testemuños.

**Aceptación:**
- [ ] O comando é idempotente.
- [ ] O top 3 de cada perfil é coherente (criterio de éxito 3).
- [ ] O funil amosa datos en todas as etapas.

**Verificación:** `cargar_demo` sobre unha base de datos baleira e despois revisión manual co humano.
**Dependencias:** T22.
**Ficheiros:** `querocan/management/commands/cargar_demo.py`, `querocan/demo/*.json`, `media/demo/` (fotos de demo con licenza libre).
**Tamaño:** M.

### T24: Accesibilidade e probas manuais
**Descrición:** completar `docs/probas-manuais.md` e corrixir o que saia ao revisar:
- o contraste;
- a orde do foco e o teclado en todo o fluxo;
- os nomes accesibles;
- o lector de pantalla no deck;
- `prefers-reduced-motion`;
- o swipe en móbiles reais.

**Aceptación:**
- [ ] Lighthouse Accessibility ≥ 90 na landing, o deck, a ficha e o test.
- [ ] O fluxo completo pódese facer só co teclado.
- [ ] A checklist manual está completa e asinada coa data.

**Verificación:** Lighthouse e a checklist manual.
**Dependencias:** T23.
**Ficheiros:** `docs/probas-manuais.md` e os CSS e plantillas que haxa que corrixir.
**Tamaño:** M.

### T25: Produción e README
**Descrición:** contén:
- `compose.prod.yaml`, con Gunicorn, WhiteNoise e Caddy (HTTPS e `media/`);
- `DEBUG=False` e a configuración de seguridade (cookies seguras, HSTS, `ALLOWED_HOSTS`);
- un README con dúas partes: como arrancar o proxecto e un «percorrido guiado polo código» para unha persoa allea.

**Aceptación:**
- [ ] `docker compose -f compose.yaml -f compose.prod.yaml up` serve por HTTPS cun dominio de proba e a xeolocalización funciona.
- [ ] `manage.py check --deploy` non dá avisos críticos.
- [ ] Unha persoa allea segue o README e explica o fluxo e a compatibilidade (criterio de éxito 8).

**Verificación:** despregue de proba e `check --deploy`.
**Dependencias:** T24.
**Ficheiros:** `compose.prod.yaml`, `Caddyfile`, `querocan/settings.py`, `README.md`.
**Tamaño:** M.

### Checkpoint final
- [ ] Cúmprense os criterios de éxito 1–8 da SPEC.
- [ ] Os tests pasan, a cobertura é ≥ 80 % e `ruff check` está limpo.
- [ ] **Aprobación humana.**

---

## Riscos e mitigacións

| Risco | Impacto | Mitigación |
|---|---|---|
| O swipe falla en iOS Safari (scroll, zoom ou *pointer events*) | Alto | T5 faise cedo, en móbil real, antes de conectar o backend; usar `touch-action: none` só na tarxeta |
| WeasyPrint non se instala na imaxe | Medio | Comprobación en T1; alternativa: xerar o PDF desde o navegador con `window.print()` e CSS de impresión |
| Os pesos de compatibilidade dan ordes absurdas | Alto | Tests cos tres perfís en T4 e revisión humana no checkpoint 2, antes de construír enriba |
| Condicións de carreira ao aceptar solicitudes | Alto | `select_for_update` e un test de concorrencia contra MySQL en T11 (non SQLite) |
| Os tests contra MySQL son lentos | Baixo | `--reuse-db` en pytest-django; base de datos de test en `tmpfs` en Compose |
| Fotos de demo con dereitos de autor | Medio | Usar só imaxes de dominio público ou CC0 e citar a fonte en `media/demo/LEEME.md` |
| Sen HTTPS non hai xeolocalización fóra de localhost | Medio | Selector de concello sempre dispoñible; HTTPS con Caddy en T25 |

## Paralelización
- **En paralelo desde o inicio:** T4 (compatibilidade) e T5 (swipe) non dependen do backend.
- **En paralelo na fase 4:** T18 (caducidade) con T14–T17; T19 (superadmin) en canto estea T6.
- **Secuencial obrigatorio:** as migracións dos modelos (T3 → T6 → T7 → T11 → T17), para evitar conflitos.

## Preguntas abertas
- As da SPEC seguen con valores por defecto (só Galicia, varias solicitudes aceptadas simultáneas, fotos de 5 MB a 1600 px, dominio da demo).
- Haberá alguén con iPhone para validar T5? Se non, hai que buscar un dispositivo ou un servizo de probas.
