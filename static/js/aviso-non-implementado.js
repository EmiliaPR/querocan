/*
 * Aviso para as funcionalidades que se ven na interface pero aínda non existen
 * (Apadriñar, Acollida e favoritos).
 *
 * Calquera elemento con o atributo data-non-implementado amosa a mensaxe nun aviso
 * flotante accesible (role="status") e non fai ningunha petición ao servidor.
 */
const MENSAXE = "Esta funcionalidade aínda non está implementada";
const DURACION_MS = 3500;
let temporizador = null;

/** Amosa unha mensaxe no aviso flotante común a todas as páxinas. */
export function amosarAviso(texto = MENSAXE) {
  const aviso = document.getElementById("aviso-flotante");
  if (!aviso) return;
  aviso.textContent = texto;
  aviso.classList.add("visible");
  clearTimeout(temporizador);
  temporizador = setTimeout(() => aviso.classList.remove("visible"), DURACION_MS);
}

// Un único escoitador para toda a páxina: serve tamén para elementos engadidos despois
document.addEventListener("click", (evento) => {
  const elemento = evento.target.closest("[data-non-implementado]");
  if (!elemento) return;
  evento.preventDefault();
  amosarAviso();
});

// Os selectores (p. ex. o filtro «Acollida») avisan e volven ao valor anterior
document.addEventListener("change", (evento) => {
  const opcion = evento.target.closest("[data-non-implementado-opcion]");
  if (!opcion) return;
  const valorNonImplementado = opcion.dataset.nonImplementadoOpcion;
  if (opcion.value === valorNonImplementado) {
    amosarAviso();
    opcion.value = opcion.dataset.valorPrevio ?? "";
  } else {
    opcion.dataset.valorPrevio = opcion.value;
  }
});
