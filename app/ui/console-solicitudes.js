// Altas pendientes y participantes del nodo, dentro de la consola.
//
// Sustituye a console-audit.js, que no llegaba a ejecutarse nunca en este
// producto: empezaba por `if (cfg.id !== "connector-1") return;` -- un
// identificador del proyecto de origen -- y ademas buscaba los identificadores
// de un console.html que la consola generada no tiene. El resultado era que
// alguien se daba de alta, se le pedia esperar, y no habia ningun sitio en el
// producto donde aprobarle.
(function () {
  const boton = document.getElementById("operationRequestsBtn");
  const panel = document.getElementById("operationRequestsPanel");
  const recargarSolicitudes = document.getElementById("reloadConnectorRequestsBtn");
  const estadoSolicitudes = document.getElementById("connectorRequestsStatus");
  const tablaSolicitudes = document.getElementById("connectorRequestsTable");
  const recargarDirectorio = document.getElementById("reloadConnectorDirectoryBtn");
  const estadoDirectorio = document.getElementById("connectorDirectoryStatus");
  const tablaDirectorio = document.getElementById("connectorDirectoryTable");

  if (!boton || !panel || !recargarSolicitudes || !estadoSolicitudes || !tablaSolicitudes
      || !recargarDirectorio || !estadoDirectorio || !tablaDirectorio) {
    return;
  }

  const cfg = window.CONNECTOR_CONFIG || {};
  const en = String(cfg.lang || document.documentElement.lang || "es").toLowerCase().startsWith("en");
  const T = en
    ? {
        cargando: "Loading pending requests...", cargadas: "Pending requests loaded",
        sinFilas: "No pending requests", error: "Failed to load pending requests",
        dirCargando: "Loading participants...", dirCargados: "Participants loaded",
        dirSinFilas: "No participants yet", dirError: "Failed to load participants",
        id: "Request", nombre: "Name", correo: "Email", perfil: "Profile",
        creada: "Requested", accion: "Action", aprobar: "Approve", denegar: "Deny",
        aprobada: "Approved", denegada: "Denied", trabajando: "Working...",
        conector: "Connector", tipo: "Profile", estado: "Status",
        sinSesion: "Could not read the session token."
      }
    : {
        cargando: "Cargando solicitudes pendientes...", cargadas: "Solicitudes pendientes cargadas",
        sinFilas: "No hay solicitudes pendientes", error: "No se pudieron cargar las solicitudes",
        dirCargando: "Cargando participantes...", dirCargados: "Participantes cargados",
        dirSinFilas: "Todavia no hay participantes", dirError: "No se pudieron cargar los participantes",
        id: "Solicitud", nombre: "Nombre", correo: "Correo", perfil: "Perfil",
        creada: "Solicitada", accion: "Accion", aprobar: "Aprobar", denegar: "Denegar",
        aprobada: "Aprobada", denegada: "Denegada", trabajando: "Trabajando...",
        conector: "Conector", tipo: "Perfil", estado: "Estado",
        sinSesion: "No se pudo leer el token de la sesion."
      };

  const estado = { cargadasUnaVez: false, directorioUnaVez: false };

  function escapar(valor) {
    return String(valor === undefined || valor === null ? "" : valor)
      .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;").replaceAll("'", "&#39;");
  }

  function decirEstado(nodo, mensaje, esError) {
    nodo.textContent = mensaje;
    nodo.classList.remove("status-ok", "status-error");
    nodo.classList.add(esError ? "status-error" : "status-ok");
  }

  function pintar(tabla, filas, cabeceras, vacio) {
    const cabeza = cabeceras.map((c) => `<th>${escapar(c)}</th>`).join("");
    if (!filas.length) {
      tabla.innerHTML = `<thead><tr>${cabeza}</tr></thead>`
        + `<tbody><tr><td colspan="${cabeceras.length}">${escapar(vacio)}</td></tr></tbody>`;
      return;
    }
    const cuerpo = filas.map((fila) => "<tr>" + fila.map((celda) => (
      celda && typeof celda === "object" && celda.html
        ? `<td>${celda.html}</td>`
        : `<td>${escapar(celda)}</td>`
    )).join("") + "</tr>").join("");
    tabla.innerHTML = `<thead><tr>${cabeza}</tr></thead><tbody>${cuerpo}</tbody>`;
  }

  function fecha(valor) {
    if (!valor) return "-";
    const d = new Date(valor);
    if (Number.isNaN(d.getTime())) return String(valor);
    return new Intl.DateTimeFormat(en ? "en-GB" : "es-ES",
      { dateStyle: "short", timeStyle: "short" }).format(d);
  }

  function esperar(ms) {
    return new Promise((resolve) => window.setTimeout(resolve, ms));
  }

  // El token de acceso, no el de identidad: los grupos -- que es lo que decide
  // si esta persona puede aprobar -- viajan en el primero.
  async function token() {
    if (typeof window.__DATASPACE_ENSURE_FRESH_TOKEN === "function") {
      try {
        const fresco = await window.__DATASPACE_ENSURE_FRESH_TOKEN();
        if (fresco) return fresco;
      } catch (_err) { /* se intenta abajo */ }
    }
    for (let i = 0; i < 20; i += 1) {
      if (window.__DATASPACE_ACCESS_TOKEN) return window.__DATASPACE_ACCESS_TOKEN;
      await esperar(200);
    }
    throw new Error(T.sinSesion);
  }

  async function pedir(url, opciones = {}) {
    const acceso = await token();
    const res = await fetch(url, {
      method: opciones.method || "GET",
      headers: {
        Authorization: `Bearer ${acceso}`,
        "Content-Type": "application/json",
        Accept: "application/json"
      },
      body: opciones.body ? JSON.stringify(opciones.body) : undefined
    });
    const datos = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(datos.message || datos.error || String(res.status));
    return datos;
  }

  function grupos(jwt) {
    try {
      const cuerpo = JSON.parse(atob(String(jwt).split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
      return (cuerpo.groups || []).map((g) => String(g || "").replace(/^\//, ""));
    } catch (_err) {
      return [];
    }
  }

  async function cargarSolicitudes() {
    decirEstado(estadoSolicitudes, T.cargando, false);
    try {
      const datos = await pedir("/api/onboarding/requests?status=pending");
      const items = Array.isArray(datos.items) ? datos.items : [];
      pintar(tablaSolicitudes, items.map((item) => {
        const acciones = `<button type="button" class="secondary accion-solicitud" `
          + `data-solicitud="${escapar(item.requestId)}" data-accion="approve">${escapar(T.aprobar)}</button> `
          + `<button type="button" class="secondary accion-solicitud" `
          + `data-solicitud="${escapar(item.requestId)}" data-accion="deny">${escapar(T.denegar)}</button>`;
        return [
          item.requestId || "-",
          [item.firstName || "", item.lastName || ""].filter(Boolean).join(" ") || "-",
          item.email || "-",
          item.requestedRoleMode || "-",
          fecha(item.createdAt),
          { html: acciones }
        ];
      }), [T.id, T.nombre, T.correo, T.perfil, T.creada, T.accion], T.sinFilas);
      decirEstado(estadoSolicitudes, T.cargadas, false);
      estado.cargadasUnaVez = true;
    } catch (err) {
      decirEstado(estadoSolicitudes, `${T.error}: ${err.message}`, true);
    }
  }

  async function cargarDirectorio() {
    decirEstado(estadoDirectorio, T.dirCargando, false);
    try {
      // Con el token: el directorio lleva datos personales y ya no se sirve
      // a quien no se identifique.
      const datos = await pedir("/api/onboarding/connectors");
      const items = Array.isArray(datos.items) ? datos.items : [];
      pintar(tablaDirectorio, items.map((item) => [
        item.connectorId || "-",
        [item.firstName || "", item.lastName || ""].filter(Boolean).join(" ") || "-",
        item.email || "-",
        item.roleMode || "-",
        item.status || "-"
      ]), [T.conector, T.nombre, T.correo, T.tipo, T.estado], T.dirSinFilas);
      decirEstado(estadoDirectorio, T.dirCargados, false);
      estado.directorioUnaVez = true;
    } catch (err) {
      decirEstado(estadoDirectorio, `${T.dirError}: ${err.message}`, true);
    }
  }

  tablaSolicitudes.addEventListener("click", async (evento) => {
    const boton = evento.target.closest(".accion-solicitud");
    if (!boton) return;
    const solicitud = boton.getAttribute("data-solicitud");
    const accion = boton.getAttribute("data-accion");
    if (!solicitud || !accion) return;
    // Se desactivan los dos botones de la fila: pulsar «aprobar» y «denegar»
    // seguidos sobre la misma solicitud es facil, y la segunda llamada
    // devolveria un error que no dice nada util.
    panel.querySelectorAll(".accion-solicitud").forEach((b) => { b.disabled = true; });
    decirEstado(estadoSolicitudes, T.trabajando, false);
    try {
      await pedir(`/api/onboarding/requests/${encodeURIComponent(solicitud)}/${accion}`,
                  { method: "POST", body: {} });
      decirEstado(estadoSolicitudes, accion === "approve" ? T.aprobada : T.denegada, false);
      await cargarSolicitudes();
      await cargarDirectorio();
    } catch (err) {
      decirEstado(estadoSolicitudes, `${T.error}: ${err.message}`, true);
      panel.querySelectorAll(".accion-solicitud").forEach((b) => { b.disabled = false; });
    }
  });

  recargarSolicitudes.addEventListener("click", cargarSolicitudes);
  recargarDirectorio.addEventListener("click", cargarDirectorio);

  // La pestana solo aparece para quien administra el nodo. Se mira el token,
  // no una lista de correos: el servidor decide lo mismo con los mismos
  // grupos, asi que esto no concede nada, solo evita ensenar una pantalla que
  // solo sabria decir «no puedes».
  (async () => {
    let puede = false;
    try {
      puede = grupos(await token()).includes("dataspace-admins");
    } catch (_err) {
      puede = false;
    }
    if (!puede) return;
    // El cambio de panel lo gobierna app.js; aqui solo se pide que la pestana
    // aparezca. Si esa funcion no esta -- otra version de la consola -- se
    // ensena el boton igual, que es mejor que dejar la pantalla inalcanzable.
    if (typeof window.__ODS_MOSTRAR_PESTANA === "function") {
      window.__ODS_MOSTRAR_PESTANA("operationRequestsPanel");
    } else {
      boton.hidden = false;
      boton.classList.remove("hidden");
    }
    boton.addEventListener("click", () => {
      if (!estado.cargadasUnaVez) cargarSolicitudes();
      if (!estado.directorioUnaVez) cargarDirectorio();
    });
  })();
})();
