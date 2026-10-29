/*
 * «Usar a miña localización»: pide a posición ao navegador e envíaa ao servidor.
 * Se o navegador non a ofrece ou a persoa a denega, queda o selector de concello.
 * (A xeolocalización só funciona en HTTPS ou en localhost.)
 */
const formulario = document.querySelector("[data-xeolocalizacion]");

if (formulario && "geolocation" in navigator) {
  const boton = formulario.querySelector("[data-xeolocalizacion-boton]");
  const estado = document.querySelector("[data-xeolocalizacion-estado]");
  formulario.hidden = false;

  boton.addEventListener("click", () => {
    boton.disabled = true;
    estado.textContent = "Buscando a túa localización…";
    navigator.geolocation.getCurrentPosition(
      (posicion) => {
        formulario.latitude.value = posicion.coords.latitude.toFixed(5);
        formulario.lonxitude.value = posicion.coords.longitude.toFixed(5);
        formulario.submit();
      },
      () => {
        boton.disabled = false;
        estado.textContent = "Non puidemos obter a localización. Escolle o teu concello.";
        document.getElementById("id_concello")?.focus();
      },
      { timeout: 10000, maximumAge: 600000 }
    );
  });
}
