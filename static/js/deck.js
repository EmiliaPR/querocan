/*
 * Deck de tarxetas con swipe (o xesto de deslizar de QueroCan).
 *
 * Amosa unha pila de tarxetas de cans. A de enriba pódese:
 *   - deslizar á dereita  → «Gústame»  (crea a solicitude de adopción)
 *   - deslizar á esquerda → «Non é para min»
 *   - deslizar cara arriba → «Ver ficha»
 * e «Desfacer» recupera a última decisión.
 *
 * Accesibilidade: cada xesto ten o seu botón e o seu atallo de teclado (← → ↑ Z).
 * Xestos, botóns e teclado chaman todos á mesma función, decidir(), así que nunca
 * se comportan de xeito distinto.
 *
 * O deck non sabe nada do servidor: recibe tres funcións (cargar, decidir e desfacer)
 * que devolven promesas. Así pódese probar con datos falsos (proba_deck.html) e usar
 * con datos reais (deck.html) sen cambiar este ficheiro.
 */

// Distancia mínima (en px) ou velocidade (px/ms) para que un arrastre conte como decisión
const LIMIAR_DISTANCIA = 110;
const LIMIAR_VELOCIDADE = 0.6;
// Cantas tarxetas se debuxan na pila (a de enriba e as que asoman detrás)
const TARXETAS_VISIBLES = 3;
// Cando quedan menos tarxetas que isto, pídense máis ao servidor
const MINIMO_ANTES_DE_CARGAR = 4;

export const DECISION = Object.freeze({
  GUSTAME: "gustame",
  NON: "non",
});

const sinMovemento = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/** Escapa texto para metelo en HTML sen risco de inxección. */
function escapar(texto) {
  const div = document.createElement("div");
  div.textContent = texto ?? "";
  return div.innerHTML;
}

export class Deck {
  /**
   * @param {HTMLElement} raiz    Elemento .deck que contén a pila, os botóns e o anuncio.
   * @param {object} accions
   * @param {() => Promise<object[]>} accions.cargar   Devolve a seguinte tanda de cans.
   * @param {(can: object, decision: string) => Promise<object|void>} accions.decidir
   * @param {(can: object, decision: string) => Promise<void>} accions.desfacer
   * @param {(can: object|null) => void} [accions.aoCambiar]  Avisa cando cambia a tarxeta de enriba.
   */
  constructor(raiz, { cargar, decidir, desfacer, aoCambiar = () => {} }) {
    this.raiz = raiz;
    this.pila = raiz.querySelector("[data-deck-pila]");
    this.anuncio = raiz.querySelector("[data-deck-anuncio]");
    this.baleiro = raiz.querySelector("[data-deck-baleiro]");
    this.botonDesfacer = raiz.querySelector('[data-deck-accion="desfacer"]');
    this.accions = { cargar, decidir, desfacer, aoCambiar };

    this.cola = [];        // cans pendentes de amosar (o primeiro é o de enriba)
    this.historial = [];   // decisións feitas, para poder desfacelas
    this.ocupado = false;  // evita dúas decisións á vez mentres dura unha animación
    this.semMais = false;  // o servidor xa non ten máis cans
    this.arrastre = null;  // estado do xesto en curso

    this.#enlazarBotons();
    this.#enlazarTeclado();
  }

  /** Carga a primeira tanda e debuxa a pila. */
  async iniciar() {
    await this.#cargarMais();
    this.#debuxar();
  }

  /** Can que está enriba da pila (ou null se non quedan). */
  get actual() {
    return this.cola[0] ?? null;
  }

  // -----------------------------------------------------------------------------------
  // Accións públicas: as mesmas para xestos, botóns e teclado
  // -----------------------------------------------------------------------------------

  /** Decide sobre o can de enriba: DECISION.GUSTAME ou DECISION.NON. */
  async decidir(decision) {
    const can = this.actual;
    if (!can || this.ocupado) return;
    this.ocupado = true;
    const tarxeta = this.#tarxetaDeEnriba();
    try {
      await this.#animarSaida(tarxeta, decision === DECISION.GUSTAME ? 1 : -1);
      const resposta = await this.accions.decidir(can, decision);
      // O servidor pode cortar a decisión (p. ex. hai que entrar ou facer o test)
      if (resposta && resposta.redirixir) {
        window.location.href = resposta.redirixir;
        return;
      }
      this.cola.shift();
      this.historial.push({ can, decision });
      this.#anunciar(
        decision === DECISION.GUSTAME
          ? `Gústache ${can.nome}. Enviamos a solicitude á protectora.`
          : `Descartaches a ${can.nome}.`
      );
      if (this.cola.length < MINIMO_ANTES_DE_CARGAR) await this.#cargarMais();
    } catch (erro) {
      console.error(erro);
      this.#anunciar("Non se puido gardar a decisión. Téntao de novo.");
    } finally {
      this.ocupado = false;
      this.#debuxar();
    }
  }

  /** Volve poñer enriba o último can decidido. */
  async desfacer() {
    const ultimo = this.historial.at(-1);
    if (!ultimo || this.ocupado) return;
    this.ocupado = true;
    try {
      await this.accions.desfacer(ultimo.can, ultimo.decision);
      this.historial.pop();
      this.cola.unshift(ultimo.can);
      this.#anunciar(`Volve estar ${ultimo.can.nome}.`);
    } catch (erro) {
      console.error(erro);
      this.#anunciar("Non se puido desfacer a última decisión.");
    } finally {
      this.ocupado = false;
      this.#debuxar({ entrada: true });
    }
  }

  /** Abre a ficha completa do can de enriba. */
  verFicha() {
    if (this.actual?.url_ficha) window.location.href = this.actual.url_ficha;
  }

  // -----------------------------------------------------------------------------------
  // Debuxo da pila
  // -----------------------------------------------------------------------------------

  #debuxar({ entrada = false } = {}) {
    this.pila.replaceChildren();
    const visibles = this.cola.slice(0, TARXETAS_VISIBLES);
    // Debuxámolas ao revés para que a primeira quede enriba no DOM
    [...visibles].reverse().forEach((can, indiceInverso) => {
      const posicion = visibles.length - 1 - indiceInverso;
      this.pila.append(this.#crearTarxeta(can, posicion));
    });

    const tarxeta = this.#tarxetaDeEnriba();
    if (tarxeta) {
      this.#enlazarArrastre(tarxeta);
      if (entrada && !sinMovemento()) {
        tarxeta.animate(
          [{ transform: "translateY(-40px) scale(1.04)", opacity: 0 }, { transform: "none", opacity: 1 }],
          { duration: 220, easing: "ease-out" }
        );
      }
    }

    const quedanCans = this.cola.length > 0;
    this.baleiro.hidden = quedanCans;
    this.raiz.querySelectorAll("[data-deck-accion]").forEach((boton) => {
      const accion = boton.dataset.deckAccion;
      boton.disabled = accion === "desfacer" ? this.historial.length === 0 : !quedanCans;
    });
    this.accions.aoCambiar(this.actual);
  }

  #crearTarxeta(can, posicion) {
    const tarxeta = document.createElement("article");
    tarxeta.className = "tarxeta-deck";
    tarxeta.dataset.posicion = posicion;
    tarxeta.style.setProperty("--posicion", posicion);
    if (posicion > 0) {
      // As tarxetas de detrás son decorativas: fóra do foco e dos lectores de pantalla
      tarxeta.setAttribute("aria-hidden", "true");
      tarxeta.inert = true;
    } else {
      tarxeta.setAttribute("aria-label", `${can.nome}, ${can.idade}`);
    }

    const foto = can.foto
      ? `<img class="tarxeta-deck__foto" src="${escapar(can.foto)}" alt="" draggable="false">`
      : `<div class="tarxeta-deck__foto foto-baleira">Sen foto</div>`;
    const porcentaxe =
      can.porcentaxe != null
        ? `<p class="tarxeta-deck__porcentaxe" aria-label="${can.porcentaxe} % de compatibilidade">${can.porcentaxe}%</p>`
        : "";
    const motivos = (can.motivos ?? [])
      .map(
        (m) =>
          `<li class="etiqueta ${m.encaixa ? "etiqueta--ok" : "etiqueta--aviso"}"><span aria-hidden="true">${m.icona}</span> ${escapar(m.texto)}</li>`
      )
      .join("");
    const urxente = can.urxente ? `<span class="etiqueta etiqueta--forte">Urxente</span>` : "";

    tarxeta.innerHTML = `
      ${foto}
      <div class="tarxeta-deck__selo tarxeta-deck__selo--si" aria-hidden="true">Gústame</div>
      <div class="tarxeta-deck__selo tarxeta-deck__selo--non" aria-hidden="true">Non</div>
      ${porcentaxe}
      <div class="tarxeta-deck__info">
        <div class="fila">${urxente}</div>
        <h2 class="tarxeta-deck__nome">${escapar(can.nome)}, ${escapar(can.idade)}</h2>
        <p class="tarxeta-deck__lugar">${can.distancia ? `A ${escapar(can.distancia)} · ` : ""}${escapar(can.protectora)}</p>
        ${motivos ? `<ul class="etiquetas tarxeta-deck__motivos">${motivos}</ul>` : ""}
      </div>`;
    return tarxeta;
  }

  #tarxetaDeEnriba() {
    return this.pila.querySelector('.tarxeta-deck[data-posicion="0"]');
  }

  // -----------------------------------------------------------------------------------
  // Xesto de arrastre con Pointer Events (rato, dedo e lapis co mesmo código)
  // -----------------------------------------------------------------------------------

  #enlazarArrastre(tarxeta) {
    tarxeta.addEventListener("pointerdown", (evento) => {
      if (this.ocupado || evento.button > 0) return;
      tarxeta.setPointerCapture(evento.pointerId);
      tarxeta.classList.add("arrastrando");
      this.arrastre = { x0: evento.clientX, y0: evento.clientY, t0: performance.now(), dx: 0, dy: 0 };
    });

    tarxeta.addEventListener("pointermove", (evento) => {
      if (!this.arrastre) return;
      const dx = evento.clientX - this.arrastre.x0;
      const dy = evento.clientY - this.arrastre.y0;
      Object.assign(this.arrastre, { dx, dy });
      tarxeta.style.transform = `translate(${dx}px, ${dy}px) rotate(${dx * 0.05}deg)`;
      // Os selos «Gústame» / «Non» aparecen segundo a dirección
      const forza = Math.min(Math.abs(dx) / LIMIAR_DISTANCIA, 1);
      tarxeta.style.setProperty("--forza-si", dx > 0 ? forza : 0);
      tarxeta.style.setProperty("--forza-non", dx < 0 ? forza : 0);
    });

    const rematar = () => {
      if (!this.arrastre) return;
      const { dx, dy, t0 } = this.arrastre;
      this.arrastre = null;
      tarxeta.classList.remove("arrastrando");
      const tempo = Math.max(performance.now() - t0, 1);
      const rapido = Math.abs(dx) / tempo > LIMIAR_VELOCIDADE;
      const horizontal = Math.abs(dx) > Math.abs(dy);

      if (horizontal && (Math.abs(dx) > LIMIAR_DISTANCIA || (rapido && Math.abs(dx) > 30))) {
        this.decidir(dx > 0 ? DECISION.GUSTAME : DECISION.NON);
      } else if (!horizontal && dy < -LIMIAR_DISTANCIA) {
        this.#volverAoSitio(tarxeta);
        this.verFicha();
      } else {
        this.#volverAoSitio(tarxeta);
      }
    };
    tarxeta.addEventListener("pointerup", rematar);
    tarxeta.addEventListener("pointercancel", () => {
      this.arrastre = null;
      tarxeta.classList.remove("arrastrando");
      this.#volverAoSitio(tarxeta);
    });
  }

  #volverAoSitio(tarxeta) {
    tarxeta.style.transform = "";
    tarxeta.style.setProperty("--forza-si", 0);
    tarxeta.style.setProperty("--forza-non", 0);
  }

  /** Saída da tarxeta pola dereita (1) ou pola esquerda (-1). */
  async #animarSaida(tarxeta, direccion) {
    if (!tarxeta) return;
    tarxeta.style.setProperty(direccion > 0 ? "--forza-si" : "--forza-non", 1);
    if (sinMovemento()) return;
    const actual = getComputedStyle(tarxeta).transform;
    const animacion = tarxeta.animate(
      [
        { transform: actual === "none" ? "none" : actual },
        { transform: `translate(${direccion * 150}%, 20px) rotate(${direccion * 18}deg)`, opacity: 0 },
      ],
      { duration: 260, easing: "ease-in", fill: "forwards" }
    );
    await animacion.finished;
  }

  // -----------------------------------------------------------------------------------
  // Botóns, teclado, carga e anuncios
  // -----------------------------------------------------------------------------------

  #enlazarBotons() {
    this.raiz.addEventListener("click", (evento) => {
      const boton = evento.target.closest("[data-deck-accion]");
      if (!boton || boton.disabled) return;
      const accion = boton.dataset.deckAccion;
      if (accion === "gustame") this.decidir(DECISION.GUSTAME);
      else if (accion === "non") this.decidir(DECISION.NON);
      else if (accion === "desfacer") this.desfacer();
      else if (accion === "ficha") this.verFicha();
    });
  }

  #enlazarTeclado() {
    document.addEventListener("keydown", (evento) => {
      // Non interferimos cando se escribe nun campo nin con atallos do navegador
      if (evento.target.closest("input, textarea, select, [contenteditable]")) return;
      if (evento.ctrlKey || evento.metaKey || evento.altKey) return;
      const accions = {
        ArrowRight: () => this.decidir(DECISION.GUSTAME),
        ArrowLeft: () => this.decidir(DECISION.NON),
        ArrowUp: () => this.verFicha(),
        z: () => this.desfacer(),
        Z: () => this.desfacer(),
      };
      const accion = accions[evento.key];
      if (accion) {
        evento.preventDefault();
        accion();
      }
    });
  }

  async #cargarMais() {
    if (this.semMais) return;
    const novos = await this.accions.cargar(this.cola.map((can) => can.id));
    const xaNaCola = new Set(this.cola.map((can) => can.id));
    const unicos = novos.filter((can) => !xaNaCola.has(can.id));
    if (unicos.length === 0) this.semMais = true;
    this.cola.push(...unicos);
  }

  #anunciar(texto) {
    if (this.anuncio) this.anuncio.textContent = texto;
  }
}
