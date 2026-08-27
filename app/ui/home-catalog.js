// El catálogo del espacio de datos, en el portal público.
//
// Reúne la oferta de este nodo y la de los nodos dados de alta, cada una con
// el nodo que la ofrece. Aquí sólo se mira: negociar el contrato y descargar
// el dato se hace desde la consola, con sesión iniciada.
//
// Lee de `/api/v1/nodes` y del `/api/v1/catalog` de cada uno. La versión
// anterior pedía el catálogo a un servicio de gobernanza externo que este
// producto no tiene: la tabla salía siempre vacía y decía «No se encontraron
// productos de datos federados» en un nodo que tenía dos publicados.
(function () {
  "use strict";

  const isEn = String(document.documentElement.lang || "es")
    .toLowerCase()
    .startsWith("en");

  const T = isEn
    ? {
        cargando: "Loading the catalogue…",
        vacio: "No data products published yet.",
        error: "The catalogue could not be read.",
        nodoCaido: "not answering",
        cabeceras: ["Node", "Data product", "Description", "Access", "Policy"],
        resumen: (n, nodos) =>
          `${n} data product${n === 1 ? "" : "s"} from ${nodos} node${nodos === 1 ? "" : "s"}`,
        esteNodo: "this node",
        recargar: "Reload",
      }
    : {
        cargando: "Cargando el catálogo…",
        vacio: "Todavía no hay productos de datos publicados.",
        error: "No se pudo leer el catálogo.",
        nodoCaido: "no contesta",
        cabeceras: ["Nodo", "Producto de datos", "Descripción", "Acceso", "Política"],
        resumen: (n, nodos) =>
          `${n} producto${n === 1 ? "" : "s"} de datos de ${nodos} nodo${nodos === 1 ? "" : "s"}`,
        esteNodo: "este nodo",
        recargar: "Recargar",
      };

  const byId = (id) => document.getElementById(id);

  function escapar(valor) {
    return String(valor == null ? "" : valor).replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
    );
  }

  function propiedad(activo, clave) {
    const props = (activo && activo.properties) || {};
    return props[clave] || "";
  }

  async function leerJson(url, timeoutMs) {
    // Un nodo remoto que no contesta no puede dejar la página cargando para
    // siempre: se le da un plazo y se sigue con los demás.
    const control = new AbortController();
    const plazo = window.setTimeout(() => control.abort(), timeoutMs || 8000);
    try {
      const respuesta = await fetch(url, { cache: "no-store", signal: control.signal });
      if (!respuesta.ok) return null;
      return await respuesta.json();
    } catch (_err) {
      return null;
    } finally {
      window.clearTimeout(plazo);
    }
  }

  async function catalogoDeLosNodos() {
    const propio = await leerJson("/api/v1/catalog");
    const filas = [];
    const nodos = [];

    if (propio && Array.isArray(propio.assets)) {
      nodos.push({ id: propio.nodeId, etiqueta: propio.label, disponible: true });
      propio.assets.forEach((activo) =>
        filas.push({ nodo: propio.label || propio.nodeId, local: true, activo })
      );
    }

    // Los remotos, cada uno por su catálogo público. Se piden a la vez: en
    // serie, un nodo lento retrasa a todos los que van detrás.
    const lista = await leerJson("/api/v1/nodes");
    const remotos = ((lista && lista.items) || []).filter((n) => !n.local);

    const respuestas = await Promise.all(
      remotos.map((nodo) =>
        leerJson(`${String(nodo.baseUrl || "").replace(/\/$/, "")}/api/v1/catalog`).then(
          (catalogo) => ({ nodo, catalogo })
        )
      )
    );

    respuestas.forEach(({ nodo, catalogo }) => {
      const disponible = Boolean(catalogo && Array.isArray(catalogo.assets));
      nodos.push({ id: nodo.id, etiqueta: nodo.label || nodo.id, disponible });
      if (!disponible) return;
      catalogo.assets.forEach((activo) =>
        filas.push({ nodo: catalogo.label || nodo.label || nodo.id, local: false, activo })
      );
    });

    return { filas, nodos };
  }

  function pintarResumen(filas, nodos) {
    const destino = byId("federatedCatalogSummary");
    if (!destino) return;
    const caidos = nodos.filter((n) => !n.disponible);
    const origenes = nodos
      .map(
        (n) =>
          `<span class="pill${n.disponible ? "" : " is-down"}">${escapar(n.etiqueta)}` +
          `${n.disponible ? "" : ` — ${escapar(T.nodoCaido)}`}</span>`
      )
      .join(" ");
    destino.innerHTML =
      `<strong>${escapar(T.resumen(filas.length, nodos.length))}</strong> ${origenes}` +
      (caidos.length
        ? `<p class="muted">${escapar(
            isEn
              ? "A node that is not answering keeps its last known offer out of this view; the rest of the catalogue is unaffected."
              : "Un nodo que no contesta se queda fuera de esta vista; el resto del catálogo no se ve afectado."
          )}</p>`
        : "");
  }

  function pintarTabla(filas) {
    const tabla = byId("federatedCatalogTable");
    if (!tabla) return;

    if (!filas.length) {
      tabla.innerHTML = `<tbody><tr><td>${escapar(T.vacio)}</td></tr></tbody>`;
      return;
    }

    const cuerpo = filas
      .map((fila) => {
        const activo = fila.activo || {};
        const id = activo.id || activo["@id"] || "";
        return `<tr>
          <td>${escapar(fila.nodo)}${fila.local ? ` <span class="muted">(${escapar(T.esteNodo)})</span>` : ""}</td>
          <td><strong>${escapar(propiedad(activo, "dct:title") || id)}</strong></td>
          <td>${escapar(propiedad(activo, "dct:description"))}</td>
          <td>${escapar(propiedad(activo, "dct:accessRights"))}</td>
          <td>${escapar(propiedad(activo, "ods:policyId"))}</td>
        </tr>`;
      })
      .join("");

    tabla.innerHTML =
      `<thead><tr>${T.cabeceras.map((c) => `<th>${escapar(c)}</th>`).join("")}</tr></thead>` +
      `<tbody>${cuerpo}</tbody>`;
  }

  async function cargar() {
    const resumen = byId("federatedCatalogSummary");
    if (resumen) resumen.textContent = T.cargando;
    try {
      const { filas, nodos } = await catalogoDeLosNodos();
      pintarResumen(filas, nodos);
      pintarTabla(filas);
    } catch (err) {
      if (resumen) resumen.textContent = T.error;
      console.error(err);
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    byId("reloadFederatedCatalogBtn")?.addEventListener("click", cargar);
    cargar();
  });
})();
