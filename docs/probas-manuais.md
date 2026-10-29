# Probas manuais

Comprobacións que non se poden automatizar con pytest. Anotar data, dispositivo e resultado.

## Deck de swipe (T5)

Páxina de proba con datos falsos: `/proba-deck/` (só con `DJANGO_DEBUG=1`).

| Comprobación | Chrome headless (emulación táctil 390×844) | Android real | iOS Safari real |
|---|---|---|---|
| Deslizar coa dedo á dereita → «Gústame» e anuncio para lectores | ✅ 2026-10-29 | ⏳ pendente | ⏳ pendente |
| Deslizar coa dedo á esquerda → «Non é para min» | ✅ 2026-10-29 | ⏳ | ⏳ |
| Arrastre curto (< 110 px) → a tarxeta volve ao sitio | ✅ 2026-10-29 | ⏳ | ⏳ |
| O xesto non fai scroll nin zoom da páxina | ✅ 2026-10-29 (scrollY = 0) | ⏳ | ⏳ |
| Arrastre co rato | ✅ 2026-10-29 | — | — |
| Teclado: ← → ↑ Z | ✅ 2026-10-29 | — | — |
| Botóns: Desfacer, Non, Gústame, Ver ficha | ✅ 2026-10-29 | ⏳ | ⏳ |
| Ao acabar os cans aparece o estado baleiro e desactívanse os botóns | ✅ 2026-10-29 | ⏳ | ⏳ |
| `prefers-reduced-motion`: sen animacións | ⏳ | ⏳ | ⏳ |

As probas automatizadas con Chrome usan o protocolo DevTools (eventos táctiles e de rato
reais). Quedan pendentes as comprobacións en dispositivos físicos.
