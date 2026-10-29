# Probas manuais

Comprobacións que non se poden facer con pytest. Anótase a data, o dispositivo e o resultado.

As probas con Chrome automatizado usan o protocolo DevTools: eventos táctiles e de rato reais,
teclado real e emulación de `prefers-reduced-motion`. Os scripts non forman parte do proxecto.
Quedan pendentes as comprobacións en dispositivos físicos (⏳).

## Deck de swipe

Páxina de proba con datos falsos: `/proba-deck/` (só con `DJANGO_DEBUG=1`). Deck real: `/descubrir/`.

| Comprobación | Chrome (emulación táctil 390×844) | Android real | iOS Safari real |
|---|---|---|---|
| Deslizar co dedo á dereita → «Gústame», solicitude creada e anuncio para lectores | ✅ 2026-10-29 | ⏳ | ⏳ |
| Deslizar co dedo á esquerda → «Non é para min» | ✅ 2026-10-29 | ⏳ | ⏳ |
| Arrastre curto (< 110 px) → a tarxeta volve ao sitio | ✅ 2026-10-29 | ⏳ | ⏳ |
| O xesto non fai scroll nin zoom da páxina | ✅ 2026-10-29 (scrollY = 0) | ⏳ | ⏳ |
| Arrastre co rato | ✅ 2026-10-29 | — | — |
| Teclado: ← → ↑ Z | ✅ 2026-10-29 | — | — |
| Botóns Desfacer / Non / Gústame / Ver ficha | ✅ 2026-10-29 | ⏳ | ⏳ |
| Só teclado: Tab ata «Non é para min», marco de foco visible e Intro decide | ✅ 2026-10-29 | — | — |
| `prefers-reduced-motion: reduce` → decisións sen animación | ✅ 2026-10-29 | ⏳ | ⏳ |
| Ao acabar os cans: estado baleiro e botóns desactivados | ✅ 2026-10-29 | ⏳ | ⏳ |

## Test de compatibilidade

| Comprobación | Resultado |
|---|---|
| Unha pregunta por pantalla; «Seguinte» desactivado ata responder | ✅ 2026-10-29 |
| Na primeira pregunta non se ve «Atrás»; na última, «Ver o resultado» | ✅ 2026-10-29 |
| Sen JavaScript vense as seis preguntas e o formulario funciona | ✅ (proba de servidor en pytest) |
| Ao enviar vai ao resultado con 3 cans | ✅ 2026-10-29 |

## Xeolocalización

| Comprobación | Resultado |
|---|---|
| Sen permiso de localización (ou sen HTTPS) queda o selector de concello | ✅ (o formulario GPS só aparece se o navegador ofrece `geolocation`) |
| Permiso aceptado en móbil real con HTTPS | ⏳ pendente de despregue con dominio |

## Accesibilidade (Lighthouse 12.6.1, categoría Accessibility)

| Páxina | Puntuación (2026-10-29) |
|---|---|
| `/` (landing) | 100 |
| `/descubrir/` (deck) | 100 |
| `/animais/` (listado) | 100 |
| `/animais/1/` (ficha) | 100 |
| `/test/` | 100 |

Lector de pantalla real (NVDA, VoiceOver ou TalkBack): ⏳ pendente.
