(function () {
  const cfg = window.CONNECTOR_CONFIG || {};
  if (cfg.id !== "connector-1") return;

  const mainBtn = document.getElementById("tabMainBtn");
  const auditBtn = document.getElementById("tabAuditBtn");
  const usersBtn = document.getElementById("tabUsersBtn");
  const mainPanel = document.getElementById("tabMainPanel");
  const auditPanel = document.getElementById("tabAuditPanel");
  const usersPanel = document.getElementById("tabUsersPanel");

  const reloadAuditBtn = document.getElementById("reloadConnectorAuditBtn");
  const auditStatusEl = document.getElementById("connectorAuditStatus");
  const auditTable = document.getElementById("connectorAuditTable");

  const reloadDirectoryBtn = document.getElementById("reloadConnectorDirectoryBtn");
  const directoryStatusEl = document.getElementById("connectorDirectoryStatus");
  const directoryTable = document.getElementById("connectorDirectoryTable");

  const reloadRequestsBtn = document.getElementById("reloadConnectorRequestsBtn");
  const requestsStatusEl = document.getElementById("connectorRequestsStatus");
  const requestsTable = document.getElementById("connectorRequestsTable");

  if (!mainBtn || !auditBtn || !usersBtn || !mainPanel || !auditPanel || !usersPanel || !reloadAuditBtn || !auditStatusEl || !auditTable || !reloadDirectoryBtn || !directoryStatusEl || !directoryTable || !reloadRequestsBtn || !requestsStatusEl || !requestsTable) {
    return;
  }

  const isEn = String(cfg.lang || document.documentElement.lang || "es").toLowerCase().startsWith("en");
  const labels = isEn
    ? {
        tabMain: "Operation",
        tabAudit: "Audit",
        tabUsers: "Users and requests",
        auditConsumerDs: "Consumer dataspace",
        auditConsumer: "Consumer connector",
        auditProviderDs: "Provider dataspace",
        auditProvider: "Provider connector",
        auditEvent: "Event",
        auditAsset: "Asset / resource",
        auditSimpl: "SIMPL / Registry",
        auditSignature: "Signature",
        auditTime: "Time",
        auditLoading: "Loading transactions...",
        auditLoaded: "Transaction log updated",
        auditNoRows: "No transactions found",
        auditError: "Failed to load transactions",
        directoryConnectorId: "Connector ID",
        directoryName: "Name",
        directoryLastName: "Last name",
        directoryEmail: "Email",
        directoryType: "Profile",
        directoryStatus: "Status",
        directoryLoading: "Loading approved connectors...",
        directoryLoaded: "Approved connector list updated",
        directoryNoRows: "No approved connectors found",
        directoryError: "Failed to load connectors",
        requestsId: "Request ID",
        requestsName: "Name",
        requestsEmail: "Email",
        requestsProfile: "Requested profile",
        requestsCreatedAt: "Created at",
        requestsStatus: "Status",
        requestsAction: "Action",
        requestsLoading: "Loading pending requests...",
        requestsLoaded: "Pending requests updated",
        requestsNoRows: "No pending requests",
        requestsError: "Failed to load pending requests",
        approve: "Approve",
        deny: "Deny",
        denied: "Denied",
        approved: "Approved",
        pending: "Pending",
        reviewerReasonDenied: "Denied from connector-1",
        authError: "Authentication required"
      }
    : {
        tabMain: "Operacion",
        tabAudit: "Auditoria",
        tabUsers: "Usuarios y solicitudes",
        auditConsumerDs: "Espacio consumidor",
        auditConsumer: "Conector consumidor",
        auditProviderDs: "Espacio proveedor",
        auditProvider: "Conector proveedor",
        auditEvent: "Evento",
        auditAsset: "Asset / recurso",
        auditSimpl: "SIMPL / Registro",
        auditSignature: "Firma",
        auditTime: "Hora",
        auditLoading: "Cargando transacciones...",
        auditLoaded: "Registro de transacciones actualizado",
        auditNoRows: "No se encontraron transacciones",
        auditError: "No se pudo cargar transacciones",
        directoryConnectorId: "Connector ID",
        directoryName: "Nombre",
        directoryLastName: "Apellidos",
        directoryEmail: "Correo",
        directoryType: "Perfil",
        directoryStatus: "Estado",
        directoryLoading: "Cargando conectores aprobados...",
        directoryLoaded: "Listado de conectores aprobados actualizado",
        directoryNoRows: "No se encontraron conectores aprobados",
        directoryError: "No se pudo cargar conectores",
        requestsId: "Solicitud",
        requestsName: "Nombre",
        requestsEmail: "Correo",
        requestsProfile: "Perfil solicitado",
        requestsCreatedAt: "Creada",
        requestsStatus: "Estado",
        requestsAction: "Accion",
        requestsLoading: "Cargando solicitudes pendientes...",
        requestsLoaded: "Solicitudes pendientes actualizadas",
        requestsNoRows: "No hay solicitudes pendientes",
        requestsError: "No se pudieron cargar las solicitudes pendientes",
        approve: "Aprobar",
        deny: "Denegar",
        denied: "Denegada",
        approved: "Aprobada",
        pending: "Pendiente",
        reviewerReasonDenied: "Denegada desde connector-1",
        authError: "Se requiere autenticacion"
      };

  const roleModeLabels = isEn
    ? { consumer: "Consumer", provider: "Provider", both: "Provider and consumer" }
    : { consumer: "Consumidor", provider: "Proveedor", both: "Proveedor y consumidor" };

  const state = {
    accessToken: "",
    loadedAuditOnce: false,
    loadedDirectoryOnce: false,
    loadedRequestsOnce: false,
    requests: [],
    connectors: []
  };

  function setPanel(active) {
    const isMain = active === "main";
    const isAudit = active === "audit";
    const isUsers = active === "users";

    mainBtn.classList.toggle("is-active", isMain);
    auditBtn.classList.toggle("is-active", isAudit);
    usersBtn.classList.toggle("is-active", isUsers);

    mainBtn.setAttribute("aria-selected", isMain ? "true" : "false");
    auditBtn.setAttribute("aria-selected", isAudit ? "true" : "false");
    usersBtn.setAttribute("aria-selected", isUsers ? "true" : "false");

    mainPanel.classList.toggle("is-active", isMain);
    auditPanel.classList.toggle("is-active", isAudit);
    usersPanel.classList.toggle("is-active", isUsers);

    if (isMain) mainPanel.removeAttribute("hidden"); else mainPanel.setAttribute("hidden", "hidden");
    if (isAudit) auditPanel.removeAttribute("hidden"); else auditPanel.setAttribute("hidden", "hidden");
    if (isUsers) usersPanel.removeAttribute("hidden"); else usersPanel.setAttribute("hidden", "hidden");
  }

  function setStatus(el, message, isError) {
    el.textContent = message;
    el.classList.remove("status-ok", "status-error");
    el.classList.add(isError ? "status-error" : "status-ok");
  }

  function normalizeStatus(value) {
    return String(value || "UNKNOWN").trim().toUpperCase() || "UNKNOWN";
  }

  function simplifyResource(resource) {
    if (!resource) return "-";
    if (typeof resource === "string") return resource;
    const parts = [];
    if (resource.assetId) parts.push(resource.assetId);
    if (resource.negotiationId) parts.push(`neg=${resource.negotiationId}`);
    if (resource.transferId) parts.push(`transfer=${resource.transferId}`);
    return parts.join(" · ") || JSON.stringify(resource);
  }

  function extractAuditParties(trace) {
    const event = (trace && trace.event) || {};
    const resource = event.resource || {};
    const evidence = event.evidence || {};
    const fallbackDataspace = trace.dataspaceId || event.dataspaceId || "";
    return {
      consumerDataspaceId: resource.consumerDataspaceId || evidence.consumerDataspaceId || fallbackDataspace || "-",
      consumerConnectorId: resource.consumerConnectorId || evidence.consumerConnectorId || evidence.connectorId || "-",
      providerDataspaceId: resource.providerDataspaceId || evidence.providerDataspaceId || fallbackDataspace || "-",
      providerConnectorId: resource.providerConnectorId || evidence.providerConnectorId || "-",
    };
  }

  function formatDateTime(value) {
    if (!value) return "-";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return new Intl.DateTimeFormat(isEn ? "en-GB" : "es-ES", {
      dateStyle: "short",
      timeStyle: "medium",
    }).format(date);
  }

  function escapeHtml(value) {
    return String(value || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function renderTable(table, rows, headers, emptyText) {
    table.innerHTML = "";

    const thead = document.createElement("thead");
    const trHead = document.createElement("tr");
    headers.forEach((header) => {
      const th = document.createElement("th");
      th.textContent = header;
      trHead.appendChild(th);
    });
    thead.appendChild(trHead);
    table.appendChild(thead);

    const tbody = document.createElement("tbody");
    if (!rows.length) {
      const tr = document.createElement("tr");
      const td = document.createElement("td");
      td.colSpan = headers.length;
      td.textContent = emptyText;
      tr.appendChild(td);
      tbody.appendChild(tr);
      table.appendChild(tbody);
      return;
    }

    rows.forEach((row) => {
      const tr = document.createElement("tr");
      row.forEach((value) => {
        const td = document.createElement("td");
        if (value && typeof value === "object" && value.html) {
          td.innerHTML = value.html;
        } else {
          td.textContent = value;
        }
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
  }

  function sleep(ms) {
    return new Promise((resolve) => window.setTimeout(resolve, ms));
  }

  function syncAccessToken() {
    const token = window.__DATASPACE_ID_TOKEN || window.__DATASPACE_ACCESS_TOKEN || "";
    if (token && token !== state.accessToken) state.accessToken = token;
    return state.accessToken;
  }

  async function ensureAccessToken() {
    if (typeof window.__DATASPACE_ENSURE_FRESH_TOKEN === "function") {
      try {
        const refreshedToken = await window.__DATASPACE_ENSURE_FRESH_TOKEN();
        if (refreshedToken) {
          state.accessToken = refreshedToken;
          return;
        }
      } catch (_err) {
        // fallback below
      }
    }
    if (syncAccessToken()) return;
    for (let i = 0; i < 15; i += 1) {
      if (syncAccessToken()) return;
      await sleep(200);
    }
    throw new Error(labels.authError);
  }

  async function fetchAuthedJson(url, options = {}) {
    await ensureAccessToken();
    const accessToken = syncAccessToken();
    const response = await fetch(url, {
      method: options.method || "GET",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
        Accept: "application/json",
        ...(options.headers || {})
      },
      body: options.body ? JSON.stringify(options.body) : undefined
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.message || data.error || `${response.status}`);
    }
    return data;
  }

  async function loadConnectorDirectory() {
    setStatus(directoryStatusEl, labels.directoryLoading, false);
    const res = await fetch("/api/onboarding/connectors");
    if (!res.ok) {
      const txt = await res.text();
      throw new Error(`${res.status} ${res.statusText} ${txt}`);
    }
    const payload = await res.json();
    state.connectors = (Array.isArray(payload.items) ? payload.items : [])
      .map((item) => ({
        connectorId: String(item.connectorId || "").trim(),
        name: String(item.name || "").trim(),
        lastName: String(item.lastName || "").trim(),
        email: String(item.email || "").trim(),
        type: String(item.type || "").trim(),
        status: String(item.status || "").trim(),
        roles: Array.isArray(item.roles) ? item.roles : []
      }))
      .filter((item) => item.connectorId)
      .sort((a, b) => a.connectorId.localeCompare(b.connectorId));

    const rows = state.connectors.map((item) => [
      item.connectorId,
      item.name || "-",
      item.lastName || "-",
      item.email || "-",
      item.roles.length ? item.roles.map((role) => roleModeLabels[role] || role).join(" + ") : (item.type || "-"),
      item.status || "-"
    ]);

    renderTable(
      directoryTable,
      rows,
      [labels.directoryConnectorId, labels.directoryName, labels.directoryLastName, labels.directoryEmail, labels.directoryType, labels.directoryStatus],
      labels.directoryNoRows
    );

    setStatus(directoryStatusEl, labels.directoryLoaded, false);
    state.loadedDirectoryOnce = true;
  }

  async function loadConnectorRequests() {
    setStatus(requestsStatusEl, labels.requestsLoading, false);
    const payload = await fetchAuthedJson("/api/onboarding/requests?status=pending");
    state.requests = (Array.isArray(payload.items) ? payload.items : []).slice();

    const rows = state.requests.map((item) => {
      const requestedMode = String(item.requestedRoleMode || "").trim();
      const actions = `
        <div style="display:flex; gap:0.5rem; flex-wrap:wrap;">
          <button type="button" class="secondary connector-request-action" data-request-id="${escapeHtml(item.requestId)}" data-action="approve">${escapeHtml(labels.approve)}</button>
          <button type="button" class="secondary connector-request-action" data-request-id="${escapeHtml(item.requestId)}" data-action="deny">${escapeHtml(labels.deny)}</button>
        </div>
      `;
      return [
        item.requestId || "-",
        [item.firstName || "", item.lastName || ""].filter(Boolean).join(" ") || "-",
        item.email || "-",
        roleModeLabels[requestedMode] || requestedMode || "-",
        formatDateTime(item.createdAt),
        labels.pending,
        { html: actions }
      ];
    });

    renderTable(
      requestsTable,
      rows,
      [labels.requestsId, labels.requestsName, labels.requestsEmail, labels.requestsProfile, labels.requestsCreatedAt, labels.requestsStatus, labels.requestsAction],
      labels.requestsNoRows
    );

    setStatus(requestsStatusEl, labels.requestsLoaded, false);
    state.loadedRequestsOnce = true;
  }

  async function loadAuditTransactions() {
    setStatus(auditStatusEl, labels.auditLoading, false);
    const res = await fetch("/api/governance/audit/traces");
    if (!res.ok) {
      const txt = await res.text();
      throw new Error(`${res.status} ${res.statusText} ${txt}`);
    }
    const payload = await res.json();
    const rows = Object.values(payload.items || {})
      .sort((left, right) => String(right.receivedAt || "").localeCompare(String(left.receivedAt || "")))
      .map((trace) => {
        const event = trace.event || {};
        const parties = extractAuditParties(trace);
        const simplEnvironment = String((event.simplEnvironment || (event.simpl && event.simpl.environment) || trace.simplEnvironment || "")).toLowerCase();
        const simplPrefix = simplEnvironment === "lab" || simplEnvironment === "live" ? `${simplEnvironment} · ` : "";
        const simplState = simplPrefix + (trace.validation && trace.validation.registeredDataspace ? (isEn ? "registered" : "registrado") : (isEn ? "not registered" : "sin registro"));
        const signatureState = trace.validation && trace.validation.signaturePresent ? (isEn ? "signed" : "firmado") : (isEn ? "unsigned" : "sin firma");
        return [
          parties.consumerDataspaceId,
          parties.consumerConnectorId,
          parties.providerDataspaceId,
          parties.providerConnectorId,
          event.eventType || "-",
          simplifyResource(event.resource),
          simplState,
          signatureState,
          formatDateTime(trace.receivedAt)
        ];
      });

    renderTable(
      auditTable,
      rows,
      [labels.auditConsumerDs, labels.auditConsumer, labels.auditProviderDs, labels.auditProvider, labels.auditEvent, labels.auditAsset, labels.auditSimpl, labels.auditSignature, labels.auditTime],
      labels.auditNoRows
    );

    setStatus(auditStatusEl, labels.auditLoaded, false);
    state.loadedAuditOnce = true;
  }

  async function loadAuditTabData(forceRefresh) {
    try {
      if (forceRefresh || !state.loadedAuditOnce) {
        await loadAuditTransactions();
      }
    } catch (err) {
      setStatus(auditStatusEl, `${labels.auditError}: ${err && err.message ? err.message : labels.authError}`, true);
    }
  }

  async function loadUsersTabData(forceRefresh) {
    try {
      if (forceRefresh || !state.loadedDirectoryOnce) {
        await loadConnectorDirectory();
      }
      if (forceRefresh || !state.loadedRequestsOnce) {
        await loadConnectorRequests();
      }
    } catch (err) {
      const msg = err && err.message ? err.message : labels.authError;
      setStatus(directoryStatusEl, `${labels.directoryError}: ${msg}`, true);
      setStatus(requestsStatusEl, `${labels.requestsError}: ${msg}`, true);
    }
  }

  async function reviewRequest(requestId, action) {
    const reason = action === "deny" ? labels.reviewerReasonDenied : "";
    const payload = await fetchAuthedJson(`/api/onboarding/requests/${encodeURIComponent(requestId)}/${action}`, {
      method: "POST",
      body: { reason }
    });
    if (payload.notificationError) {
      setStatus(requestsStatusEl, payload.notificationError, true);
    } else {
      setStatus(requestsStatusEl, action === "approve" ? labels.approved : labels.denied, false);
    }
    await loadUsersTabData(true);
  }

  requestsTable.addEventListener("click", (event) => {
    const btn = event.target instanceof HTMLElement ? event.target.closest(".connector-request-action") : null;
    if (!btn) return;
    const requestId = btn.getAttribute("data-request-id") || "";
    const action = btn.getAttribute("data-action") || "";
    if (!requestId || !action) return;
    btn.setAttribute("disabled", "disabled");
    reviewRequest(requestId, action).catch((err) => {
      setStatus(requestsStatusEl, `${labels.requestsError}: ${err && err.message ? err.message : labels.authError}`, true);
    }).finally(() => {
      btn.removeAttribute("disabled");
    });
  });

  mainBtn.addEventListener("click", () => setPanel("main"));
  auditBtn.addEventListener("click", () => {
    setPanel("audit");
    loadAuditTabData(false);
  });
  usersBtn.addEventListener("click", () => {
    setPanel("users");
    loadUsersTabData(false);
  });
  reloadAuditBtn.addEventListener("click", () => loadAuditTabData(true));
  reloadDirectoryBtn.addEventListener("click", () => loadUsersTabData(true));
  reloadRequestsBtn.addEventListener("click", () => loadUsersTabData(true));

  mainBtn.textContent = labels.tabMain;
  auditBtn.textContent = labels.tabAudit;
  usersBtn.textContent = labels.tabUsers;
  setPanel("main");
})();
