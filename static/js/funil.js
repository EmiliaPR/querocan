/*
 * Gráfica do funil de adopción (Chart.js). Unha soa serie: barras horizontais nun
 * único ton, coas cifras escritas ao final de cada barra. A táboa da páxina ten os
 * mesmos datos para quen non vexa a gráfica.
 */
(function () {
  const lenzo = document.getElementById("grafica-funil");
  const fonte = document.getElementById("datos-funil");
  if (!lenzo || !fonte || !window.Chart) return;

  const datos = JSON.parse(fonte.textContent);
  const estilos = getComputedStyle(document.documentElement);
  const cor = (nome) => estilos.getPropertyValue(nome).trim();

  // Escribe o valor ao final de cada barra (etiquetado directo, sen lenda)
  const valoresNasBarras = {
    id: "valoresNasBarras",
    afterDatasetsDraw(grafica) {
      const { ctx } = grafica;
      ctx.save();
      ctx.fillStyle = cor("--cor-texto");
      ctx.font = `700 14px ${cor("--fonte-texto")}`;
      ctx.textBaseline = "middle";
      grafica.getDatasetMeta(0).data.forEach((barra, i) => {
        ctx.fillText(String(datos.valores[i]), barra.x + 8, barra.y);
      });
      ctx.restore();
    },
  };

  new window.Chart(lenzo, {
    type: "bar",
    data: {
      labels: datos.etiquetas,
      datasets: [
        {
          label: "Solicitudes",
          data: datos.valores,
          backgroundColor: cor("--borgona"),
          hoverBackgroundColor: cor("--vino-profundo"),
          borderRadius: 4,
          borderSkipped: "start",
          barThickness: 28,
        },
      ],
    },
    options: {
      indexAxis: "y",
      maintainAspectRatio: false,
      animation: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? false : undefined,
      layout: { padding: { right: 40 } },
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: (c) => ` ${c.parsed.x} solicitudes` } },
      },
      scales: {
        x: {
          beginAtZero: true,
          ticks: { precision: 0, color: cor("--texto-secundario") },
          grid: { color: cor("--borde") },
        },
        y: { ticks: { color: cor("--cor-texto"), font: { weight: 700 } }, grid: { display: false } },
      },
    },
    plugins: [valoresNasBarras],
  });
})();
