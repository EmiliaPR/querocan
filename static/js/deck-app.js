/*
 * Conecta o deck (deck.js) coa API do servidor (animais/api.py).
 * Tamén enche o panel de detalles do can de enriba (só se ve en escritorio).
 */
import { Deck } from "./deck.js";

const paxina = document.querySelector("[data-api]");
const token = document.querySelector("input[name=csrfmiddlewaretoken]")?.value;

/** POST con JSON e o token CSRF que esixe Django. */
async function enviar(url, datos) {
  const resposta = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRFToken": token },
    credentials: "same-origin",
    body: JSON.stringify(datos),
  });
  const corpo = await resposta.json().catch(() => ({}));
  if (!resposta.ok) throw new Error(corpo.erro || `Erro ${resposta.status}`);
  return corpo;
}

function encherDetalle(can) {
  const panel = document.querySelector("[data-deck-detalle]");
  if (!panel) return;
  panel.hidden = !can;
  if (!can) return;
  const campo = (nome) => panel.querySelector(`[data-detalle="${nome}"]`);
  campo("titulo").textContent = `Coñece a ${can.nome}`;
  campo("idade").textContent = can.idade;
  campo("tamano").textContent = can.tamano;
  campo("convivencia").textContent = can.convivencia;
  campo("descricion").textContent = can.descricion;
  campo("ficha").href = can.url_ficha;
  const etiquetas = campo("etiquetas");
  etiquetas.replaceChildren(
    ...can.etiquetas.map((texto) => Object.assign(document.createElement("li"), { className: "etiqueta", textContent: texto }))
  );
  if (can.urxente) {
    etiquetas.append(Object.assign(document.createElement("li"), { className: "etiqueta etiqueta--forte", textContent: "Urxente" }));
  }
}

if (paxina) {
  const filtros = paxina.dataset.filtros;
  const deck = new Deck(paxina.querySelector("[data-deck]"), {
    cargar: async (naPila) => {
      const parametros = new URLSearchParams(filtros);
      parametros.set("excluir", naPila.join(","));
      const resposta = await fetch(`${paxina.dataset.api}?${parametros}`, { credentials: "same-origin" });
      return (await resposta.json()).cans;
    },
    decidir: (can, decision) => enviar(paxina.dataset.apiDecision, { can: can.id, decision }),
    desfacer: (can, decision) => enviar(paxina.dataset.apiDesfacer, { can: can.id, decision }),
    aoCambiar: encherDetalle,
  });
  deck.iniciar();
}
