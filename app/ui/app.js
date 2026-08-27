(function () {
  const cfg = window.CONNECTOR_CONFIG;
  if (!cfg) {
    throw new Error("Missing CONNECTOR_CONFIG");
  }

  const lang = String(cfg.lang || document.documentElement.lang || "es").toLowerCase().startsWith("en") ? "en" : "es";
  const t = {
    es: {
      missingToken: "No hay token de acceso de Keycloak",
      keycloakUnavailable: "Keycloak JS no disponible",
      keycloakImportError: "Keycloak JS no disponible",
      keycloakAuthFailed: "No se pudo autenticar con Keycloak",
      refreshFailed: "No se pudo refrescar token",
      tableId: "ID",
      tableName: "Nombre",
      tableDescription: "Descripción",
      tableLicense: "Licencia",
      tableAssetDescription: "Descripción",
      tablePolicy: "Política",
      tableContract: "Contrato",
      tableAsset: "Activo",
      tableConsumer: "Consumidor",
      tableProvider: "Proveedor",
      tableStatus: "Estado",
      tableDownload: "Descarga",
      tableAction: "Acción",
      tableMetadata: "Metadatos",
      pending: "Pendiente",
      notAvailable: "No disponible",
      download: "Descargar",
      ownAsset: "Activo propio",
      negotiate: "Aceptar",
      acceptPolicy: "Aceptar",
      policyClausesUnavailable: "Se aceptará la política publicada por el proveedor.",
      policyDetailsInternal: "Uso interno",
      policyDetailsAi: "Uso para IA",
      policyDetailsRedistribution: "Redistribución",
      policyDetailsPermitted: "Permitido",
      policyDetailsProhibited: "Prohibido",
      policyDetailsDuties: "Obligaciones",
      incompleteNegotiationData: "Datos de negociación incompletos",
      ownAssetNegotiationDenied: "No se negocian assets propios",
      providerNotConfigured: "Proveedor no configurado",
      negotiationCompleted: "Negociación completada para asset",
      negotiationError: "Error negociación",
      downloadStarted: "Descarga iniciada",
      downloadError: "Error descarga",
      dashboardOpened: "Cuadro de mando abierto",
      dashboardOpenError: "Error al abrir el cuadro de mando",
      catalogsLoaded: "Catálogos cargados",
      federatedReloaded: "Catálogo federado recargado",
      governanceCatalogUnavailable: "Catálogo federado de governance no disponible; usando Fuseki local",
      governanceRemoteReadOnly: "Visible en el catálogo del espacio de datos",
      governanceNegotiationCompleted: "Negociación federada completada",
      governanceNegotiationError: "Error en negociación federada",
      negotiationStarting: "Iniciando negociación",
      governanceNegotiationStarting: "Iniciando negociación federada",
      openAsset: "Abrir activo",
      auditPublished: "Evento de auditoría publicado",
      auditPublishError: "No se pudo publicar el evento de auditoría",
      assetMetadataIncomplete: "Revisa nombre y descripción antes de crear el asset",
      assetMetadataValidating: "Validando metadatos DCAT-AP...",
      assetMetadataValidationPassed: "Validación DCAT-AP superada",
      assetMetadataValidationFailed: "Validación DCAT-AP fallida",
      assetMetadataValidationLabel: "Validación DCAT-AP",
      assetMetadataValidationScore: "Puntuación",
      assetMetadataValidationMissing: "Campos obligatorios pendientes",
      assetMetadataValidationWarnings: "Avisos",
      assetMetadataValidationRecommendations: "Recomendaciones",
      assetCreated: "Asset creado",
      policyCreated: "Política creada",
      contractCreated: "Contrato creado",
      policyDraftIncomplete: "Revisa nombre, acciones permitidas y cláusulas antes de crear la política",
      policyProfileLabel: "Perfil de política",
      policyClausesLabel: "Cláusulas propuestas",
      flowStatusStart: "Empieza pegando una URL válida del recurso para encadenar el análisis completo.",
      flowStatusDocument: "El documento ya está analizado; revisa y ajusta los metadatos del asset.",
      flowStatusMetadata: "Los metadatos del asset ya están listos; ahora revisa la política sugerida.",
      flowStatusPolicy: "La política ya está propuesta; puedes revisar ambos formularios antes de crear.",
      flowStatusReady: "Todo está preparado: ya puedes crear el asset y la política con revisión final."
      ,
      traceTitle: "Trazabilidad de transferencia",
      traceDescription: "Evidencia técnica paso a paso del flujo de espacio de datos (IDs, token enmascarado, negociación, EDR y descarga).",
      traceStep: "Paso",
      traceState: "Estado",
      traceData: "Datos",
      traceNoRows: "Aún no hay eventos de transferencia",
      traceClear: "Limpiar trazas",
      traceReady: "Panel de trazabilidad listo",
      participantAuditTitle: "Transacciones auditadas",
      participantAuditDescription: "Trazas auditadas de este participante: qué se pidió, quién lo pidió, qué se decidió y con qué firma.",
      participantAuditReload: "Recargar auditoría",
      participantAuditTrace: "Trace ID",
      participantAuditEvent: "Evento",
      participantAuditAsset: "Asset / recurso",
      participantAuditConsume: "Consume",
      participantAuditProvide: "Provee",
      participantAuditTime: "Hora",
      participantAuditLoading: "Cargando transacciones auditadas...",
      participantAuditLoaded: "Transacciones auditadas actualizadas",
      participantAuditNoRows: "Aún no hay transacciones auditadas para este participante",
      participantAuditError: "No se pudo cargar la auditoría del participante",
      participantAuditRegistered: "Registrado",
      participantAuditUnregistered: "Sin registro",
      participantAuditSigned: "Firmado",
      participantAuditUnsigned: "Sin firma",
      participantAuditTraceRef: "Traza",
      participantAuditSigner: "Firmante",
      participantAuditPending: "Pendiente",
      participantAuditNotApplicable: "Sin revisión documental para este evento",
      participantAuditAwaitingDownload: "La revisión documental se mostrará al completarse la descarga",
      participantAuditUnavailable: "No disponible",
      participantAuditReportUnavailable: "Informe no disponible",
      participantAuditNoReport: "Sin informe",
      traceAuthStarted: "Autenticación iniciada",
      traceAuthCompleted: "Autenticación completada",
      traceTokenRefreshed: "Token refrescado",
      traceNegotiationStarted: "Negociación iniciada",
      traceNegotiationConsumerRequested: "Solicitud registrada en consumidor",
      traceNegotiationProviderRequested: "Solicitud enviada al proveedor",
      traceNegotiationCompleted: "Negociación completada",
      traceEdrLookup: "Consulta EDR/transfer process",
      traceDownloadStarted: "Descarga iniciada",
      traceDownloadCompleted: "Descarga completada",
      traceStepError: "Error en paso"
    },
    en: {
      missingToken: "Missing Keycloak access token",
      keycloakUnavailable: "Keycloak JS unavailable",
      keycloakImportError: "Keycloak JS unavailable",
      keycloakAuthFailed: "Keycloak authentication failed",
      refreshFailed: "Failed to refresh token",
      tableId: "ID",
      tableName: "Name",
      tableDescription: "Description",
      tableLicense: "License",
      tableAssetDescription: "Description",
      tablePolicy: "Policy",
      tableContract: "Contract",
      tableAsset: "Asset",
      tableConsumer: "Consumer",
      tableProvider: "Provider",
      tableStatus: "Status",
      tableDownload: "Download",
      tableAction: "Action",
      tableMetadata: "Metadata",
      pending: "Pending",
      notAvailable: "Unavailable",
      download: "Download",
      ownAsset: "Own asset",
      negotiate: "Accept",
      acceptPolicy: "Accept",
      policyClausesUnavailable: "The provider policy will be accepted as published.",
      policyDetailsInternal: "Internal use",
      policyDetailsAi: "AI usage",
      policyDetailsRedistribution: "Redistribution",
      policyDetailsPermitted: "Permitted",
      policyDetailsProhibited: "Prohibited",
      policyDetailsDuties: "Duties",
      incompleteNegotiationData: "Incomplete negotiation data",
      ownAssetNegotiationDenied: "Own assets cannot be negotiated",
      providerNotConfigured: "Provider not configured",
      negotiationCompleted: "Negotiation completed for asset",
      negotiationError: "Negotiation error",
      downloadStarted: "Download started",
      downloadError: "Download error",
      dashboardOpened: "Dashboard opened",
      dashboardOpenError: "Error opening dashboard",
      catalogsLoaded: "Catalogs loaded",
      federatedReloaded: "Federated catalog reloaded",
      governanceCatalogUnavailable: "Governance federated catalog unavailable; using local Fuseki",
      governanceRemoteReadOnly: "Visible in the data space catalogue",
      governanceNegotiationCompleted: "Federated negotiation completed",
      governanceNegotiationError: "Federated negotiation error",
      negotiationStarting: "Starting negotiation",
      governanceNegotiationStarting: "Starting federated negotiation",
      openAsset: "Open asset",
      auditPublished: "Audit event published",
      auditPublishError: "Audit event could not be published",
      assetMetadataIncomplete: "Review name and description before creating the asset",
      assetMetadataValidating: "Validating DCAT-AP metadata...",
      assetMetadataValidationPassed: "DCAT-AP validation passed",
      assetMetadataValidationFailed: "DCAT-AP validation failed",
      assetMetadataValidationLabel: "DCAT-AP validation",
      assetMetadataValidationScore: "Score",
      assetMetadataValidationMissing: "Required fields pending",
      assetMetadataValidationWarnings: "Warnings",
      assetMetadataValidationRecommendations: "Recommendations",
      assetCreated: "Asset created",
      policyCreated: "Policy created",
      contractCreated: "Contract created",
      policyDraftIncomplete: "Review the name, permitted actions and clauses before creating the policy",
      policyProfileLabel: "Policy profile",
      policyClausesLabel: "Suggested clauses",
      flowStatusStart: "Start by pasting a valid resource URL to chain the full analysis.",
      flowStatusDocument: "The document is already analyzed; now review and adjust the asset metadata.",
      flowStatusMetadata: "The asset metadata is ready; now review the suggested policy.",
      flowStatusPolicy: "The policy is already proposed; you can review both forms before creating them.",
      flowStatusReady: "Everything is ready: you can now create the asset and the policy after a final review."
      ,
      traceTitle: "Transfer traceability",
      traceDescription: "Step-by-step technical evidence of the data space flow (IDs, masked token, negotiation, EDR and download).",
      traceStep: "Step",
      traceState: "State",
      traceData: "Data",
      traceNoRows: "No transfer events yet",
      traceClear: "Clear trace",
      traceReady: "Trace panel ready",
      participantAuditTitle: "Audited transactions",
      participantAuditDescription: "Audited traces for this participant: what was asked, who asked, what was decided and under whose signature.",
      participantAuditReload: "Reload audit",
      participantAuditTrace: "Trace ID",
      participantAuditEvent: "Event",
      participantAuditAsset: "Asset / resource",
      participantAuditConsume: "Consume",
      participantAuditProvide: "Provide",
      participantAuditTime: "Time",
      participantAuditLoading: "Loading audited transactions...",
      participantAuditLoaded: "Audited transactions updated",
      participantAuditNoRows: "No audited transactions yet for this participant",
      participantAuditError: "Failed to load participant audit",
      participantAuditRegistered: "Registered",
      participantAuditUnregistered: "Unregistered",
      participantAuditSigned: "Signed",
      participantAuditUnsigned: "Unsigned",
      participantAuditTraceRef: "Trace",
      participantAuditSigner: "Signer",
      participantAuditPending: "Pending",
      participantAuditNotApplicable: "No document review for this event",
      participantAuditAwaitingDownload: "Document review will appear once the download completes",
      participantAuditUnavailable: "Unavailable",
      participantAuditReportUnavailable: "Report unavailable",
      participantAuditNoReport: "No report",
      traceAuthStarted: "Authentication started",
      traceAuthCompleted: "Authentication completed",
      traceTokenRefreshed: "Token refreshed",
      traceNegotiationStarted: "Negotiation started",
      traceNegotiationConsumerRequested: "Request registered at consumer",
      traceNegotiationProviderRequested: "Request sent to provider",
      traceNegotiationCompleted: "Negotiation completed",
      traceEdrLookup: "EDR/transfer process lookup",
      traceDownloadStarted: "Download started",
      traceDownloadCompleted: "Download completed",
      traceStepError: "Step error"
    }
  }[lang];

  const features = {
    create: true,
    myAssets: true,
    federated: true,
    allowNegotiate: true,
    allowDownload: true,
    ...(cfg.features || {})
  };

  const state = {
    assets: [],
    policies: [],
    contracts: [],
    negotiations: [],
    federated: [],
    localPolicyMap: new Map(),
    negotiatedFederatedKeys: new Set(),
    pendingNegotiationKeys: new Set(),
    accessToken: "",
    transferTrace: [],
    participantAuditLoaded: false,
    assetDraftUpload: null,
    assetMetadataValidation: null,
    policyDraftReport: null,
  };

  function persistentNegotiationStorageKey() {
    return `mydataspace.negotiatedAssets.${cfg.id}`;
  }

  function persistedNegotiationKey(providerDataspaceId, providerConnectorId, assetId) {
    return [
      String(providerDataspaceId || "").trim(),
      String(providerConnectorId || "").trim(),
      String(assetId || "").trim()
    ].join("|");
  }

  function persistedNegotiationAssetKey(assetId) {
    return [`asset`, String(assetId || "").trim()].join("|");
  }

  function addNegotiationPersistenceAliases(providerDataspaceId, providerConnectorId, assetId) {
    const dataspaceId = String(providerDataspaceId || "").trim();
    const connectorId = String(providerConnectorId || "").trim();
    const namespacedConnectorId = dataspaceId && connectorId && connectorId.indexOf(`${dataspaceId}:`) !== 0
      ? `${dataspaceId}:${connectorId}`
      : connectorId;
    state.negotiatedFederatedKeys.add(persistedNegotiationKey(dataspaceId, connectorId, assetId));
    if (namespacedConnectorId && namespacedConnectorId !== connectorId) {
      state.negotiatedFederatedKeys.add(persistedNegotiationKey(dataspaceId, namespacedConnectorId, assetId));
    }
    state.negotiatedFederatedKeys.add(persistedNegotiationAssetKey(assetId));
  }

  function loadPersistedNegotiations() {
    try {
      const raw = window.localStorage.getItem(persistentNegotiationStorageKey());
      const items = raw ? JSON.parse(raw) : [];
      state.negotiatedFederatedKeys = new Set(Array.isArray(items) ? items : []);
    } catch (_err) {
      state.negotiatedFederatedKeys = new Set();
    }
  }

  function savePersistedNegotiations() {
    try {
      window.localStorage.setItem(
        persistentNegotiationStorageKey(),
        JSON.stringify(Array.from(state.negotiatedFederatedKeys))
      );
    } catch (_err) {
      // ignore local storage failures
    }
  }

  // Las pestañas se leen del DOM en vez de estar escritas aquí.
  //
  // Antes eran exactamente dos, «proveedor» y «consumo», con sus dos botones y
  // sus dos paneles nombrados uno a uno; añadir la de nodos conocidos obligaba
  // a tocar esta función. Ahora cada botón declara el panel que controla con
  // aria-controls, que es lo que ya tenía que decir de todas formas.
  function initOperationTabs() {
    const tabNav = byId("operationTabNav");
    if (!tabNav) return;

    const buttons = Array.from(tabNav.querySelectorAll("[role='tab']"));
    const visibleFor = {
      operationProviderPanel: Boolean(features.create || features.myAssets),
      operationConsumerPanel: Boolean(features.federated || features.allowNegotiate),
      // Fuera de esta entrega, con su código intacto.
      //
      // El panel sigue en la página y todo lo que hay detrás -- alta de nodos
      // conocidos, «actualizar ahora», la lista con su última sincronización --
      // sigue escrito y probado. Lo único que cambia es que no se ofrece.
      // Volver a ponerla es cambiar este `false` por `true`; nada más depende
      // de esta línea.
      //
      // Lo que sí desaparece con ella: la única forma desde la interfaz de dar
      // de alta otro nodo. La federación periódica sigue corriendo con los
      // nodos que ya estén dados de alta, y `POST /api/v1/nodes` y
      // `POST /api/v1/nodes/sync` siguen ahí.
      operationNodesPanel: false,
      // Nace oculta. Solo quien administra el nodo tiene algo que hacer en
      // ella, y eso no se sabe hasta que hay token: la ensena
      // console-solicitudes.js llamando a __ODS_MOSTRAR_PESTANA.
      operationRequestsPanel: false
    };

    const tabs = buttons
      .map((button) => ({
        button,
        panel: byId(button.getAttribute("aria-controls") || ""),
        visible: visibleFor[button.getAttribute("aria-controls")] !== false
      }))
      .filter((tab) => tab.panel);

    const show = (node, visible) => {
      if (!node) return;
      node.hidden = !visible;
      node.classList.toggle("hidden", !visible);
    };

    tabs.forEach((tab) => show(tab.button, tab.visible));
    const disponibles = tabs.filter((tab) => tab.visible);
    // Con una sola pestaña visible no hay nada que elegir, y una barra de
    // pestañas con un único botón sólo estorba.
    show(tabNav, disponibles.length > 1);

    const setActive = (activa) => {
      tabs.forEach((tab) => {
        const esta = tab === activa && tab.visible;
        tab.button.classList.toggle("is-active", esta);
        tab.button.setAttribute("aria-selected", esta ? "true" : "false");
        tab.panel.classList.toggle("is-active", esta);
        tab.panel.hidden = !esta;
      });
    };

    disponibles.forEach((tab) => tab.button.addEventListener("click", () => setActive(tab)));
    if (disponibles.length) setActive(disponibles[0]);

    // Una pestaña puede aparecer despues, cuando algo que no se sabia al
    // pintar -- los grupos del token -- resulta cierto. Se le da su botón y su
    // manejador aquí y no en el módulo que la pide, para que el cambio de
    // panel siga viviendo en un solo sitio.
    window.__ODS_MOSTRAR_PESTANA = (panelId) => {
      const tab = tabs.find((item) => item.panel && item.panel.id === panelId);
      if (!tab || tab.visible) return false;
      tab.visible = true;
      show(tab.button, true);
      show(tabNav, tabs.filter((item) => item.visible).length > 1);
      tab.button.addEventListener("click", () => setActive(tab));
      return true;
    };
  }

  // --- Nodos conocidos ---------------------------------------------------
  //
  // Es la pantalla que convierte esto en un espacio de datos: se añade la
  // dirección de otro nodo y su oferta entra en el catálogo consolidado.
  function initKnownNodes() {
    const panel = byId("operationNodesPanel");
    if (!panel) return;

    const tabla = byId("nodesTable");
    const estado = byId("nodesStatus");
    const labelInput = byId("nodeLabel");
    const urlInput = byId("nodeBaseUrl");

    const decir = (texto, esError) => {
      if (!estado) return;
      estado.textContent = texto;
      estado.classList.toggle("error", Boolean(esError));
    };

    const fecha = (valor) => {
      if (!valor) return lang === "en" ? "never" : "nunca";
      try {
        return new Date(valor).toLocaleString();
      } catch (_err) {
        return valor;
      }
    };

    const etiquetaEstado = (nodo) => {
      if (nodo.status === "unreachable") {
        return lang === "en" ? "unavailable" : "no disponible";
      }
      if (nodo.status === "pending") {
        return lang === "en" ? "not synced yet" : "sin sincronizar";
      }
      return lang === "en" ? "up" : "disponible";
    };

    async function pintar() {
      let items = [];
      try {
        const respuesta = await fetch("/api/v1/nodes", { headers: { Accept: "application/json" } });
        items = (await respuesta.json()).items || [];
      } catch (err) {
        decir(lang === "en" ? "Could not read the node list." : "No se pudo leer la lista de nodos.", true);
        return;
      }
      if (!tabla) return;
      const cabecera = lang === "en"
        ? ["Node", "Address", "State", "Last successful sync", ""]
        : ["Nodo", "Dirección", "Estado", "Última sincronización correcta", ""];
      const filas = items.map((nodo) => {
        const propio = nodo.local
          ? `<span class="muted">${escapeHtml(lang === "en" ? "this node" : "este nodo")}</span>`
          : `<button class="secondary" data-remove-node="${escapeHtml(nodo.id)}">${escapeHtml(lang === "en" ? "Remove" : "Retirar")}</button>`;
        return `<tr>
          <td><strong>${escapeHtml(nodo.label || nodo.id)}</strong><br><span class="muted">${escapeHtml(nodo.id)}</span></td>
          <td>${escapeHtml(nodo.baseUrl || "")}</td>
          <td>${escapeHtml(etiquetaEstado(nodo))}</td>
          <td>${escapeHtml(fecha(nodo.lastSyncAt))}</td>
          <td>${propio}</td>
        </tr>`;
      });
      tabla.innerHTML =
        `<thead><tr>${cabecera.map((c) => `<th>${escapeHtml(c)}</th>`).join("")}</tr></thead>` +
        `<tbody>${filas.join("")}</tbody>`;

      tabla.querySelectorAll("[data-remove-node]").forEach((boton) => {
        boton.addEventListener("click", () => retirar(boton.getAttribute("data-remove-node")));
      });
    }

    async function conIdentidad(url, opciones) {
      const token = await ensureAccessToken();
      if (!token) {
        throw new Error(lang === "en" ? "sign in first" : "hay que iniciar sesión");
      }
      return fetch(url, {
        ...opciones,
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          Authorization: `Bearer ${token}`,
          ...(opciones && opciones.headers)
        }
      });
    }

    async function anadir() {
      const label = String(labelInput?.value || "").trim();
      const baseUrl = String(urlInput?.value || "").trim();
      if (!baseUrl) {
        decir(lang === "en" ? "The address is required." : "Hace falta la dirección.", true);
        return;
      }
      decir(lang === "en" ? "Adding…" : "Añadiendo…");
      try {
        const respuesta = await conIdentidad("/api/v1/nodes", {
          method: "POST",
          body: JSON.stringify({ label, baseUrl })
        });
        const cuerpo = await respuesta.json();
        if (!respuesta.ok) {
          // El servicio contesta con un motivo concreto; enseñarlo tal cual es
          // más útil que un «no se pudo añadir» que no dice si la dirección
          // está mal, si el nodo ya estaba o si falta identidad.
          decir(motivo(cuerpo.error), true);
          return;
        }
        if (labelInput) labelInput.value = "";
        if (urlInput) urlInput.value = "";
        decir(lang === "en"
          ? "Node added. Its offer appears after the next sync."
          : "Nodo añadido. Su oferta aparece tras la próxima sincronización.");
        await pintar();
      } catch (err) {
        decir(String(err.message || err), true);
      }
    }

    function motivo(codigo) {
      const textos = {
        missing_base_url: lang === "en" ? "The address is required." : "Hace falta la dirección.",
        invalid_base_url: lang === "en" ? "That is not an http(s) address." : "Eso no es una dirección http(s).",
        invalid_node_id: lang === "en" ? "That name cannot be used as an identifier." : "Ese nombre no sirve como identificador.",
        node_is_local: lang === "en" ? "That is this node." : "Ese es este mismo nodo.",
        node_already_known: lang === "en" ? "That node is already on the list." : "Ese nodo ya está en la lista.",
        cannot_remove_local_node: lang === "en" ? "This node cannot be removed." : "Este nodo no se puede retirar.",
        forbidden: lang === "en" ? "You need administrator rights." : "Hace falta ser administrador."
      };
      return textos[codigo] || String(codigo || (lang === "en" ? "unknown error" : "error desconocido"));
    }

    async function retirar(id) {
      if (!id) return;
      decir(lang === "en" ? "Removing…" : "Retirando…");
      try {
        const respuesta = await conIdentidad(`/api/v1/nodes/${encodeURIComponent(id)}`, { method: "DELETE" });
        if (!respuesta.ok) {
          decir(motivo((await respuesta.json()).error), true);
          return;
        }
        decir(lang === "en" ? "Node removed, along with its graph." : "Nodo retirado, y su grafo con él.");
        await pintar();
      } catch (err) {
        decir(String(err.message || err), true);
      }
    }

    async function actualizarAhora() {
      decir(lang === "en" ? "Syncing…" : "Sincronizando…");
      try {
        const respuesta = await conIdentidad("/api/v1/nodes/sync", { method: "POST" });
        const cuerpo = await respuesta.json();
        if (!respuesta.ok || cuerpo.ok === false) {
          decir(motivo(cuerpo.error || cuerpo.detail), true);
          return;
        }
        decir(cuerpo.summary || (lang === "en" ? "Sync finished." : "Sincronización terminada."));
        await pintar();
      } catch (err) {
        decir(String(err.message || err), true);
      }
    }

    byId("addNodeBtn")?.addEventListener("click", anadir);
    byId("syncNodesBtn")?.addEventListener("click", actualizarAhora);
    pintar();
  }

  // El conector que la instalación declara, frente a uno creado por un alta.
  //
  // Se comprobaba con /^connector-[123]$/, los tres identificadores del
  // despliegue de origen: en cualquier otra instalación esa expresión no casa
  // con nada y la consola filtraba por dueño recursos que son de todo el nodo.



  function localNegotiationKey(providerConnectorId, assetId) {
    return [String(providerConnectorId || "").trim(), String(assetId || "").trim()].join("|");
  }

  function federatedNegotiationKey(providerDataspaceId, providerConnectorId, assetId) {
    return [
      String(providerDataspaceId || "").trim(),
      String(providerConnectorId || "").trim(),
      String(assetId || "").trim()
    ].join("|");
  }


  function isSameDataspaceAsset(row, currentDataspaceId) {
    const providerDataspaceId = String(row && row.providerDataspaceId || "").trim();
    const currentId = String(currentDataspaceId || "").trim();
    return !providerDataspaceId || !currentId || providerDataspaceId === currentId;
  }




  function appendDashboardVersion(url) {
    const value = String(url || "").trim();
    if (!value) return "";
    try {
      const parsed = new URL(value, window.location.origin);
      if (/\/urban-dashboard\.html$/i.test(parsed.pathname)) {
        parsed.pathname = parsed.pathname.replace(/\/urban-dashboard\.html$/i, "/urban-dashboard-v2.html");
      }
      parsed.searchParams.set("uiVersion", DASHBOARD_UI_VERSION);
      return parsed.toString();
    } catch (_err) {
      return value;
    }
  }


  function buildDashboardViewerUrl(row) {
    const explicit = String((row && row.viewerUrl) || "").trim();
    if (explicit) return appendDashboardVersion(explicit);
    const params = new URLSearchParams();
    if (row && row.assetId) params.set("assetId", row.assetId);
    if (row && row.assetName) params.set("title", row.assetName);
    if (row && row.baseUrl) params.set("dataUrl", row.baseUrl);
    if (row && row.topicCode) params.set("topic", row.topicCode);
    if (row && row.dashboardUnit) params.set("unit", row.dashboardUnit);
    params.set("uiVersion", DASHBOARD_UI_VERSION);
    return `${resolveDashboardBaseUrl(row)}?${params.toString()}`;
  }

  function buildUrbanCommandCenterUrl() {
    const publicBaseUrl = String((window.DATASPACE_RUNTIME_CONFIG && window.DATASPACE_RUNTIME_CONFIG.publicBaseUrl) || window.location.origin || "").trim();
    return appendDashboardVersion(`${publicBaseUrl.replace(/\/$/, "")}/urban-dashboard-v2.html`);
  }

  const byId = (id) => document.getElementById(id);
  const statusEl = byId("status");

  function setStatus(msg, isError = false) {
    statusEl.textContent = msg;
    statusEl.style.color = isError ? "#9b2226" : "#2d6a4f";
  }



  // Una etiqueta que dice "Validando..." y no se mueve durante dos minutos se
  // lee como una pagina colgada, asi que la espera se cuenta a si misma.
  async function whileWaiting(setter, label, work) {
    const startedAt = Date.now();
    setter(label);
    const tick = window.setInterval(function () {
      const seconds = Math.round((Date.now() - startedAt) / 1000);
      setter(label + " (" + seconds + " s)");
    }, 1000);
    try {
      return await work();
    } finally {
      window.clearInterval(tick);
    }
  }





  function normalizeFileName(value, fallback = "download.bin") {
    const raw = (value || "").trim();
    if (!raw) return fallback;
    return raw.replace(/[\\/:*?"<>|]+/g, "_");
  }

  function maskToken(token) {
    const raw = String(token || "");
    if (!raw) return "";
    if (raw.length <= 24) return `${raw.slice(0, 8)}...`;
    return `${raw.slice(0, 12)}...${raw.slice(-10)}`;
  }

  function parseJwtPayload(token) {
    try {
      const parts = String(token || "").split(".");
      if (parts.length < 2) return {};
      const normalized = parts[1].replace(/-/g, "+").replace(/_/g, "/");
      const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=");
      const json = atob(padded);
      return JSON.parse(json);
    } catch (_err) {
      return {};
    }
  }

  function isUsableJwt(token) {
    const raw = String(token || "").trim();
    if (!raw || raw.split(".").length !== 3) return false;
    const payload = parseJwtPayload(raw);
    if (!payload || !payload.exp) return false;
    return Number(payload.exp) > Math.floor(Date.now() / 1000) + 10;
  }

  function rememberAccessToken(token) {
    state.accessToken = String(token || "").trim();
    window.__DATASPACE_ACCESS_TOKEN = state.accessToken;
    return state.accessToken;
  }

  function prettyData(data) {
    if (data == null) return "";
    if (typeof data === "string") return data;
    try {
      return JSON.stringify(data, null, 2);
    } catch (_err) {
      return String(data);
    }
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  const legalClassificationLabels = {
    "open-public-sector-reuse": {
      es: "Reutilización abierta con trazabilidad reforzada",
      en: "Open reuse with enhanced traceability"
    },
    "controlled-governed-reuse": {
      es: "Reutilización gobernada con condiciones contractuales",
      en: "Governed reuse with contractual conditions"
    },
    "restricted-personal-data-review": {
      es: "Datos personales sin anonimizar o con revisión jurídica",
      en: "Personal data requiring legal review"
    },
    "restricted-sensitive-data-review": {
      es: "Dato sensible o categoría especial: revisión reforzada",
      en: "Sensitive or special-category data: enhanced review"
    },
    "missing-legal-basis-review": {
      es: "Base jurídica o licencia insuficiente",
      en: "Insufficient legal basis or licence"
    }
  };

  const legalReasoningCatalog = {
    no_extractable_text: {
      es: {
        title: "Sin texto extraíble",
        detail: "El documento no expone texto procesable en esta fase y requiere revisión manual."
      },
      en: {
        title: "No extractable text",
        detail: "The document does not expose processable text in this phase and requires manual review."
      }
    },
    special_category_data: {
      es: {
        title: "Dato sensible detectado",
        detail: "Se han detectado indicios de categorías especiales de datos; conviene detener la reutilización automática."
      },
      en: {
        title: "Sensitive data detected",
        detail: "Signals of special-category data were detected; automatic reuse should be halted."
      }
    },
    personal_data_indicators: {
      es: {
        title: "Datos personales sin anonimizar",
        detail: "Hay indicios de datos personales y se requiere base jurídica, minimización y control de retención."
      },
      en: {
        title: "Personal data indicators",
        detail: "There are signs of personal data and lawful basis, minimisation and retention control are required."
      }
    },
    missing_licence_or_contract_basis: {
      es: {
        title: "Licencia o contrato insuficiente",
        detail: "No se detecta una base clara de licencia o contrato para reutilización entre espacios."
      },
      en: {
        title: "Missing licence or contract basis",
        detail: "No clear licence or contract basis for cross-dataspace reuse was detected."
      }
    },
    licence_detected: {
      es: {
        title: "Licencia detectada",
        detail: "El activo contiene referencias de licencia o reutilización que facilitan su compartición gobernada."
      },
      en: {
        title: "Licence detected",
        detail: "The asset contains licence or reuse references that support governed sharing."
      }
    },
    public_sector_context: {
      es: {
        title: "Contexto de sector público",
        detail: "El contenido encaja con marcos de reutilización, control y auditoría del sector público."
      },
      en: {
        title: "Public sector context",
        detail: "The content aligns with public-sector reuse, control and audit frameworks."
      }
    },
    interoperability_and_governance: {
      es: {
        title: "Interoperabilidad y gobernanza",
        detail: "Se observan señales que favorecen trazabilidad, catálogo y compartición gobernada."
      },
      en: {
        title: "Interoperability and governance",
        detail: "Signals that support traceability, cataloguing and governed sharing are present."
      }
    },
    gdprRgpd: {
      es: {
        title: "Alineado con RGPD/GDPR",
        detail: "El contenido contiene referencias compatibles con obligaciones de protección de datos."
      },
      en: {
        title: "Aligned with GDPR",
        detail: "The content contains references compatible with data protection obligations."
      }
    },
    dataGovernanceAct: {
      es: {
        title: "Alineado con Data Governance Act",
        detail: "El documento contiene señales compatibles con intermediación, gobernanza o altruismo de datos."
      },
      en: {
        title: "Aligned with Data Governance Act",
        detail: "The document contains signals compatible with data intermediation, governance or altruism."
      }
    },
    dataAct: {
      es: {
        title: "Alineado con Data Act",
        detail: "El documento contiene referencias relacionadas con acceso, portabilidad o compartición de datos."
      },
      en: {
        title: "Aligned with Data Act",
        detail: "The document contains references related to data access, portability or sharing."
      }
    },
    omnibusLaw: {
      es: {
        title: "Alineado con Ley Ómnibus",
        detail: "El contenido contiene señales compatibles con simplificación administrativa."
      },
      en: {
        title: "Aligned with Omnibus Law",
        detail: "The content contains signals compatible with administrative simplification."
      }
    }
  };

  const recommendationCatalog = {
    "Manual review required because the document does not expose extractable text in this CPU-safe phase.": {
      es: "Revisar manualmente el documento porque no expone texto extraíble en esta fase.",
      en: "Review the document manually because it does not expose extractable text in this phase."
    },
    "Escalate the transfer to manual legal review before enabling downstream AI reuse.": {
      es: "Escalar la transferencia a revisión jurídica manual antes de permitir reutilización aguas abajo.",
      en: "Escalate the transfer to manual legal review before enabling downstream reuse."
    },
    "Record the lawful basis and retention policy for any personal data before transfer.": {
      es: "Registrar la base jurídica y la política de retención antes de transferir datos personales.",
      en: "Record the lawful basis and retention policy before transferring personal data."
    },
    "Attach an explicit licence or contract clause before reuse across data spaces.": {
      es: "Añadir una licencia explícita o cláusula contractual antes de reutilizar entre espacios de datos.",
      en: "Attach an explicit licence or contract clause before reuse across data spaces."
    },
    "Improve metadata and interoperability descriptors before scaling the reuse scenario.": {
      es: "Mejorar los metadatos y los descriptores de interoperabilidad antes de escalar la reutilización.",
      en: "Improve metadata and interoperability descriptors before scaling reuse."
    },
    "Keep the governance trace linked to sector-public reuse obligations and audit evidence.": {
      es: "Mantener la traza de gobernanza vinculada a obligaciones de reutilización del sector público y a la evidencia auditada.",
      en: "Keep the governance trace linked to public-sector reuse obligations and audit evidence."
    },
    "Transfer can proceed with standard signed evidence and governance traceability.": {
      es: "La transferencia puede continuar con evidencia firmada estándar y trazabilidad de gobernanza.",
      en: "The transfer can proceed with standard signed evidence and governance traceability."
    },
    "Verify and record the source terms of reuse, but do not treat the asset as personal or sensitive data solely because the licence is implicit.": {
      es: "Verificar y registrar los términos de reutilización del origen, pero sin tratar el activo como dato personal o sensible solo porque la licencia no venga explícita.",
      en: "Verify and record the source terms of reuse, but do not treat the asset as personal or sensitive data solely because the licence is implicit."
    },
    "Document the anonymization or aggregation method and keep evidence that re-identification risk has been assessed.": {
      es: "Documentar el método de anonimización o agregación y conservar evidencia de que se ha evaluado el riesgo de reidentificación.",
      en: "Document the anonymization or aggregation method and keep evidence that re-identification risk has been assessed."
    }
  };

  const policyValueCatalog = {
    use: { es: "usar", en: "use" },
    read: { es: "leer", en: "read" },
    reproduce: { es: "reproducir", en: "reproduce" },
    query: { es: "consultar", en: "query" },
    integrate: { es: "integrar", en: "integrate" },
    "cache-temporarily": { es: "cache temporal", en: "cache temporarily" },
    distribute: { es: "distribuir", en: "distribute" },
    share: { es: "compartir", en: "share" },
    "derive-aggregates": { es: "generar agregados", en: "derive aggregates" },
    "export-internal-copy": { es: "exportar copia interna", en: "export internal copy" },
    quote: { es: "citar", en: "quote" },
    summarize: { es: "resumir", en: "summarize" },
    index: { es: "indexar", en: "index" },
    "catalog-reference": { es: "referenciar catálogo", en: "catalog reference" },
    sell: { es: "vender", en: "sell" },
    "bypass-rate-limits": { es: "eludir límites de tasa", en: "bypass rate limits" },
    "disrupt-service": { es: "interrumpir servicio", en: "disrupt service" },
    "misrepresent-publisher": { es: "falsear el editor", en: "misrepresent publisher" },
    reidentify: { es: "reidentificar", en: "reidentify" },
    "share-raw-personal-data": { es: "compartir datos personales en bruto", en: "share raw personal data" },
    "train-ai": { es: "entrenar IA", en: "train AI" },
    redistribute: { es: "redistribuir", en: "redistribute" },
    "remove-attribution": { es: "eliminar atribución", en: "remove attribution" },
    attribution: { es: "atribución", en: "attribution" },
    "keep-source-link": { es: "mantener enlace al origen", en: "keep source link" },
    "respect-rate-limits": { es: "respetar límites de tasa", en: "respect rate limits" },
    "preserve-source-timestamp": { es: "preservar marca temporal del origen", en: "preserve source timestamp" },
    "preserve-column-metadata": { es: "preservar metadatos de columnas", en: "preserve column metadata" },
    "document-transformations": { es: "documentar transformaciones", en: "document transformations" },
    "preserve-catalog-identifiers": { es: "preservar identificadores de catálogo", en: "preserve catalog identifiers" },
    "link-to-distribution": { es: "enlazar a la distribución", en: "link to distribution" },
    "preserve-context-of-excerpts": { es: "preservar contexto de extractos", en: "preserve context of excerpts" },
    "document-anonymization-method": { es: "documentar método de anonimización", en: "document anonymization method" },
    "reidentification-risk-check": { es: "verificar riesgo de reidentificación", en: "reidentification risk check" },
    "contract-reference": { es: "referencia contractual", en: "contract reference" },
    "lawful-basis-record": { es: "registrar base jurídica", en: "lawful basis record" },
    "retention-control": { es: "control de retención", en: "retention control" },
    "manual-legal-review": { es: "revisión jurídica manual", en: "manual legal review" },
    "incident-notification": { es: "notificación de incidentes", en: "incident notification" },
    "attach-licence-or-contract-basis": { es: "adjuntar licencia o base contractual", en: "attach licence or contract basis" },
    allowed: { es: "permitido", en: "allowed" },
    "allowed-with-review": { es: "permitido con revisión", en: "allowed with review" },
    "allowed-with-traceability": { es: "permitido con trazabilidad", en: "allowed with traceability" },
    "review-required": { es: "requiere revisión", en: "review required" },
    prohibited: { es: "prohibido", en: "prohibited" },
    "contract-only": { es: "solo con contrato", en: "contract only" },
    "link-or-contract-only": { es: "solo enlace o contrato", en: "link or contract only" },
    "allowed-with-attribution": { es: "permitido con atribución", en: "allowed with attribution" },
    "aggregates-only-with-contract": { es: "solo agregados con contrato", en: "aggregates only with contract" },
    "aggregates-only-with-attribution": { es: "solo agregados con atribución", en: "aggregates only with attribution" },
    "already-claimed-check-evidence": { es: "declarada; verificar evidencia", en: "claimed already; check evidence" },
    required: { es: "requerida", en: "required" },
    "not-required": { es: "no requerida", en: "not required" },
    "source-link-and-publisher": { es: "enlace al origen y editor", en: "source link and publisher" },
    "required-for-derived-material": { es: "obligatoria en materiales derivados", en: "required for derived material" },
    mandatory: { es: "obligatorio", en: "mandatory" },
    "not-applicable": { es: "no aplica", en: "not applicable" },
    "not-declared": { es: "sin requisito declarado", en: "no declared requirement" },
    "snapshot-or-versioned-release": { es: "instantánea o versión publicada", en: "snapshot or versioned release" },
    "dynamic-api-check-source-before-reuse": { es: "API dinámica; comprobar origen antes de reutilizar", en: "dynamic API; check source before reuse" },
    "check-publication-date-before-republication": { es: "comprobar fecha de publicación antes de republicar", en: "check publication date before republication" },
    "refresh-catalog-metadata-periodically": { es: "refrescar metadatos de catálogo periódicamente", en: "refresh catalog metadata periodically" },
    "static-document-version": { es: "versión documental estática", en: "static document version" }
  };

  function getLocalizedClassification(report) {
    const key = report?.legalClassification?.key || "";
    const labels = legalClassificationLabels[key] || null;
    if (labels) return labels[lang] || labels.en;
    return report?.legalClassification?.label || report?.decision || report?.documentType || t.notAvailable;
  }

  function localizeDecision(value) {
    const map = {
      allow: { es: "Verde: todo correcto", en: "Green: all clear" },
      "allow-with-warning": { es: "Ámbar: reutilización con advertencias", en: "Amber: reuse with warnings" },
      "manual-review": { es: "Rojo: revisión manual obligatoria", en: "Red: manual review required" }
    };
    const entry = map[String(value || "").trim()];
    return entry ? entry[lang] : (value || t.notAvailable);
  }

  function localizeRisk(value) {
    const map = {
      low: { es: "Bajo", en: "Low" },
      medium: { es: "Medio", en: "Medium" },
      high: { es: "Alto", en: "High" }
    };
    const entry = map[String(value || "").trim().toLowerCase()];
    return entry ? entry[lang] : (value || t.notAvailable);
  }

  function localizeReasonItem(item) {
    const code = item?.code || "";
    const catalog = legalReasoningCatalog[code];
    const localized = catalog ? catalog[lang] || catalog.en : null;
    return {
      severity: item?.severity || "low",
      title: localized?.title || item?.title || "",
      detail: localized?.detail || item?.detail || "",
      evidence: Array.isArray(item?.evidence) ? item.evidence : []
    };
  }

  function localizeRecommendations(items) {
    return (Array.isArray(items) ? items : []).map((item) => {
      const key = String(item || "").trim();
      const localized = recommendationCatalog[key];
      return localized ? (localized[lang] || localized.en) : key;
    });
  }

  function localizePolicyValue(value) {
    const key = String(value || "").trim();
    const localized = policyValueCatalog[key];
    return localized ? (localized[lang] || localized.en || key) : key;
  }

  function localizePolicyList(items) {
    return (Array.isArray(items) ? items : []).map((item) => localizePolicyValue(item));
  }

  function canonicalizePolicyValue(value) {
    const raw = String(value || "").trim();
    if (!raw) return "";
    for (const [key, labels] of Object.entries(policyValueCatalog)) {
      if (raw === key || raw === labels.es || raw === labels.en) {
        return key;
      }
    }
    return raw;
  }

  function canonicalizePolicyList(items) {
    return (Array.isArray(items) ? items : [])
      .map((item) => canonicalizePolicyValue(item))
      .filter(Boolean);
  }

  function extractPolicyDefinitionId(policy) {
    return String((policy && (policy.id || policy["@id"])) || "").trim();
  }

  function extractAssetDefinitionId(asset) {
    return String((asset && (asset.id || asset["@id"])) || "").trim();
  }

  function findLocalAssetDefinition(assetId) {
    const target = String(assetId || "").trim();
    return (state.assets || []).find((asset) => extractAssetDefinitionId(asset) === target) || null;
  }

  function findLocalPolicyDefinition(policyId) {
    const target = String(policyId || "").trim();
    return (state.policies || []).find((policy) => extractPolicyDefinitionId(policy) === target) || null;
  }

  function firstNonEmpty(...values) {
    for (const value of values) {
      const text = String(value || "").trim();
      if (text) return text;
    }
    return "";
  }

  function catalogText(value) {
    if (Array.isArray(value)) return value.map((item) => String(item || "").trim()).filter(Boolean).join(", ");
    return String(value || "").trim();
  }

  function assetProperties(asset) {
    return asset && asset.properties && typeof asset.properties === "object" ? asset.properties : {};
  }

  function semanticAssetField(assetOrRow, ...keys) {
    const props = assetProperties(assetOrRow);
    for (const key of keys) {
      const value = props[key] !== undefined ? props[key] : assetOrRow && assetOrRow[key];
      const text = catalogText(value);
      if (text) return text;
    }
    return "";
  }

  function renderMetadataTokens(values) {
    return values
      .map((value) => catalogText(value))
      .filter(Boolean)
      .map((value) => `<span class="audit-token">${escapeHtml(value)}</span>`)
      .join("");
  }

  function renderAssetSemanticSummary(assetOrRow) {
    const tokens = renderMetadataTokens([
      semanticAssetField(assetOrRow, "dct:accessRights", "assetAccessRights", "accessRights"),
      semanticAssetField(assetOrRow, "ods:deliveryMode", "myds:deliveryMode", "deliveryMode"),
      semanticAssetField(assetOrRow, "dcat:mediaType", "assetMediaType", "mediaType"),
      semanticAssetField(assetOrRow, "dcat:theme", "topicCode", "assetTheme", "theme")
    ]);
    const keywords = semanticAssetField(assetOrRow, "dcat:keyword", "keywords", "assetKeywords");
    const license = semanticAssetField(assetOrRow, "dct:license", "licenseUrl", "assetLicense");
    const publisher = semanticAssetField(assetOrRow, "dct:publisher", "publisher");
    return `
      <div class="catalog-policy-cell">
        ${tokens ? `<div class="catalog-policy-summary">${tokens}</div>` : `<span class="muted">${escapeHtml(t.notAvailable)}</span>`}
        ${keywords ? `<div class="catalog-policy-group"><span class="muted">Keywords:</span> ${escapeHtml(keywords)}</div>` : ""}
        ${license ? `<div class="catalog-policy-group"><span class="muted">License:</span> ${escapeHtml(license)}</div>` : ""}
        ${publisher ? `<div class="catalog-policy-group"><span class="muted">Publisher:</span> ${escapeHtml(publisher)}</div>` : ""}
      </div>
    `;
  }

  function findFederatedCatalogRow(providerDataspaceId, providerConnectorId, assetId, policyId = "") {
    const providerDs = String(providerDataspaceId || "").trim();
    const providerId = String(providerConnectorId || "").trim();
    const targetAsset = String(assetId || "").trim();
    const targetPolicy = String(policyId || "").trim();
    return (state.federated || []).find((row) => {
      const rowProvider = String(row.providerRaw || row.provider || "").trim();
      const rowProviderDs = String(row.providerDataspaceId || "").trim();
      return String(row.assetId || "").trim() === targetAsset &&
        (!targetPolicy || String(row.policyId || "").trim() === targetPolicy) &&
        (!providerId || rowProvider === providerId) &&
        (!providerDs || rowProviderDs === providerDs);
    }) || null;
  }

  function findCatalogRowForEvidence(providerDataspaceId, providerConnectorId, assetId, policyId = "") {
    const federatedRow = findFederatedCatalogRow(providerDataspaceId, providerConnectorId, assetId, policyId);
    if (federatedRow) return federatedRow;
    const localAsset = findLocalAssetDefinition(assetId);
    if (localAsset) return localAsset;
    return {
      assetId,
      policyId,
      providerDataspaceId,
      providerConnectorId
    };
  }

  function catalogMetadataFingerprint(row) {
    const assetId = semanticAssetField(row, "assetId") || extractAssetDefinitionId(row);
    const metadata = {
      assetId,
      policyId: semanticAssetField(row, "policyId", "ods:policyId", "myds:policyId"),
      contractId: semanticAssetField(row, "contractId", "ods:contractId", "myds:contractId"),
      title: semanticAssetField(row, "dct:title", "assetName", "name"),
      description: semanticAssetField(row, "dct:description", "assetDescription", "description"),
      publisher: semanticAssetField(row, "dct:publisher", "publisher"),
      license: semanticAssetField(row, "dct:license", "licenseUrl", "assetLicense"),
      accessRights: semanticAssetField(row, "dct:accessRights", "assetAccessRights", "accessRights"),
      theme: semanticAssetField(row, "dcat:theme", "topicCode", "assetTheme", "theme"),
      keywords: semanticAssetField(row, "dcat:keyword", "keywords", "assetKeywords"),
      mediaType: semanticAssetField(row, "dcat:mediaType", "assetMediaType", "mediaType"),
      deliveryMode: semanticAssetField(row, "ods:deliveryMode", "myds:deliveryMode", "deliveryMode"),
      baseUrl: semanticAssetField(row, "objectUrl", "baseUrl"),
      catalogSource: semanticAssetField(row, "catalogSource")
    };
    const compact = Object.fromEntries(Object.entries(metadata).filter(([, value]) => catalogText(value)));
    const canonical = JSON.stringify(compact, Object.keys(compact).sort());
    let hash = 0;
    for (let index = 0; index < canonical.length; index += 1) {
      hash = ((hash << 5) - hash + canonical.charCodeAt(index)) | 0;
    }
    return {
      profile: "ods-dcat-fingerprint-1.0",
      hash: `ui-${Math.abs(hash).toString(16)}`,
      metadata: compact
    };
  }

  function catalogEvidence(providerDataspaceId, providerConnectorId, assetId, policyId = "") {
    const row = findCatalogRowForEvidence(providerDataspaceId, providerConnectorId, assetId, policyId);
    return {
      catalogMetadata: catalogMetadataFingerprint(row)
    };
  }


  function fallbackContractDefinition(contractId, policyId, assetId) {
    return {
      "@id": contractId,
      accessPolicyId: policyId,
      contractPolicyId: policyId,
      assetsSelector: [
        {
          operandLeft: "https://w3id.org/edc/v0.0.1/ns/id",
          operator: "=",
          operandRight: assetId,
          rightOperand: assetId,
          leftOperand: "id"
        }
      ]
    };
  }


  function buildPolicyDefinitionMap(items) {
    const map = new Map();
    for (const item of Array.isArray(items) ? items : []) {
      const id = extractPolicyDefinitionId(item);
      if (id) {
        map.set(id, item);
      }
    }
    return map;
  }

  function renderPolicyClauses(policy) {
    const policyData = (policy && policy.policy) || {};
    const summaryBits = [];
    const internalUse = localizePolicyValue(policyData.internalUse || "");
    const aiUsage = localizePolicyValue(policyData.aiUsage || "");
    const redistribution = localizePolicyValue(policyData.redistributionMode || policyData.onwardTransfer || "");
    if (internalUse) summaryBits.push(`${t.policyDetailsInternal}: ${internalUse}`);
    if (aiUsage) summaryBits.push(`${t.policyDetailsAi}: ${aiUsage}`);
    if (redistribution) summaryBits.push(`${t.policyDetailsRedistribution}: ${redistribution}`);

    const clauseGroups = [
      {
        label: t.policyDetailsPermitted,
        items: localizePolicyList((policyData.permission || []).map((entry) => entry && entry.action))
      },
      {
        label: t.policyDetailsProhibited,
        items: localizePolicyList((policyData.prohibition || []).map((entry) => entry && entry.action))
      },
      {
        label: t.policyDetailsDuties,
        items: localizePolicyList((policyData.duty || []).map((entry) => entry && entry.action))
      }
    ].filter((group) => group.items.length);

    return {
      summaryBits,
      clauseGroups,
      hasContent: summaryBits.length > 0 || clauseGroups.length > 0
    };
  }

  function renderCatalogPolicyCell(row, policyMap) {
    const policy = policyMap.get(String(row.policyId || "").trim());
    const title = policy
      ? ((policy.policy && (policy.policy.name || policy.policy.title)) || extractPolicyDefinitionId(policy) || row.policyId || t.notAvailable)
      : (row.policyId || t.notAvailable);
    const contractLine = row.contractId
      ? `<div class="muted">${escapeHtml(t.tableContract)}: ${escapeHtml(row.contractId)}</div>`
      : "";
    const clauses = policy ? renderPolicyClauses(policy) : null;
    if (!clauses || !clauses.hasContent) {
      return `
        <div class="catalog-policy-cell">
          <strong>${escapeHtml(title)}</strong>
          ${contractLine}
          <div class="muted">${escapeHtml(t.policyClausesUnavailable)}</div>
        </div>
      `;
    }

    const summary = clauses.summaryBits.length
      ? `<div class="catalog-policy-summary">${clauses.summaryBits.map((item) => `<span class="audit-token">${escapeHtml(item)}</span>`).join("")}</div>`
      : "";
    const groups = clauses.clauseGroups.map((group) => `
      <div class="catalog-policy-group">
        <span class="muted">${escapeHtml(group.label)}:</span>
        ${group.items.map((item) => `<span class="audit-token">${escapeHtml(item)}</span>`).join("")}
      </div>
    `).join("");

    return `
      <div class="catalog-policy-cell">
        <strong>${escapeHtml(title)}</strong>
        ${contractLine}
        ${summary}
        ${groups}
      </div>
    `;
  }

  function buildAssetNarrative(report) {
    if (!report) return t.assetAuditNoReport;
    const inferred = report.inferredMetadata || {};
    const title = inferred.title || "";
    const description = inferred.description || "";
    const type = report.documentType || "";
    const classification = getLocalizedClassification(report);
    const parts = [];
    if (title) parts.push(lang === "es" ? `Título detectado: ${title}.` : `Detected title: ${title}.`);
    if (description) parts.push(description.endsWith(".") ? description : `${description}.`);
    if (type) parts.push(lang === "es" ? `Tipo detectado: ${type}.` : `Detected type: ${type}.`);
    parts.push(lang === "es" ? `Clasificación propuesta: ${classification}.` : `Proposed classification: ${classification}.`);
    return parts.join(" ").trim() || report.summary || t.assetAuditNoReport;
  }

  function buildPolicyNarrative(draft) {
    if (!draft) return t.policyAuditNoReport;
    const profile = draft.policyProfileLabel || draft.policyProfile || t.notAvailable;
    const internalUse = localizePolicyValue(draft.internalUse || "");
    const aiUsage = localizePolicyValue(draft.aiUsage || "");
    const redistribution = localizePolicyValue(draft.redistributionMode || draft.onwardTransfer || "");
    const classification = draft.classificationLabel || t.notAvailable;
    return lang === "es"
      ? `Perfil sugerido: ${profile}. Uso interno: ${internalUse}. Uso para IA: ${aiUsage}. Redistribución: ${redistribution}. Clasificación: ${classification}.`
      : `Suggested profile: ${profile}. Internal use: ${internalUse}. AI usage: ${aiUsage}. Redistribution: ${redistribution}. Classification: ${classification}.`;
  }

  function buildPolicyReasoning(draft) {
    if (!draft) return "";
    const clauses = []
      .concat(localizePolicyList(draft.duties || []).slice(0, 3))
      .filter(Boolean);
    const base = lang === "es"
      ? `La propuesta combina ${localizePolicyValue(draft.internalUse || "")}, ${localizePolicyValue(draft.aiUsage || "")} y ${localizePolicyValue(draft.redistributionMode || draft.onwardTransfer || "")}.`
      : `The proposal combines ${localizePolicyValue(draft.internalUse || "")}, ${localizePolicyValue(draft.aiUsage || "")} and ${localizePolicyValue(draft.redistributionMode || draft.onwardTransfer || "")}.`;
    if (!clauses.length) return base;
    return lang === "es"
      ? `${base} Cláusulas destacadas: ${clauses.join(", ")}.`
      : `${base} Key clauses: ${clauses.join(", ")}.`;
  }

  function auditTone(report) {
    const key = report?.legalClassification?.key || "";
    if (key === "restricted-sensitive-data-review" || key === "restricted-personal-data-review" || key === "missing-legal-basis-review") {
      return "danger";
    }
    if (report?.decision === "allow-with-warning" || report?.overallRisk === "medium") {
      return "warn";
    }
    if (report?.decision === "manual-review" || report?.overallRisk === "high") {
      return "danger";
    }
    if (report?.decision === "allow" || report?.overallRisk === "low") {
      return "safe";
    }
    return "info";
  }

  function auditToneLabel(tone) {
    return {
      safe: t.assetAuditToneSafe,
      warn: t.assetAuditToneWarn,
      danger: t.assetAuditToneDanger,
      info: t.assetAuditToneInfo
    }[tone] || t.assetAuditToneInfo;
  }

  function formatDateTime(value) {
    if (!value) return "-";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return new Intl.DateTimeFormat(lang === "en" ? "en-GB" : "es-ES", {
      dateStyle: "short",
      timeStyle: "medium"
    }).format(date);
  }

  function simplifyResource(resource) {
    if (!resource) return "-";
    if (typeof resource === "string") return resource;
    const parts = [];
    if (resource.assetId) parts.push(resource.assetId);
    if (resource.transferId) parts.push(`transfer=${resource.transferId}`);
    if (resource.negotiationId) parts.push(`neg=${resource.negotiationId}`);
    return parts.join(" · ") || prettyData(resource);
  }

  function extractAuditParties(trace) {
    // La traza **es** el evento. Venia envuelta en `{event: {...}}` por el
    // servicio de gobernanza; aqui se guarda plana. Se aceptan las dos formas
    // para que un registro escrito antes de este cambio se siga leyendo.
    const event = (trace && trace.event) || trace || {};
    const resource = event.resource || {};
    const evidence = event.evidence || {};
    const fallbackDataspace = trace.dataspaceId || event.dataspaceId || "";
    return {
      consumerDataspaceId: resource.consumerDataspaceId || evidence.consumerDataspaceId || fallbackDataspace || "-",
      consumerConnectorId: resource.consumerConnectorId || evidence.consumerConnectorId || evidence.connectorId || "-",
      providerDataspaceId: resource.providerDataspaceId || evidence.providerDataspaceId || fallbackDataspace || "-",
      providerConnectorId: resource.providerConnectorId || evidence.providerConnectorId || "-"
    };
  }

  function formatParty(dataspaceId, connectorId) {
    const ds = escapeHtml(dataspaceId || "-");
    const connector = escapeHtml(connectorId || "-");
    return `${ds}<br><span class="muted">${connector}</span>`;
  }

  function normalizeStatusLabel(value) {
    return String(value || "").trim().toUpperCase() || t.participantAuditUnavailable;
  }

  function shortenTraceId(value) {
    const raw = String(value || "").trim();
    if (!raw) return "-";
    if (raw.length <= 18) return raw;
    return `${raw.slice(0, 12)}...${raw.slice(-4)}`;
  }

  function shortenKid(value) {
    const raw = String(value || "").trim();
    if (!raw) return "";
    const hashIndex = raw.indexOf("#");
    if (hashIndex >= 0) {
      return raw.slice(hashIndex + 1);
    }
    return raw.length > 28 ? `${raw.slice(0, 18)}...${raw.slice(-6)}` : raw;
  }

  function getTraceNodes() {
    let table = byId("transferTraceTable");
    let clearBtn = byId("clearTransferTraceBtn");
    if (table && clearBtn) {
      return { table, clearBtn };
    }

    const container = (features.federated ? byId("operationConsumerPanel") : null) || document.querySelector(".container");
    if (!container) return { table: null, clearBtn: null };

    const card = document.createElement("div");
    card.className = "card";
    card.id = "transferTraceCard";

    const title = document.createElement("h2");
    title.textContent = t.traceTitle;
    card.appendChild(title);

    const description = document.createElement("p");
    description.className = "muted";
    description.textContent = t.traceDescription;
    card.appendChild(description);

    clearBtn = document.createElement("button");
    clearBtn.id = "clearTransferTraceBtn";
    clearBtn.className = "secondary";
    clearBtn.type = "button";
    clearBtn.textContent = t.traceClear;
    card.appendChild(clearBtn);

    table = document.createElement("table");
    table.id = "transferTraceTable";
    card.appendChild(table);

    const statusNode = byId("status");
    if (statusNode && statusNode.parentElement === container) {
      container.insertBefore(card, statusNode);
    } else {
      container.appendChild(card);
    }

    return { table, clearBtn };
  }

  function getParticipantAuditNodes() {
    let table = byId("participantAuditTable");
    let reloadBtn = byId("reloadParticipantAuditBtn");
    let status = byId("participantAuditStatus");
    if (table && reloadBtn && status) {
      return { table, reloadBtn, status };
    }

    const container = (features.federated ? byId("operationConsumerPanel") : null) || document.querySelector(".container");
    if (!container) return { table: null, reloadBtn: null, status: null };

    const card = document.createElement("div");
    card.className = "card";
    card.id = "participantAuditCard";

    const title = document.createElement("h2");
    title.textContent = t.participantAuditTitle;
    card.appendChild(title);

    const description = document.createElement("p");
    description.className = "muted";
    description.textContent = t.participantAuditDescription;
    card.appendChild(description);

    reloadBtn = document.createElement("button");
    reloadBtn.id = "reloadParticipantAuditBtn";
    reloadBtn.className = "secondary";
    reloadBtn.type = "button";
    reloadBtn.textContent = t.participantAuditReload;
    card.appendChild(reloadBtn);

    status = document.createElement("div");
    status.id = "participantAuditStatus";
    status.className = "status muted";
    card.appendChild(status);

    table = document.createElement("table");
    table.id = "participantAuditTable";
    card.appendChild(table);

    const statusNode = byId("status");
    if (statusNode && statusNode.parentElement === container) {
      container.insertBefore(card, statusNode);
    } else {
      container.appendChild(card);
    }

    return { table, reloadBtn, status };
  }

  function renderTransferTrace() {
    const { table } = getTraceNodes();
    if (!table) return;

    table.innerHTML = "";
    const thead = document.createElement("thead");
    const headRow = document.createElement("tr");
    ["#", t.traceStep, t.traceState, t.traceData].forEach((label) => {
      const th = document.createElement("th");
      th.textContent = label;
      headRow.appendChild(th);
    });
    thead.appendChild(headRow);
    table.appendChild(thead);

    const tbody = document.createElement("tbody");
    if (!state.transferTrace.length) {
      const tr = document.createElement("tr");
      const td = document.createElement("td");
      td.colSpan = 4;
      td.textContent = t.traceNoRows;
      tr.appendChild(td);
      tbody.appendChild(tr);
      table.appendChild(tbody);
      return;
    }

    state.transferTrace.forEach((item, idx) => {
      const tr = document.createElement("tr");

      const tdIndex = document.createElement("td");
      tdIndex.textContent = `${idx + 1}`;
      tr.appendChild(tdIndex);

      const tdStep = document.createElement("td");
      tdStep.textContent = `${item.timestamp} | ${item.step}`;
      tr.appendChild(tdStep);

      const tdState = document.createElement("td");
      tdState.textContent = item.ok ? "OK" : "ERROR";
      tdState.className = item.ok ? "status-ok" : "status-error";
      tr.appendChild(tdState);

      const tdData = document.createElement("td");
      const pre = document.createElement("pre");
      pre.className = "trace-data";
      pre.textContent = prettyData(item.data);
      tdData.appendChild(pre);
      tr.appendChild(tdData);

      tbody.appendChild(tr);
    });

    table.appendChild(tbody);
  }

  function renderParticipantAudit(rows) {
    const { table } = getParticipantAuditNodes();
    if (!table) return;
    renderTable("participantAuditTable", rows, [
      { label: t.participantAuditTrace, render: (row) => `<code>${escapeHtml(row.traceId)}</code>` },
      { label: t.participantAuditEvent, render: (row) => escapeHtml(row.eventType) },
      { label: t.participantAuditAsset, render: (row) => escapeHtml(row.assetLabel) },
      { label: t.participantAuditConsume, render: (row) => row.consumerHtml },
      { label: t.participantAuditProvide, render: (row) => row.providerHtml },
      { label: t.participantAuditTime, render: (row) => escapeHtml(row.receivedAtLabel) }
    ]);
  }

  function addTransferTrace(step, data, ok = true) {
    const currentDataspaceId = ((window.DATASPACE_SITE && window.DATASPACE_SITE.config && window.DATASPACE_SITE.config.organisationId) || "").trim();
    const normalizedData = {
      consumerDataspaceId: data && data.consumerDataspaceId ? data.consumerDataspaceId : currentDataspaceId || "",
      providerDataspaceId: data && data.providerDataspaceId ? data.providerDataspaceId : currentDataspaceId || "",
      consumerConnectorId: data && data.consumerConnectorId ? data.consumerConnectorId : cfg.id || "",
      ...(data || {})
    };
    const time = new Date().toISOString();
    state.transferTrace.unshift({
      timestamp: time,
      step,
      ok,
      data: normalizedData
    });
    if (state.transferTrace.length > 80) {
      state.transferTrace.length = 80;
    }
    renderTransferTrace();
  }

  function uniqueId(prefix) {
    const ts = Date.now().toString(36);
    const rand = Math.random().toString(36).slice(2, 8);
    const safePrefix = String(prefix || "item").replace(/[^a-zA-Z0-9_-]+/g, "-").toLowerCase();
    return `${safePrefix}-${ts}-${rand}`;
  }

  function readInputValue(id, fallback = "") {
    const el = byId(id);
    if (!el) return fallback;
    return String(el.value || "").trim() || fallback;
  }

  function parseCsvList(value) {
    return String(value || "")
      .split(",")
      .map((item) => item.trim())
      .filter((item) => item.length > 0);
  }

  function populateSelect(selectId, rows, getValue, getLabel) {
    const select = byId(selectId);
    if (!select) return;
    select.innerHTML = "";
    rows.forEach((row) => {
      const opt = document.createElement("option");
      opt.value = getValue(row);
      opt.textContent = getLabel(row);
      select.appendChild(opt);
    });
  }

  function triggerBlobDownload(blob, fileName = "") {
    if (!blob) {
      throw new Error("Contenido de descarga vacio");
    }
    const objectUrl = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = objectUrl;
    const normalized = normalizeFileName(fileName, "");
    if (normalized) {
      a.download = normalized;
    }
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(objectUrl);
  }

  function isNegotiationCompleted(status) {
    const s = (status || "").toUpperCase();
    return s === "COMPLETED" || s === "FINALIZED" || s === "CONFIRMED" || s === "APPROVED";
  }

  async function connectorFetch(baseUrl, path, options = {}) {
    const accessToken = await ensureAccessToken();
    if (!accessToken) {
      throw new Error(t.missingToken);
    }
    const headers = {
      "Content-Type": "application/json",
      ...(options.headers || {})
    };
    headers.Authorization = `Bearer ${accessToken}`;

    const res = await fetch(`${baseUrl}${path}`, {
      ...options,
      headers
    });
    if (!res.ok) {
      const txt = await res.text();
      throw new Error(`${res.status} ${res.statusText} ${txt}`);
    }
    return res.status === 204 ? null : res.json();
  }

  async function localApi(path, options = {}) {
    return connectorFetch(cfg.baseUrl, path, options);
  }

  async function connectorFetchBlob(baseUrl, path, options = {}) {
    const accessToken = await ensureAccessToken();
    if (!accessToken) {
      throw new Error(t.missingToken);
    }
    const headers = {
      ...(options.headers || {})
    };
    headers.Authorization = `Bearer ${accessToken}`;

    const res = await fetch(`${baseUrl}${path}`, {
      ...options,
      headers
    });
    if (!res.ok) {
      const txt = await res.text();
      throw new Error(`${res.status} ${res.statusText} ${txt}`);
    }
    return res;
  }

  function extractFileNameFromContentDisposition(disposition, fallback) {
    if (!disposition) return fallback;
    const match = disposition.match(/filename\*?=(?:UTF-8''|\")?([^;\"]+)/i);
    if (!match || !match[1]) return fallback;
    const cleaned = decodeURIComponent(match[1].trim().replace(/^"|"$/g, ""));
    return normalizeFileName(cleaned, fallback);
  }

  function getConnectorBaseUrlByProvider(provider) {
    if (!provider || provider === cfg.id) {
      return cfg.baseUrl;
    }
    const providerTarget = (cfg.negotiationTargets || []).find((target) => target.id === provider);
    if (!providerTarget || !providerTarget.baseUrl) {
      throw new Error(`${t.providerNotConfigured}: ${provider}`);
    }
    return providerTarget.baseUrl;
  }

  function findMatchingNegotiation(provider, assetId) {
    return state.negotiations.find(
      (n) => isNegotiationCompleted(n.status) && n.providerConnectorId === provider && n.assetId === assetId
    );
  }



  async function initAuth() {
    const authCfg = cfg.auth || {};
    if (!authCfg.enabled) {
      return;
    }
    if (typeof window.Keycloak !== "function") {
      try {
        const mod = await import("./vendor/keycloak.js");
        window.Keycloak = mod?.default || mod?.Keycloak || window.Keycloak;
      } catch (e) {
        throw new Error(`${t.keycloakImportError} (${e && e.message ? e.message : "import error"})`);
      }
    }
    if (typeof window.Keycloak !== "function") {
      throw new Error(t.keycloakUnavailable);
    }

    const keycloak = new window.Keycloak({
      url: authCfg.url,
      realm: authCfg.realm,
      clientId: authCfg.clientId
    });
    state.keycloak = keycloak;

    const authenticated = await keycloak.init({
      onLoad: "login-required",
      checkLoginIframe: false,
      pkceMethod: "S256"
    });
    addTransferTrace(t.traceAuthStarted, {
      connectorId: cfg.id,
      authMode: "login-required"
    });
    if (!authenticated || !keycloak.token) {
      throw new Error(t.keycloakAuthFailed);
    }
    // El conector de quien mira, sacado de su token.
    //
    // La pagina se genera una vez y la comparte el nodo, asi que el
    // identificador que trae es el del nodo. Un nodo tiene un conector por
    // participante: sin esto, a cada persona le saldria la oferta del nodo
    // como suya y no podria negociar nada aqui dentro.
    const conectorDelToken = String(keycloak.tokenParsed?.connector_id || "").trim();
    if (conectorDelToken) {
      cfg.id = conectorDelToken;
      const titulo = byId("consoleHeading");
      if (titulo) {
        titulo.textContent = `${lang === "en" ? "Connector" : "Conector"} ${conectorDelToken}`;
      }
    }
    const quienEntra = String(
      keycloak.tokenParsed?.email || keycloak.tokenParsed?.preferred_username || ""
    ).trim();
    const duenno = byId("consoleOwner");
    if (quienEntra && duenno) {
      duenno.textContent = quienEntra;
    }

    const refreshSeconds = Math.max(5, Number(authCfg.refreshSeconds || 30));
    rememberAccessToken(keycloak.token);
    state.idToken = keycloak.idToken || "";
    window.__DATASPACE_ID_TOKEN = state.idToken;
    window.__DATASPACE_ENSURE_FRESH_TOKEN = async () => {
      const refreshed = await keycloak.updateToken(refreshSeconds);
      if ((refreshed || !window.__DATASPACE_ACCESS_TOKEN) && keycloak.token) {
        rememberAccessToken(keycloak.token);
        state.idToken = keycloak.idToken || state.idToken || "";
        window.__DATASPACE_ID_TOKEN = state.idToken;
      }
      return window.__DATASPACE_ACCESS_TOKEN || "";
    };
    const payload = parseJwtPayload(state.accessToken);
    addTransferTrace(t.traceAuthCompleted, {
      connectorId: cfg.id,
      tokenMasked: maskToken(state.accessToken),
      tokenExp: payload.exp || "",
      tokenIat: payload.iat || "",
      subject: payload.sub || "",
      preferredUsername: payload.preferred_username || ""
    });
    window.setInterval(async () => {
      try {
        const refreshed = await keycloak.updateToken(refreshSeconds);
        if (refreshed && keycloak.token) {
          rememberAccessToken(keycloak.token);
          state.idToken = keycloak.idToken || state.idToken || "";
          window.__DATASPACE_ID_TOKEN = state.idToken;
          addTransferTrace(t.traceTokenRefreshed, {
            tokenMasked: maskToken(state.accessToken)
          });
        }
      } catch (e) {
        console.error(t.refreshFailed, e);
      }
    }, 10000);
  }

  async function ensureAccessToken() {
    if (isUsableJwt(state.accessToken)) {
      return state.accessToken;
    }
    const keycloak = state.keycloak;
    if (!keycloak) {
      rememberAccessToken("");
      return "";
    }
    try {
      await keycloak.updateToken(30);
      if (isUsableJwt(keycloak.token)) {
        rememberAccessToken(keycloak.token);
        state.idToken = keycloak.idToken || state.idToken || "";
        window.__DATASPACE_ID_TOKEN = state.idToken;
        return state.accessToken;
      }
    } catch (error) {
      console.warn(t.refreshFailed, error);
    }
    rememberAccessToken("");
    if (typeof keycloak.login === "function") {
      keycloak.login();
    }
    return "";
  }

  function renderTable(id, rows, columns) {
    const table = byId(id);
    if (!table) return;
    table.innerHTML = "";
    const thead = document.createElement("thead");
    const trh = document.createElement("tr");
    columns.forEach((c) => {
      const th = document.createElement("th");
      th.textContent = c.label;
      trh.appendChild(th);
    });
    thead.appendChild(trh);
    table.appendChild(thead);

    const tbody = document.createElement("tbody");
    rows.forEach((row) => {
      const tr = document.createElement("tr");
      columns.forEach((c) => {
        const td = document.createElement("td");
        td.innerHTML = c.render(row);
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
  }

  async function fetchJsonFromCandidates(bases, path, options = {}) {
    const optional404 = Boolean(options.optional404);
    // The governance audit trail is read from another origin, and until now it
    // was read by nobody in particular: no credential travelled with the
    // request, which is why that endpoint answers 155 traces to anyone on the
    // internet. Sending the signed-in user's token is the half of the fix that
    // belongs here; governance requiring it is the other half and lands after
    // this, because doing it in the other order empties both consoles.
    //
    // Opt-in per call rather than on every candidate base: an Authorization
    // header makes a cross-origin GET preflighted, and only the governance
    // origin is known to answer that preflight - verified against production,
    // Access-Control-Allow-Headers: Content-Type, Authorization.
    const headers = { Accept: "application/json" };
    if (options.authenticated) {
      try {
        const accessToken = await ensureAccessToken();
        if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
      } catch (_err) {
        // Not signed in. The request goes out bare and governance decides.
      }
    }
    let lastError = null;
    for (const base of bases) {
      try {
        const separator = path.startsWith("/") ? "" : "/";
        const response = await fetch(`${base.replace(/\/$/, "")}${separator}${path}`, {
          method: "GET",
          cache: "no-store",
          headers
        });
        if (optional404 && response.status === 404) {
          return null;
        }
        if (!response.ok) {
          const txt = await response.text();
          lastError = new Error(`${response.status}: ${txt}`);
          continue;
        }
        return response.json();
      } catch (err) {
        lastError = err;
      }
    }
    if (optional404) return null;
    throw lastError || new Error(t.participantAuditUnavailable);
  }

  async function reloadLocalCatalog() {
    if (!features.myAssets) return;
    const [assets, policies, contracts, negotiations] = await Promise.all([
      localApi("/management/v3/assets"),
      localApi("/management/v3/policydefinitions"),
      localApi("/management/v3/contractdefinitions"),
      localApi("/management/v3/negotiations")
    ]);
    const rawAssets = Array.isArray(assets) ? assets : [];
    const rawPolicies = Array.isArray(policies) ? policies : [];
    const rawContracts = Array.isArray(contracts) ? contracts : [];
    const rawNegotiations = Array.isArray(negotiations) ? negotiations : [];

    // Sin filtrar por dueno.
    //
    // Aqui se separaban los recursos de tres conectores que compartian el
    // mismo backend -- el despliegue de origen -- adivinando el dueno por el
    // nombre del identificador, con /connector-[a-z0-9]+/. Un nodo tiene un
    // conector, asi que todo lo que devuelve es suyo; y la adivinanza hacia
    // dano: un activo llamado `asset-connector-mtck41dc-x` -- lo que genera la
    // propia consola cuando el conector se llama `connector` -- daba un dueno
    // inventado, `connector-mtck41dc`, y negociar contra el fallaba con
    // «proveedor no configurado».
    state.assets = rawAssets;
    state.policies = rawPolicies;
    state.contracts = rawContracts;
    state.negotiations = rawNegotiations;

    renderTable("assetsTable", state.assets, [
      { label: t.tableId, render: (r) => r.id || r["@id"] || "" },
      { label: t.tableName, render: (r) => escapeHtml(semanticAssetField(r, "dct:title", "name")) },
      { label: t.tableDescription, render: (r) => escapeHtml(semanticAssetField(r, "dct:description", "description")) },
      { label: t.tableMetadata, render: (r) => renderAssetSemanticSummary(r) }
    ]);

    renderTable("policiesTable", state.policies, [
      { label: t.tableId, render: (r) => r.id || r["@id"] || "" },
      { label: t.tableName, render: (r) => (r.policy && (r.policy.name || r.policy.title)) || "" },
      {
        label: t.tablePolicy,
        render: (r) => {
          const clauses = renderPolicyClauses(r);
          if (!clauses.hasContent) {
            return (r.policy && r.policy.licenseUrl) || `<span class="muted">${escapeHtml(t.policyClausesUnavailable)}</span>`;
          }
          const groups = clauses.clauseGroups.map((group) => `
            <div class="catalog-policy-group">
              <span class="muted">${escapeHtml(group.label)}:</span>
              ${group.items.map((item) => `<span class="audit-token">${escapeHtml(item)}</span>`).join("")}
            </div>
          `).join("");
          return `
            <div class="catalog-policy-cell">
              ${clauses.summaryBits.length ? `<div class="catalog-policy-summary">${clauses.summaryBits.map((item) => `<span class="audit-token">${escapeHtml(item)}</span>`).join("")}</div>` : ""}
              ${groups}
            </div>
          `;
        }
      }
    ]);

    renderTable("contractsTable", state.contracts, [
      { label: t.tableId, render: (r) => r.id || r["@id"] || "" },
      { label: t.tablePolicy, render: (r) => r.contractPolicyId || "" },
      {
        label: t.tableAsset,
        render: (r) => {
          const s = (r.assetsSelector || []).find((x) => {
            const left = String(x.leftOperand || x.operandLeft || "");
            return left === "id" || left.endsWith("/id");
          });
          return s ? (s.rightOperand || s.operandRight || "") : "";
        }
      }
    ]);

    renderTable("negotiationsTable", state.negotiations, [
      { label: t.tableId, render: (r) => r.id || r["@id"] || "" },
      { label: t.tableConsumer, render: (r) => r.consumerConnectorId || "" },
      { label: t.tableProvider, render: (r) => r.providerConnectorId || "" },
      { label: t.tableAsset, render: (r) => r.assetId || "" },
      { label: t.tablePolicy, render: (r) => r.policyId || "" },
      { label: t.tableStatus, render: (r) => r.status || "" },
      {
        label: t.tableDownload,
        render: (r) => {
          const completed = isNegotiationCompleted(r.status);
          if (!completed) {
            return `<button class="secondary" disabled>${t.pending}</button>`;
          }
          if (!r.assetId) {
            return `<span class="muted">${t.notAvailable}</span>`;
          }
          const fileName = `${r.assetId || "asset"}-data`;
          return `<button class="secondary" onclick='window.downloadNegotiatedAsset(${JSON.stringify(r.providerConnectorId || "")}, ${JSON.stringify(r.assetId)}, ${JSON.stringify(fileName)})'>${t.download}</button>`;
        }
      }
    ]);

    populateSelect(
      "contractAssetIdSelect",
      state.assets,
      (r) => r.id || r["@id"] || "",
      (r) => {
        const id = r.id || r["@id"] || "";
        const name = (r.properties && r.properties.name) || "";
        return name ? `${name} (${id})` : id;
      }
    );

    populateSelect(
      "contractPolicyIdSelect",
      state.policies,
      (r) => r.id || r["@id"] || "",
      (r) => {
        const id = r.id || r["@id"] || "";
        const name = (r.policy && (r.policy.name || r.policy.title)) || "";
        return name ? `${name} (${id})` : id;
      }
    );
  }

  async function reloadNegotiationsOnly() {
    if (!features.allowDownload) {
      state.negotiations = [];
      return;
    }
    state.negotiations = await localApi("/management/v3/negotiations");
  }


  // El registro de operaciones vive en este nodo. Antes esta lista tenia una
  // segunda direccion, la de un servicio de gobernanza externo; un nodo que
  // instala un tercero no tiene ninguno, y consultarlo filtraba a un dominio
  // ajeno lo que este nodo hace.
  function auditBaseUrls() {
    return [`${window.location.origin}/api/audit`];
  }


  function upsertNegotiationTargets(items) {
    if (!Array.isArray(items)) return;
    cfg.negotiationTargets = Array.isArray(cfg.negotiationTargets) ? cfg.negotiationTargets : [];
    items.forEach((item) => {
      // El identificador que dice el catalogo, no uno adivinado del nombre del
      // activo: esa adivinanza daba duenos que no existen y dejaba destinos de
      // negociacion contra conectores inventados.
      const providerId = String(item.providerConnectorRawId || item.providerConnectorId || "").trim();
      const providerBaseUrl = String(item.providerBaseUrl || "").trim();
      const providerLabel = String(item.providerLabel || providerId || "").trim();
      if (!providerId || !providerBaseUrl) return;
      const providerDataspaceId = String(item.providerDataspaceId || "").trim();
      const existing = cfg.negotiationTargets.find((target) => target.id === providerId && String(target.dataspaceId || "") === providerDataspaceId);
      if (existing) {
        existing.baseUrl = providerBaseUrl;
        existing.label = providerLabel || existing.label;
        return;
      }
      cfg.negotiationTargets.push({
        id: providerId,
        dataspaceId: providerDataspaceId,
        label: providerLabel || providerId,
        baseUrl: providerBaseUrl
      });
    });
  }


  function currentUserInfo() {
    const payload = parseJwtPayload(state.accessToken || "");
    return {
      subject: payload.sub || "",
      email: payload.email || payload.preferred_username || "",
      username: payload.preferred_username || payload.email || ""
    };
  }

  function isParticipantTrace(trace) {
    const user = currentUserInfo();
    // La traza **es** el evento. Venia envuelta en `{event: {...}}` por el
    // servicio de gobernanza; aqui se guarda plana. Se aceptan las dos formas
    // para que un registro escrito antes de este cambio se siga leyendo.
    const event = (trace && trace.event) || trace || {};
    const resource = event.resource || {};
    const evidence = event.evidence || {};
    const identifiers = new Set(
      [
        cfg.id,
        user.email || "",
        user.username || "",
        user.subject || ""
      ].filter(Boolean)
    );
    const candidates = [
      resource.consumerConnectorId,
      resource.providerConnectorId,
      evidence.connectorId,
      evidence.consumerConnectorId,
      evidence.providerConnectorId,
      event.subject,
      evidence.username
    ].filter(Boolean);
    return candidates.some((value) => identifiers.has(String(value)));
  }








  async function loadParticipantAudit(forceRefresh = false) {
    const nodes = getParticipantAuditNodes();
    if (!nodes.table || !nodes.status) return;
    nodes.status.textContent = t.participantAuditLoading;
    nodes.status.classList.remove("status-error");
    try {
      // El registro vive en este nodo. Antes se pedia a un servicio de
      // gobernanza externo que no existe aqui, asi que esta pestana no
      // cargaba nunca.
      const res = await fetch(`${auditBaseUrls()[0]}/events?limit=200`, {
        headers: { Accept: "application/json" },
        cache: "no-store"
      });
      if (!res.ok) {
        throw new Error(`${res.status}`);
      }
      const payload = await res.json();
      const traces = (Array.isArray(payload && payload.items) ? payload.items : [])
        .filter(isParticipantTrace)
        .sort((left, right) => String(right.receivedAt || "").localeCompare(String(left.receivedAt || "")))
        .slice(0, 20);

      // El evento guardado es plano: lo que la consola envio, firmado. Antes
      // aqui se enriquecia cada traza con dos consultas mas al servicio
      // externo -- cumplimiento y auditoria documental -- que este producto
      // no tiene.
      const rows = traces.map((trace) => {
        const parties = extractAuditParties(trace);
        return {
          traceId: trace.eventId || trace.auditTraceId || "",
          eventType: trace.eventType || "-",
          assetLabel: simplifyResource(trace.resource),
          consumerHtml: formatParty(parties.consumerDataspaceId, parties.consumerConnectorId),
          providerHtml: formatParty(parties.providerDataspaceId, parties.providerConnectorId),
          receivedAtLabel: formatDateTime(trace.receivedAt)
        };
      });

      renderParticipantAudit(rows);
      nodes.status.textContent = rows.length ? t.participantAuditLoaded : t.participantAuditNoRows;
      nodes.status.classList.remove("status-error");
      state.participantAuditLoaded = true;
    } catch (err) {
      nodes.status.textContent = `${t.participantAuditError}: ${err.message}`;
      nodes.status.classList.add("status-error");
      if (forceRefresh) {
        console.warn("participant audit refresh failed", err);
      }
    }
  }

  async function publishAuditEvent(eventType, resource, outcome, evidence = {}) {
    const dataspaceId = ((window.DATASPACE_SITE && window.DATASPACE_SITE.config && window.DATASPACE_SITE.config.organisationId) || "").trim();
    if (!dataspaceId) {
      return null;
    }
    const user = currentUserInfo();
    const payload = {
      eventId: `evt-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      dataspaceId,
      eventType,
      timestamp: new Date().toISOString(),
      subject: user.email || user.subject || cfg.id,
      outcome,
      resource,
      evidence: {
        connectorId: cfg.id,
        username: user.username,
        ...evidence
      },
      signature: ""
    };
    let lastError = null;
    for (const base of auditBaseUrls()) {
      try {
        const response = await fetch(`${base.replace(/\/$/, "")}/events`, {
          method: "POST",
          headers: { "Content-Type": "application/json", Accept: "application/json" },
          body: JSON.stringify(payload)
        });
        if (!response.ok) {
          const txt = await response.text();
          lastError = new Error(`${response.status}: ${txt}`);
          continue;
        }
        return response.json();
      } catch (err) {
        lastError = err;
      }
    }
    if (lastError) {
      console.warn(t.auditPublishError, lastError);
    }
    return null;
  }




  async function postOnboardingJson(path, payload) {
    const response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(payload)
    });
    if (!response.ok) {
      const txt = await response.text();
      throw new Error(`${response.status}: ${txt}`);
    }
    return response.json();
  }

  async function postOnboardingJsonDetailed(path, payload) {
    const response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(payload)
    });
    const text = await response.text();
    let body = null;
    if (text) {
      try {
        body = JSON.parse(text);
      } catch (_err) {
        body = { message: text };
      }
    }
    return {
      ok: response.ok,
      status: response.status,
      body: body || {}
    };
  }

  function setInputIfPresent(id, value) {
    const el = byId(id);
    if (!el || value === undefined || value === null) return;
    el.value = Array.isArray(value) ? value.join(", ") : String(value);
  }

  function currentAssetMetadataForPublication(assetId, baseUrl) {
    const name = readInputValue("assetName");
    const description = readInputValue("assetDescription");
    const identifierValue = readInputValue("assetIdentifier");
    const dcatIdentifier = identifierValue.endsWith(":") ? `${identifierValue}${assetId}` : identifierValue;
    const mediaType = readInputValue("assetMediaType", "application/pdf");
    return {
      name,
      description,
      contenttype: mediaType,
      objectUrl: baseUrl,
      "dct:identifier": dcatIdentifier,
      "dct:title": name,
      "dct:description": description,
      "dcat:keyword": parseCsvList(readInputValue("assetKeywords")),
      "dcat:theme": readInputValue("assetTheme"),
      "dct:language": readInputValue("assetLanguage", lang),
      "dct:license": readInputValue("assetLicense", "https://creativecommons.org/licenses/by-nc/4.0/"),
      "dct:publisher": readInputValue(
        "assetPublisher",
        (window.DATASPACE_SITE && window.DATASPACE_SITE.config && window.DATASPACE_SITE.config.defaultPublisher) || "MyDataSpace"
      ),
      "dct:spatial": readInputValue("assetSpatial"),
      "dct:temporalStart": readInputValue("assetTemporalStart"),
      "dct:temporalEnd": readInputValue("assetTemporalEnd"),
      "dcat:distributionFormat": readInputValue("assetFormat", "application/pdf"),
      "dcat:mediaType": mediaType,
      "dct:accessRights": readInputValue("assetAccessRights", "public"),
      // `ods:`, no `myds:`. El perfil de metadatos exige `ods:deliveryMode`
      // y la consola enviaba `myds:deliveryMode`, el prefijo del proyecto de
      // origen: la validacion respondia «campos obligatorios pendientes:
      // ods:deliveryMode» pasara lo que pasara, asi que **no se podia
      // publicar nada desde la consola**, ni rellenandolo todo.
      "ods:deliveryMode": readInputValue("assetDeliveryMode", "download")
    };
  }

  function renderAssetMetadataValidation(validation) {
    if (!validation) return "";
    const missing = Array.isArray(validation.missing) ? validation.missing : [];
    const warnings = Array.isArray(validation.warnings) ? validation.warnings : [];
    const recommendations = Array.isArray(validation.recommendations) ? validation.recommendations : [];
    const rows = [
      missing.length ? `<li><strong>${escapeHtml(t.assetMetadataValidationMissing)}:</strong> ${missing.map((item) => `<span class="audit-token">${escapeHtml(item)}</span>`).join(" ")}</li>` : "",
      warnings.length ? `<li><strong>${escapeHtml(t.assetMetadataValidationWarnings)}:</strong> ${warnings.map((item) => escapeHtml(item)).join("; ")}</li>` : "",
      recommendations.length ? `<li><strong>${escapeHtml(t.assetMetadataValidationRecommendations)}:</strong> ${recommendations.map((item) => escapeHtml(item)).join("; ")}</li>` : ""
    ].filter(Boolean);
    const tone = validation.ok ? "safe" : "danger";
    return `
      <h4>${escapeHtml(t.assetMetadataValidationLabel)}</h4>
      <div class="audit-reason audit-reason--${tone === "safe" ? "low" : "high"}">
        <div class="audit-reason-head">
          <strong>${escapeHtml(validation.ok ? t.assetMetadataValidationPassed : t.assetMetadataValidationFailed)}</strong>
          <span class="audit-token">${escapeHtml(t.assetMetadataValidationScore)}: ${escapeHtml(String(validation.score == null ? t.notAvailable : validation.score))}</span>
        </div>
        ${rows.length ? `<ul class="audit-recommendations">${rows.join("")}</ul>` : `<p>${escapeHtml(t.assetAuditNoRecommendations)}</p>`}
      </div>
    `;
  }

  function formatAssetMetadataValidationError(validation) {
    const missing = Array.isArray(validation && validation.missing) ? validation.missing : [];
    const warnings = Array.isArray(validation && validation.warnings) ? validation.warnings : [];
    const details = missing.length
      ? `${t.assetMetadataValidationMissing}: ${missing.join(", ")}`
      : warnings.length
        ? `${t.assetMetadataValidationWarnings}: ${warnings.join("; ")}`
        : "";
    return details ? `${t.assetMetadataValidationFailed}. ${details}` : t.assetMetadataValidationFailed;
  }

  async function validateAssetMetadataBeforePublish(assetId, baseUrl) {
    setStatus(t.assetMetadataValidating);
    const metadata = currentAssetMetadataForPublication(assetId, baseUrl);
    const response = await postOnboardingJsonDetailed("/api/v1/metadata/validate", { metadata });
    const validation = {
      ...(response.body || {}),
      ok: Boolean(response.ok && response.body && response.body.ok)
    };
    state.assetMetadataValidation = validation;
    if (!validation.ok) {
      throw new Error(formatAssetMetadataValidationError(validation));
    }
    return validation;
  }


  function renderPolicyDraftReport(draft) {
    const summaryEl = byId("policyAuditSummary");
    const metaEl = byId("policyAuditMeta");
    const reasoningEl = byId("policyAuditReasoning");
    const recommendationsEl = byId("policyAuditRecommendations");
    if (!summaryEl || !metaEl || !reasoningEl || !recommendationsEl) return;
    if (!draft) {
      summaryEl.textContent = t.policyAuditNoReport;
      metaEl.textContent = "";
      reasoningEl.innerHTML = "";
      recommendationsEl.innerHTML = "";
      return;
    }
    summaryEl.innerHTML = `
      <div class="audit-hero">
        <div>
          <div class="audit-eyebrow">${escapeHtml(t.policyAuditSummaryLabel)}</div>
          <div class="audit-summary-text">${escapeHtml(buildPolicyNarrative(draft))}</div>
        </div>
      </div>
    `;
    metaEl.innerHTML = `
      <div class="audit-meta-grid">
        <div class="audit-meta-card">
          <span class="audit-meta-label">${escapeHtml(t.assetAuditClassificationLabel)}</span>
          <strong>${escapeHtml(draft.classificationLabel || t.notAvailable)}</strong>
        </div>
        <div class="audit-meta-card">
          <span class="audit-meta-label">${escapeHtml(t.policyProfileLabel)}</span>
          <strong>${escapeHtml(draft.policyProfileLabel || draft.policyProfile || t.notAvailable)}</strong>
        </div>
        <div class="audit-meta-card">
          <span class="audit-meta-label">${escapeHtml(t.assetAuditRiskLabel)}</span>
          <strong>${escapeHtml(localizeRisk(draft.risk || "low"))}</strong>
        </div>
        <div class="audit-meta-card">
          <span class="audit-meta-label">${escapeHtml(t.policyClausesLabel)}</span>
          <strong>${escapeHtml(String((draft.permittedActions || []).length + (draft.prohibitedActions || []).length + (draft.duties || []).length))}</strong>
        </div>
      </div>
    `;
    const policyReasoning = buildPolicyReasoning(draft);
    reasoningEl.innerHTML = policyReasoning
      ? `<h4>${escapeHtml(t.assetAuditReasonsLabel)}</h4><p>${escapeHtml(policyReasoning)}</p>`
      : "";
    const clauses = []
      .concat(localizePolicyList(draft.permittedActions || []))
      .concat(localizePolicyList(draft.prohibitedActions || []))
      .concat(localizePolicyList(draft.duties || []));
    recommendationsEl.innerHTML = clauses.length
      ? `<h4>${escapeHtml(t.policyClausesLabel)}</h4><ul class="audit-recommendations">${clauses.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
      : `<h4>${escapeHtml(t.policyClausesLabel)}</h4><p class="muted">${escapeHtml(t.policyAuditNoReport)}</p>`;
  }


  function invalidateAssetMetadataValidation() {
    if (!state.assetMetadataValidation) return;
    state.assetMetadataValidation = null;
  }


  function applySuggestedAssetMetadata(metadata) {
    if (!metadata || typeof metadata !== "object") return;
    setInputIfPresent("assetName", metadata.name || "");
    setInputIfPresent("assetDescription", metadata.description || "");
    setInputIfPresent("assetBaseUrl", metadata.baseUrl || "");
    setInputIfPresent("assetKeywords", metadata.keywords || []);
    setInputIfPresent("assetTheme", metadata.theme || "");
    setInputIfPresent("assetLanguage", metadata.language || "");
    setInputIfPresent("assetLicense", metadata.license || "");
    setInputIfPresent("assetPublisher", metadata.publisher || "");
    setInputIfPresent("assetSpatial", metadata.spatial || "");
    setInputIfPresent("assetTemporalStart", metadata.temporalStart || "");
    setInputIfPresent("assetTemporalEnd", metadata.temporalEnd || "");
    setInputIfPresent("assetFormat", metadata.format || "");
    setInputIfPresent("assetMediaType", metadata.mediaType || "");
    setInputIfPresent("assetAccessRights", metadata.accessRights || "");
    const baseUrl = String(metadata.baseUrl || "").trim();
    if (baseUrl) {
      state.assetDraftUpload = {
        ...(state.assetDraftUpload || {}),
        objectUrl: baseUrl,
        fileName: state.assetDraftUpload && state.assetDraftUpload.fileName ? state.assetDraftUpload.fileName : "",
        contentType: metadata.mediaType || metadata.format || "application/octet-stream"
      };
      setInputIfPresent("policySourceUrl", baseUrl);
    }
  }

  function applySuggestedPolicyDraft(draft) {
    if (!draft || typeof draft !== "object") return;
    setInputIfPresent("policyName", draft.name || "");
    setInputIfPresent("policyLicenseUrl", draft.licenseUrl || "");
    setInputIfPresent("policyPurpose", draft.purpose || "");
    setInputIfPresent("policyGeographicScope", draft.geographicScope || "");
    setInputIfPresent("policyRetentionDays", draft.retentionDays == null ? "" : draft.retentionDays);
    setInputIfPresent("policyInternalUse", localizePolicyValue(draft.internalUse || ""));
    setInputIfPresent("policyAiUsage", localizePolicyValue(draft.aiUsage || ""));
    setInputIfPresent("policyRedistributionMode", localizePolicyValue(draft.redistributionMode || draft.onwardTransfer || ""));
    setInputIfPresent("policyOnwardTransfer", localizePolicyValue(draft.onwardTransfer || ""));
    setInputIfPresent("policyCommercialUse", localizePolicyValue(draft.commercialUse || ""));
    setInputIfPresent("policyAnonymization", localizePolicyValue(draft.anonymizationRequired || ""));
    setInputIfPresent("policyAttributionMode", localizePolicyValue(draft.attributionMode || ""));
    setInputIfPresent("policyNoticeOfChanges", localizePolicyValue(draft.noticeOfChanges || ""));
    setInputIfPresent("policyRateLimitCompliance", localizePolicyValue(draft.rateLimitCompliance || ""));
    setInputIfPresent("policyDataRefreshExpectation", localizePolicyValue(draft.dataRefreshExpectation || ""));
    setInputIfPresent("policyPermittedActions", localizePolicyList(draft.permittedActions || []));
    setInputIfPresent("policyProhibitedActions", localizePolicyList(draft.prohibitedActions || []));
    setInputIfPresent("policyDuties", localizePolicyList(draft.duties || []));
    setInputIfPresent("policySecurityMeasures", draft.securityMeasures || "");
    setInputIfPresent("policyClausesSummary", draft.reviewNotes || "");
  }






  function renderFederatedCatalog(rows) {
    const currentDataspaceId = ((window.DATASPACE_SITE && window.DATASPACE_SITE.config && window.DATASPACE_SITE.config.organisationId) || "").trim();
    const localPolicyMap = state.localPolicyMap instanceof Map ? state.localPolicyMap : new Map();
    const normalizedRows = (Array.isArray(rows) ? rows : [])
      .filter((row, idx, arr) => {
        const key = [
          row.ownerConnectorId || row.providerRaw || row.providerConnectorRawId || "",
          row.assetId || "",
          row.policyId || "",
          row.contractId || ""
        ].join("|");
        return arr.findIndex((candidate) => [
          candidate.ownerConnectorId || candidate.providerRaw || candidate.providerConnectorRawId || "",
          candidate.assetId || "",
          candidate.policyId || "",
          candidate.contractId || ""
        ].join("|") === key) === idx;
      });
    state.federated = normalizedRows.map((row, idx) => ({ rowKey: idx, ...row }));
    renderTable("federatedTable", state.federated, [
      {
        // Delante quien ofrece, detras el nodo donde esta.
        //
        // Iba al reves, y con un conector por participante eso hace que la
        // oferta de una persona salga «asignada» al nodo: se leia el nombre
        // del nodo en grande y un identificador con aspecto de hash debajo.
        // Quien mira el catalogo quiere saber con quien va a negociar.
        label: t.tableProvider,
        render: (r) => {
          const quien = escapeHtml(r.providerLabel || r.provider || "");
          const donde = escapeHtml(r.providerDataspaceName || r.providerDataspaceId || "");
          if (!donde || donde === quien) return quien;
          return `${quien}<br><span class="muted">${donde}</span>`;
        }
      },
      { label: t.tableAsset, render: (r) => `${r.assetId}<br><span class="muted">${r.assetName}</span>` },
      { label: t.tableAssetDescription, render: (r) => r.assetDescription || "" },
      { label: t.tableMetadata, render: (r) => renderAssetSemanticSummary(r) },
      { label: t.tablePolicy, render: (r) => renderCatalogPolicyCell(r, localPolicyMap) },
      {
        label: t.tableAction,
        render: (r) => {
          // Sin caso aparte para la oferta de este nodo.
          //
          // Aqui se devolvia «Activo propio» desactivado para toda fila local,
          // y eso rompe el criterio 6 de la especificacion, que pide publicar
          // un producto y, **desde la vista de consumo del mismo nodo**,
          // negociar su contrato y descargar el dato. En un nodo con varios
          // participantes ademas dejaba fuera a quien acababa de darse de
          // alta: la oferta del nodo le salia como suya y no podia pedir nada.
          //
          // Lo que decide si se puede descargar sigue siendo lo mismo que
          // antes: que haya una negociacion cerrada. Eso no se ha tocado.
          const remoteDataspace = currentDataspaceId && r.providerDataspaceId && r.providerDataspaceId !== currentDataspaceId;
          const completed = state.negotiations.find(
            (n) =>
              isNegotiationCompleted(n.status) &&
              (n.providerConnectorId === r.providerRaw || n.providerConnectorId === r.provider) &&
              n.assetId === r.assetId
          );
          const isNegotiated = Boolean(
            completed ||
            (state.negotiations || []).find((n) => isNegotiationCompleted(n.status) && n.assetId === r.assetId) ||
            r.negotiated ||
            state.negotiatedFederatedKeys.has(
              federatedNegotiationKey(r.providerDataspaceId, r.providerRaw || r.provider, r.assetId)
            ) ||
            state.negotiatedFederatedKeys.has(
              persistedNegotiationKey(r.providerDataspaceId || currentDataspaceId, r.providerRaw || r.provider, r.assetId)
            ) ||
            state.negotiatedFederatedKeys.has(
              persistedNegotiationKey(r.providerDataspaceId || currentDataspaceId, r.provider || r.providerRaw, r.assetId)
            ) ||
            state.negotiatedFederatedKeys.has(
              persistedNegotiationAssetKey(r.assetId)
            )
          );
          const isPending = state.pendingNegotiationKeys.has(
            remoteDataspace
              ? federatedNegotiationKey(r.providerDataspaceId, r.providerRaw || r.provider, r.assetId)
              : localNegotiationKey(r.providerRaw || r.provider, r.assetId)
          );
          // Aqui habia un segundo camino, «de gobernanza», para las filas de
          // otro nodo: iba a `/api/governance`, que no existe. Y ademas lo
          // tomaban **todas** las filas, porque el identificador que trae el
          // catalogo consolidado es el del conector y nunca coincide con el
          // de la organizacion. Un solo camino, el que funciona: este nodo
          // negocia contra el conector del nodo proveedor.
          if (isNegotiated && features.allowDownload) {
            if (!r.assetId) {
              return `<span class="muted">${t.notAvailable}</span>`;
            }
            const fileName = `${r.assetId || "asset"}-data`;
            return `<button class="secondary" onclick='window.downloadNegotiatedAsset(${JSON.stringify(r.providerRaw || r.provider)}, ${JSON.stringify(r.assetId)}, ${JSON.stringify(fileName)})'>${t.download}</button>`;
          }
          if (isPending) {
            return `<button class="secondary" disabled>${t.pending}</button>`;
          }
          if (!features.allowNegotiate) {
            return `<button class="secondary" disabled>${t.pending}</button>`;
          }
          return `<button class="secondary" onclick='window.requestNegotiation(${JSON.stringify(r.providerDataspaceId || "")}, ${JSON.stringify(r.providerRaw || r.provider)}, ${JSON.stringify(r.assetId)}, ${JSON.stringify(r.policyId)})'>${t.acceptPolicy}</button>`;
        }
      }
    ]);
  }

  async function reloadFederatedCatalog() {
    if (!features.federated) return;
    const selectedLanguage = lang === "en" ? "en" : "es";
    const currentDataspaceId = ((window.DATASPACE_SITE && window.DATASPACE_SITE.config && window.DATASPACE_SITE.config.organisationId) || "").trim();
    const federatedRows = [];
    let localPolicyMap = new Map();

    // El catálogo consolidado, pedido a la API.
    //
    // Antes esto consultaba el SPARQL de Fuseki directamente, con sus
    // credenciales de administración metidas en la página mediante
    // btoa("admin:"). Dos problemas: nadie enruta /fuseki —y no debe,
    // porque publicarlo es exactamente lo que ODS_SPARQL_PUBLIC=false
    // evita—, y esas credenciales llegaban al navegador de cualquiera que
    // abriese la consola.
    //
    // Ahora la consulta la hace el servidor y aquí sólo llegan filas.
    const loadLocalFusekiCatalog = async () => {
      const url = cfg.consolidatedCatalogUrl || "/api/v1/nodes/catalog";
      const res = await fetch(url, { headers: { Accept: "application/json" } });
      if (!res.ok) {
        throw new Error(`${t.federatedCatalogError || "catálogo"}: ${res.status}`);
      }
      const data = await res.json();
      if (data.ok === false) {
        // El catálogo consolidado nunca bloquea: se dice y se sigue con la
        // vista local.
        console.warn("catálogo consolidado no disponible:", data.detail || data.error);
        return [];
      }
      // Los destinos de negociacion salian del catalogo de gobernanza. Sin
      // el, `requestNegotiation` no encontraba la URL del nodo proveedor y
      // fallaba con «proveedor no configurado». El catalogo consolidado ya
      // trae esa direccion: es la del registro de nodos conocidos.
      upsertNegotiationTargets((data.items || [])
        .filter((r) => r.connector && (r.local || r.baseUrl))
        .map((r) => ({
          providerConnectorId: r.connector || "",
          providerConnectorRawId: r.connector || "",
          // El conector que la ofrece, no la etiqueta del nodo: la celda ya
        // enseña el nodo arriba, y con un conector por participante lo que
        // falta saber es **quien** de ese nodo la ofrece.
        providerLabel: r.connector || r.nodeLabel || "",
          // Los conectores de este nodo se alcanzan por el paso local, sea
          // cual sea el participante: un nodo tiene un conector por
          // participante y todos viven en el mismo sitio. Antes solo entraban
          // los remotos, asi que negociar con un vecino del propio nodo
          // fallaba con «proveedor no configurado».
          // A **su** conector, nombrado. Cada participante tiene su
          // instancia: apuntar al paso a secas lleva al de quien mira, y
          // negociar o descargar lo de un vecino es hablar con el suyo.
          providerBaseUrl: r.local
            ? `${cfg.baseUrl}/${r.connector}`
            : (r.baseUrl || ""),
          providerDataspaceId: r.local ? currentDataspaceId : (r.connector || "")
        })));
      return (data.items || []).map((r) => ({
        provider: r.connector || "",
        providerRaw: r.connector || "",
        // El nombre de quien la ofrece, que trae el catalogo; el
        // identificador del conector solo si no se sabe el nombre.
        providerLabel: r.connectorLabel || r.connector || "",
        // El espacio de datos, no el conector. Aqui se ponia `r.connector`,
        // y como nunca coincide con el identificador de la organizacion toda
        // fila se juzgaba «de otro espacio de datos»: ni siquiera los activos
        // propios se reconocian como propios.
        providerDataspaceId: r.local ? currentDataspaceId : (r.connector || ""),
        providerDataspaceName: r.nodeLabel || r.connector || "",
        contractId: r.contractId || "",
        assetId: r.assetId || "",
        assetName: r.name || "",
        assetDescription: r.description || "",
        assetLanguage: "",
        publisher: r.publisher || "",
        licenseUrl: r.license || "",
        accessRights: r.accessRights || "",
        topicCode: r.theme || "",
        keywords: r.keywords || "",
        mediaType: r.mediaType || "",
        deliveryMode: r.deliveryMode || "",
        policyId: r.policyId || "",
        baseUrl: r.baseUrl || "",
        local: Boolean(r.local),
        catalogSource: r.local ? "nodo-local" : "nodo-remoto"
      }));
    };

    try {
      const policies = await localApi("/management/v3/policydefinitions");
      state.policies = policies;
      localPolicyMap = buildPolicyDefinitionMap(policies);
    } catch (_err) {
      localPolicyMap = buildPolicyDefinitionMap(state.policies);
    }
    state.localPolicyMap = localPolicyMap;

    try {
      federatedRows.push(...await loadLocalFusekiCatalog());
    } catch (err) {
      if (federatedRows.length === 0) {
        throw err;
      }
    }

    const deduped = [];
    const seen = new Set();
    for (const row of federatedRows) {
      // Governance is loaded before the local Fuseki fallback. Treat the
      // dataspace/connector/asset tuple as the catalog identity so that the
      // same offer is not rendered twice merely because one representation
      // carries additional policy or contract metadata.
      const key = [
        row.providerDataspaceId || "",
        row.providerRaw || row.provider || "",
        row.assetId || ""
      ].join("|");
      if (seen.has(key)) continue;
      seen.add(key);
      deduped.push(row);
    }
    renderFederatedCatalog(deduped);
  }

  async function createAsset(e) {
    e.preventDefault();
    const baseUrlCandidate = readInputValue("assetBaseUrl", "").trim();
    if (!baseUrlCandidate) {
      throw new Error(t.assetDocumentMissing);
    }
    const assetId = uniqueId(`asset-${cfg.id}`);
    const name = readInputValue("assetName");
    const description = readInputValue("assetDescription");
    if (!name.trim() || !description.trim()) {
      throw new Error(t.assetMetadataIncomplete);
    }
    const baseUrl = readInputValue("assetBaseUrl", (state.assetDraftUpload && state.assetDraftUpload.objectUrl) || "");
    const metadata = currentAssetMetadataForPublication(assetId, baseUrl);
    await validateAssetMetadataBeforePublish(assetId, baseUrl);
    const payload = {
      "@id": assetId,
      properties: metadata,
      dataAddress: {
        type: "HttpData",
        baseUrl
      }
    };
    await localApi("/management/v3/assets", { method: "POST", body: JSON.stringify(payload) });
    setStatus(`${t.assetCreated}: ${assetId}`);
    await reloadLocalCatalog();
  }

  async function createPolicy(e) {
    e.preventDefault();
    const sourceUrl = readInputValue("policySourceUrl", "").trim();
    if (!sourceUrl) {
      throw new Error(t.policyDocumentMissing);
    }
    const permittedActions = canonicalizePolicyList(parseCsvList(readInputValue("policyPermittedActions")));
    const prohibitedActions = canonicalizePolicyList(parseCsvList(readInputValue("policyProhibitedActions")));
    const duties = canonicalizePolicyList(parseCsvList(readInputValue("policyDuties")));
    if (!readInputValue("policyName").trim() || permittedActions.length === 0) {
      throw new Error(t.policyDraftIncomplete);
    }
    const policyId = uniqueId(`policy-${cfg.id}`);
    const payload = {
      "@id": policyId,
      policy: {
        "@context": { odrl: "http://www.w3.org/ns/odrl/2/" },
        "@type": "Set",
        name: byId("policyName").value.trim(),
        licenseUrl: byId("policyLicenseUrl").value.trim(),
        sourceUrl,
        purpose: readInputValue("policyPurpose"),
        geographicScope: readInputValue("policyGeographicScope"),
        retentionDays: Number(readInputValue("policyRetentionDays", "0")) || 0,
        internalUse: canonicalizePolicyValue(readInputValue("policyInternalUse")),
        aiUsage: canonicalizePolicyValue(readInputValue("policyAiUsage")),
        redistributionMode: canonicalizePolicyValue(readInputValue("policyRedistributionMode")),
        onwardTransfer: canonicalizePolicyValue(readInputValue("policyOnwardTransfer")),
        commercialUse: canonicalizePolicyValue(readInputValue("policyCommercialUse")),
        anonymizationRequired: canonicalizePolicyValue(readInputValue("policyAnonymization")),
        attributionMode: canonicalizePolicyValue(readInputValue("policyAttributionMode")),
        noticeOfChanges: canonicalizePolicyValue(readInputValue("policyNoticeOfChanges")),
        rateLimitCompliance: canonicalizePolicyValue(readInputValue("policyRateLimitCompliance")),
        dataRefreshExpectation: canonicalizePolicyValue(readInputValue("policyDataRefreshExpectation")),
        securityMeasures: readInputValue("policySecurityMeasures"),
        reviewNotes: readInputValue("policyClausesSummary"),
        classificationKey: readInputValue("policyClassificationKey", ""),
        policyProfile: "ods-odrl-1.0.0",
        permission: permittedActions.map((action) => ({ action })),
        prohibition: prohibitedActions.map((action) => ({ action })),
        duty: duties.map((action) => ({ action }))
      }
    };
    await localApi("/management/v3/policydefinitions", { method: "POST", body: JSON.stringify(payload) });
    setStatus(`${t.policyCreated}: ${policyId}`);
    await reloadLocalCatalog();
  }

  async function createContract(e) {
    e.preventDefault();
    const contractId = uniqueId(`contract-${cfg.id}`);
    const policyId = byId("contractPolicyIdSelect") ? byId("contractPolicyIdSelect").value.trim() : byId("contractPolicyId").value.trim();
    const assetId = byId("contractAssetIdSelect") ? byId("contractAssetIdSelect").value.trim() : byId("contractAssetId").value.trim();
    // Aqui se pedia antes a `/api/v1/edc/bridge/payloads` que compusiera la
    // definicion. Esa ruta es del proyecto de origen y no existe en este
    // producto: contestaba 404 en cada contrato, se registraba el aviso en la
    // consola del navegador y se usaba igualmente la definicion directa. La
    // directa es la unica que hubo nunca.
    const payload = fallbackContractDefinition(contractId, policyId, assetId);
    await localApi("/management/v3/contractdefinitions", { method: "POST", body: JSON.stringify(payload) });
    setStatus(`${t.contractCreated}: ${contractId}`);
    // Federar lo hace el nodo al ver nacer el contrato, no esta pagina: asi
    // vale igual para quien lo cree por la API.
    //
    // Aqui se recarga tambien el catalogo del espacio de datos, para que la
    // oferta aparezca sin ir a buscarla. Sin esto, quien acababa de crear el
    // contrato no veia nada cambiar y volvia a pulsar.
    await reloadLocalCatalog();
    if (features.federated) {
      await reloadFederatedCatalog().catch(() => {});
      // Y otra vez pasada la ventana del freno del nodo. Si el contrato cayo
      // dentro de ella, la oferta entra en el grafo unos segundos despues y sin
      // esto habria que recargar a mano -- que es cuando la gente da por hecho
      // que no ha salido y vuelve a pulsar.
      window.setTimeout(() => {
        reloadFederatedCatalog().catch(() => {});
      }, 7000);
    }
  }

  /** Pide al nodo que vuelva a leer los catalogos. No bloquea si falla. */
  async function sincronizarCatalogo() {
    try {
      const token = await ensureAccessToken();
      await fetch("/api/v1/nodes/sync", {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {}
      });
    } catch (err) {
      console.warn("no se pudo sincronizar el catalogo", err);
    }
  }

  window.requestNegotiation = async function (providerDataspaceId, provider, assetId, policyId) {
    if (typeof policyId === "undefined") {
      policyId = assetId;
      assetId = provider;
      provider = providerDataspaceId;
      providerDataspaceId = "";
    }
    try {
      setStatus(`${t.negotiationStarting}: ${assetId || ""}`);
      const pendingKey = localNegotiationKey(provider, assetId);
      state.pendingNegotiationKeys.add(pendingKey);
      renderFederatedCatalog(state.federated);
      const currentDataspaceId = ((window.DATASPACE_SITE && window.DATASPACE_SITE.config && window.DATASPACE_SITE.config.organisationId) || "").trim();
      if (!provider || !assetId || !policyId) {
        throw new Error(t.incompleteNegotiationData);
      }
      // El proveedor puede ser este mismo nodo. Aqui se rechazaba con «no se
      // negocian assets propios», que impedia el recorrido que pide el
      // criterio 6: publicar y negociar el contrato desde la vista de consumo
      // del propio nodo. La negociacion se registra igual -- consumidor y
      // proveedor -- y es lo que despues permite descargar.
      const providerTarget = provider === cfg.id
        ? { id: cfg.id, baseUrl: cfg.baseUrl, label: cfg.label || cfg.id }
        : (cfg.negotiationTargets || []).find((t) => {
            if (t.id !== provider) return false;
            const targetDataspaceId = String(t.dataspaceId || "").trim();
            const requestedDataspaceId = String(providerDataspaceId || "").trim();
            return !requestedDataspaceId || targetDataspaceId === requestedDataspaceId;
          });
      if (!providerTarget) {
        throw new Error(`${t.providerNotConfigured}: ${provider}`);
      }

      const negotiationId = `neg-${Date.now()}`;
      const basePayload = {
        "@id": negotiationId,
        consumerConnectorId: cfg.id,
        providerConnectorId: provider,
        assetId,
        policyId
      };
      addTransferTrace(t.traceNegotiationStarted, {
        negotiationId,
        consumerConnectorId: cfg.id,
        providerConnectorId: provider,
        assetId,
        policyId,
        tokenMasked: maskToken(state.accessToken)
      });
      // 1) Registrar en el consumidor como pendiente.
      const consumerResponse = await localApi("/management/v3/negotiations", {
        method: "POST",
        body: JSON.stringify({ ...basePayload, status: "REQUESTED" })
      });
      addTransferTrace(t.traceNegotiationConsumerRequested, {
        negotiationId,
        status: "REQUESTED",
        response: consumerResponse || {}
      });

      // 2 y 3) La solicitud al proveedor y su cierre.
      //
      // Cuando el proveedor es este mismo nodo, el paso 1 ya la ha registrado
      // en el conector que hace falta: repetirla contra la misma direccion
      // escribiria el mismo registro dos veces mas y las trazas dirian que se
      // hablo con otro nodo cuando no lo hubo.
      const proveedorEsEsteNodo = providerTarget.baseUrl === cfg.baseUrl;
      let providerResponse = null;
      let providerCompleteResponse = null;
      if (!proveedorEsEsteNodo) {
        providerResponse = await connectorFetch(providerTarget.baseUrl, "/management/v3/negotiations", {
          method: "POST",
          body: JSON.stringify({ ...basePayload, status: "REQUESTED" })
        });
        addTransferTrace(t.traceNegotiationProviderRequested, {
          negotiationId,
          providerConnectorId: provider,
          providerBaseUrl: providerTarget.baseUrl,
          response: providerResponse || {}
        });

        // Cerrarla tambien en el proveedor, para que la descarga que se valida
        // alli reconozca el acuerdo.
        providerCompleteResponse = await connectorFetch(providerTarget.baseUrl, "/management/v3/negotiations", {
          method: "POST",
          body: JSON.stringify({ ...basePayload, status: "COMPLETED" })
        });
      }

      // 4) Reflejar la misma negociación completada en el consumidor.
      const completeResponse = await localApi("/management/v3/negotiations", {
        method: "POST",
        body: JSON.stringify({ ...basePayload, status: "COMPLETED" })
      });
      addTransferTrace(t.traceNegotiationCompleted, {
        negotiationId,
        finalStatus: "COMPLETED",
        providerResponse: providerCompleteResponse || {},
        response: completeResponse || {}
      });
      await publishAuditEvent(
        "local-negotiation-completed",
        {
          assetId,
          policyId,
          consumerDataspaceId: currentDataspaceId || "",
          consumerConnectorId: cfg.id,
          providerConnectorId: provider,
          providerDataspaceId: currentDataspaceId || "",
          negotiationId
        },
        "success",
        {
          ...catalogEvidence(currentDataspaceId || "", provider, assetId, policyId),
          providerResponse: providerCompleteResponse || {},
          consumerResponse: completeResponse || {}
        }
      );
      await loadParticipantAudit(true).catch(() => {});

      state.pendingNegotiationKeys.delete(pendingKey);
      addNegotiationPersistenceAliases(providerDataspaceId || currentDataspaceId, provider, assetId);
      savePersistedNegotiations();
      state.negotiations.unshift({
        id: negotiationId,
        consumerConnectorId: cfg.id,
        providerConnectorId: provider,
        assetId,
        policyId,
        status: "COMPLETED"
      });
      renderFederatedCatalog(state.federated);
      setStatus(`${t.negotiationCompleted} ${assetId} (${provider})`);
      if (features.myAssets) {
        await reloadLocalCatalog();
      } else {
        await reloadNegotiationsOnly();
        await reloadFederatedCatalog();
      }
    } catch (err) {
      state.pendingNegotiationKeys.delete(localNegotiationKey(provider, assetId));
      addTransferTrace(t.traceStepError, {
        operation: "negotiation",
        message: err.message
      }, false);
      renderFederatedCatalog(state.federated);
      setStatus(`${t.negotiationError}: ${err.message}`, true);
      if (features.myAssets) {
        await reloadLocalCatalog().catch(() => {});
      } else {
        await reloadNegotiationsOnly().catch(() => {});
        await reloadFederatedCatalog().catch(() => {});
      }
    }
  };


  window.downloadNegotiatedAsset = async function (provider, assetId, fileName) {
    try {
      if (!assetId) {
        throw new Error(t.notAvailable);
      }
      const connectorBaseUrl = getConnectorBaseUrlByProvider(provider);
      const negotiation = findMatchingNegotiation(provider, assetId);
      const transferId = negotiation ? negotiation.id || negotiation["@id"] || "" : "";
      addTransferTrace(t.traceDownloadStarted, {
        transferId,
        providerConnectorId: provider,
        assetId,
        endpoint: `${connectorBaseUrl}/management/v3/assets/${encodeURIComponent(assetId)}/download`,
        tokenMasked: maskToken(state.accessToken)
      });

      const response = await connectorFetchBlob(
        connectorBaseUrl,
        `/management/v3/assets/${encodeURIComponent(assetId)}/download`,
        { method: "GET" }
      );
      const fallbackName = normalizeFileName(fileName || `${assetId}-data`);
      const contentDisposition = response.headers.get("Content-Disposition") || "";
      const resolvedName = extractFileNameFromContentDisposition(contentDisposition, fallbackName);
      const blob = await response.blob();
      triggerBlobDownload(blob, resolvedName);
      addTransferTrace(t.traceDownloadCompleted, {
        transferId,
        providerConnectorId: provider,
        assetId,
        fileName: resolvedName,
        contentType: response.headers.get("Content-Type") || "",
        contentLength: response.headers.get("Content-Length") || "",
        status: response.status
      });
      const auditResult = await publishAuditEvent(
        "asset-download-completed",
        {
          assetId,
          consumerDataspaceId: ((window.DATASPACE_SITE && window.DATASPACE_SITE.config && window.DATASPACE_SITE.config.organisationId) || "").trim(),
          consumerConnectorId: cfg.id,
          providerConnectorId: provider,
          providerDataspaceId: ((window.DATASPACE_SITE && window.DATASPACE_SITE.config && window.DATASPACE_SITE.config.organisationId) || "").trim(),
          transferId
        },
        "success",
        {
          ...catalogEvidence(((window.DATASPACE_SITE && window.DATASPACE_SITE.config && window.DATASPACE_SITE.config.organisationId) || "").trim(), provider, assetId),
          fileName: resolvedName,
          contentType: response.headers.get("Content-Type") || "",
          contentLength: response.headers.get("Content-Length") || "",
          httpStatus: response.status
        }
      );
      if (auditResult && auditResult.auditTraceId) {
        await loadParticipantAudit(true).catch(() => {});
      }
      setStatus(t.downloadStarted);
    } catch (err) {
      addTransferTrace(t.traceStepError, {
        operation: "download",
        providerConnectorId: provider,
        assetId,
        message: err.message
      }, false);
      setStatus(`${t.downloadError}: ${err.message}`, true);
    }
  };




  async function refreshAll() {
    if (features.federated) {
      await reloadNegotiationsOnly().catch(() => {
        state.negotiations = [];
      });
      await reloadFederatedCatalog();
    }
    if (features.myAssets) {
      await reloadLocalCatalog();
    }
    setStatus(t.catalogsLoaded);
  }

  const assetForm = byId("assetForm");
  if (assetForm && features.create) {
    assetForm.addEventListener("submit", (e) => createAsset(e).catch((err) => setStatus(err.message, true)));
  }
  const assetBaseUrlInput = byId("assetBaseUrl");
  if (assetBaseUrlInput) {
    assetBaseUrlInput.addEventListener("input", () => {
      const current = String(assetBaseUrlInput.value || "").trim();
      // Cambiar la dirección invalida la validación de metadatos: las formas
      // SHACL se comprobaron contra la anterior.
      invalidateAssetMetadataValidation();
      // La política se hace sobre el mismo recurso, así que se arrastra.
      setInputIfPresent("policySourceUrl", current);
    });
  }
  [
    "assetName",
    "assetDescription",
    "assetIdentifier",
    "assetKeywords",
    "assetTheme",
    "assetLanguage",
    "assetLicense",
    "assetPublisher",
    "assetSpatial",
    "assetTemporalStart",
    "assetTemporalEnd",
    "assetFormat",
    "assetMediaType",
    "assetAccessRights"
  ].forEach((id) => {
    const el = byId(id);
    if (el) {
      el.addEventListener("input", () => {
        invalidateAssetMetadataValidation();
      });
    }
  });
  const policyForm = byId("policyForm");
  if (policyForm && features.create) {
    policyForm.addEventListener("submit", (e) => createPolicy(e).catch((err) => setStatus(err.message, true)));
  }
  [
    "policyName",
    "policyPermittedActions",
    "policyProhibitedActions",
    "policyDuties"
  ].forEach((id) => {
    const el = byId(id);
    if (el) {
      el.addEventListener("input", () => {
      });
    }
  });
  renderPolicyDraftReport(null);
  const contractForm = byId("contractForm");
  if (contractForm && features.create) {
    contractForm.addEventListener("submit", (e) => createContract(e).catch((err) => setStatus(err.message, true)));
  }
  const reloadBtn = byId("reloadBtn");
  if (reloadBtn) {
    reloadBtn.addEventListener("click", () => refreshAll().catch((err) => setStatus(err.message, true)));
  }
  const reloadFederatedBtn = byId("reloadFederatedBtn");
  if (reloadFederatedBtn && features.federated) {
    // Sincroniza antes de mirar: es el boton que se pulsa esperando ver lo que
    // hay **ahora**, y sin esto ensenaba lo ultimo que el federador hubiera
    // traido, hasta cinco minutos viejo.
    reloadFederatedBtn.addEventListener("click", () =>
      sincronizarCatalogo()
        .then(() => reloadNegotiationsOnly().catch(() => {
          state.negotiations = [];
        }))
        .then(() => reloadFederatedCatalog())
        .then(() => setStatus(t.federatedReloaded))
        .catch((err) => setStatus(err.message, true))
    );
  }

  const traceNodes = getTraceNodes();
  if (traceNodes.clearBtn) {
    traceNodes.clearBtn.addEventListener("click", () => {
      state.transferTrace = [];
      renderTransferTrace();
    });
  }
  renderTransferTrace();
  addTransferTrace(t.traceReady, { connectorId: cfg.id });
  loadPersistedNegotiations();

  initOperationTabs();
  initKnownNodes();
  const participantAuditNodes = getParticipantAuditNodes();
  if (participantAuditNodes.reloadBtn) {
    participantAuditNodes.reloadBtn.addEventListener("click", () => {
      loadParticipantAudit(true).catch((err) => setStatus(err.message, true));
    });
  }

  initAuth()
    .then(() => refreshAll())
    .then(() => loadParticipantAudit())
    .catch((err) => setStatus(err.message, true));
})();
