# QueroCan

## Problem Statement
Como podemos conseguir que unha persoa atope o can que encaixa coa súa vida (non o máis bonito
da galería), e que as protectoras reciban menos solicitudes pero mellores?

## Recommended Direction
Plataforma web mobile-first con tres roles (adoptante, protectora, superadmin), en Django + MySQL,
que prioriza un **fluxo de adopción completo e robusto** sobre o puído visual. O adoptante enche
o seu perfil de condicións no rexistro (vivenda, horas fóra, nenos, outros animais, experiencia,
nivel de actividade) e explora fichas a pantalla completa con swipe, ordenadas por compatibilidade
e filtrables por distancia.

A compatibilidade é **simétrica e explicable**: a protectora describe as necesidades de cada can
nas mesmas dimensións que o perfil do adoptante, e unha función de regras con pesos (Python puro,
testada e comentada) devolve unha porcentaxe e os motivos ("✓ tes patio · ⚠ non convive con gatos").
Swipe á dereita crea unha solicitude; a protectora decide desde o seu propio panel (lista, non swipe).
Só hai *match* se ambas partes din si.

Tras o match, o adoptante completa un **checklist de responsabilidade** (derivado do Manual de
boas maneiras) e acepta un **contrato** xerado desde modelo (as 7 cláusulas da referencia), con
rexistro de data, usuario e hash do texto aceptado, descargable en PDF. O superadmin valida
protectoras e ve un **funil sinxelo** (solicitudes → matches → contratos → adopcións) por protectora.
Identidade visual da referencia (`docs/referencias/`: fucsia + menta, fondo crema, cintas, polaroids)
adaptada a móbil. O panel do superadmin é unha interface propia con esa estética; `django.contrib.admin`
queda só como ferramenta interna de desenvolvemento.

## Key Assumptions to Validate
- [ ] A compatibilidade ordena con sentido — seed de ~30 cans e 3 perfís contrastados (estudante
      en piso, familia con nenos e casa, xubilada); o top 3 de cada perfil debe parecer razoable
      a unha persoa allea.
- [ ] O fluxo con varios adoptantes por can é coherente — deseñar a máquina de estados (can:
      dispoñible/reservado/adoptado; solicitude: pendente/aceptada/en espera/rexeitada/completada/
      cancelada) en papel antes do modelo de datos, e testar transicións.
- [ ] As protectoras completan as necesidades do can — campos obrigatorios con opción
      "indiferente" explícita; comprobar con alguén alleo que o formulario se entende.
- [ ] O swipe con pointer events nativos funciona en móbil real — prototipo HTML/JS illado
      probado en Android e iOS antes de integralo.
- [ ] Unha persoa allea entende o código — que alguén de fóra lea models + fluxo de solicitude
      e explique o funcionamento sen axuda.

## MVP Scope
**Dentro:**
- Rexistro/login con roles (Django auth + grupos/decoradores de permiso)
- Adoptante: perfil de condicións, swipe ordenado por compatibilidade co "por que", filtro por
  distancia (GPS ou concello → Haversine), lista de solicitudes e o seu estado, checklist, contrato
- Protectora: rexistro pendente de validación, CRUD de cans (fotos + necesidades), panel de
  solicitudes con compatibilidade visible, aceptar/rexeitar
- Superadmin: validar protectoras, xestionar usuarios, funil de métricas (Chart.js), xestión do
  contido estático (testemuños Amores Palleiros, enlaces de interese)
- Landing explicando o concepto "Tinder para adoptar"
- Comentarios en galego en todo o código; seed de datos de demo

**Fóra:** ver abaixo.

## Not Doing (and Why)
- Tenda / pagamentos — decisión explícita; come semanas sen reforzar o fluxo central
- Swipe para protectoras — a revisión de solicitudes é traballo de xestión; unha lista é mellor
- Chat interno — o contacto post-match faise por correo/teléfono; un chat é un proxecto en si
- Notificacións en tempo real / push — abondan estados e contadores ao entrar
- Sinatura dixital con validez legal — aceptación + hash abonda para o académico; documentarase
  como limitación
- Machine learning na compatibilidade — regras con pesos son explicables e testables
- Outras especies e acollida temporal — liñas de traballo futuro para a memoria
- Testemuños ligados á adopción — quedan como contido estático xestionado polo superadmin
- Mapas interactivos — a distancia en km na ficha abonda

## Open Questions
- Data de entrega e tamaño do equipo? (determina se o funil do superadmin e a PDF entran ou se
  recortan)
- Cales son exactamente as 6–8 dimensións de compatibilidade e os seus pesos? (a referencia mestura
  condicións obxectivas con preguntas de personalidade — "síntese só?", "asume o papel de líder?";
  hai que decidir se estas últimas entran e como se mapean a trazos do can)
- Que pasa se unha adopción aceptada non se completa en X días? (expiración automática ou manual)
- Onde se aloxa a demo para o tribunal? (afecta a HTTPS, que é obrigatorio para a xeolocalización
  do navegador)
- O texto do contrato é o de "Os Palleiros" ou cada protectora pode personalizar o seu?
