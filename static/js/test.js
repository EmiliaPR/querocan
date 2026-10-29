/*
 * Test de compatibilidade paso a paso.
 *
 * Sen JavaScript vense as seis preguntas xuntas e funciona igual. Con JavaScript
 * amósase unha pregunta por pantalla con «Atrás» e «Seguinte», como na proposta.
 */
const formulario = document.querySelector("[data-test]");

if (formulario) {
  const preguntas = [...formulario.querySelectorAll("[data-pregunta]")];
  const atras = formulario.querySelector("[data-test-atras]");
  const seguinte = formulario.querySelector("[data-test-seguinte]");
  const enviar = formulario.querySelector("[data-test-enviar]");

  // Se o servidor devolveu erros, empezamos na primeira pregunta sen responder
  let actual = Math.max(0, preguntas.findIndex((p) => !respondida(p)));
  if (actual === -1) actual = 0;
  formulario.classList.add("test--paso-a-paso");

  function respondida(pregunta) {
    const grupos = new Set([...pregunta.querySelectorAll("input[type=radio]")].map((i) => i.name));
    return [...grupos].every((nome) => pregunta.querySelector(`input[name="${nome}"]:checked`));
  }

  function amosar(indice, moverFoco = true) {
    actual = indice;
    preguntas.forEach((p, i) => p.classList.toggle("actual", i === indice));
    const ultima = indice === preguntas.length - 1;
    atras.hidden = indice === 0;
    seguinte.hidden = ultima;
    enviar.hidden = !ultima;
    actualizarBotons();
    if (moverFoco) preguntas[indice].querySelector("h1").focus({ preventScroll: false });
  }

  function actualizarBotons() {
    const lista = respondida(preguntas[actual]);
    seguinte.disabled = !lista;
    enviar.disabled = !lista;
  }

  preguntas.forEach((p) => p.querySelector("h1").setAttribute("tabindex", "-1"));
  atras.addEventListener("click", () => amosar(actual - 1));
  seguinte.addEventListener("click", () => amosar(actual + 1));
  // Non avanzamos soas ao escoller: coas frechas do teclado cámbiase de opción e
  // pasar de pregunta sen avisar desorientaría a quen navega así
  formulario.addEventListener("change", actualizarBotons);

  amosar(actual, false);
}
