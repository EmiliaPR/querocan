/*
 * Páxina de proba do deck con datos falsos (só en desenvolvemento).
 * Serve para validar o xesto en móbiles reais sen depender do servidor.
 */
import { Deck } from "./deck.js";

const NOMES = ["Luna", "Rufus", "Nina", "Bruno", "Mel", "Toby", "Lúa", "Trasno", "Chispa", "Óscar"];
let seguinte = 0;

function canFalso(indice) {
  return {
    id: indice,
    nome: NOMES[indice % NOMES.length],
    idade: `${(indice % 9) + 1} anos`,
    distancia: `${5 + indice * 7} km`,
    protectora: "Protectora de proba",
    foto: null,
    urxente: indice % 4 === 0,
    porcentaxe: 95 - indice * 6,
    motivos: [
      { icona: "✓", texto: "Tes o patio que lle convén", encaixa: true },
      { icona: "⚠", texto: "Pasaría máis tempo só do que lle convén", encaixa: false },
    ],
    url_ficha: "#ficha",
  };
}

const deck = new Deck(document.querySelector("[data-deck]"), {
  cargar: async () => {
    if (seguinte >= 10) return [];
    const tanda = Array.from({ length: 5 }, () => canFalso(seguinte++));
    return tanda;
  },
  decidir: async (can, decision) => console.info("Decisión", can.nome, decision),
  desfacer: async (can) => console.info("Desfeito", can.nome),
});
deck.iniciar();
