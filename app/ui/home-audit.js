(function () {
  const table = document.getElementById("auditTransactionsTable");
  const reloadBtn = document.getElementById("reloadAuditBtn");
  const statusEl = document.getElementById("auditStatus");
  if (!table || !reloadBtn || !statusEl) return;

  const isEn = String(document.documentElement.lang || "es").toLowerCase().startsWith("en");
  const labels = isEn
    ? {
        consumer: "Consumer connector",
        provider: "Provider connector",
        asset: "Transferred asset",
        status: "Final status",
        transferId: "Transfer ID",
        loading: "Loading audit log...",
        loaded: "Audit log updated",
        partialLoaded: "Audit log updated with partial data",
        noRows: "No transactions found",
        loadError: "Failed to load audit log",
        loginRequired: "Sign in to load the audit log",
        keycloakUnavailable: "Keycloak JS unavailable",
        keycloakAuthFailed: "Keycloak authentication failed",
        missingToken: "Missing Keycloak access token"
      }
    : {
        consumer: "Conector consumidor",
        provider: "Conector proveedor",
        asset: "Data asset transferido",
        status: "Estado final",
        transferId: "ID transferencia",
        loading: "Cargando registro de auditoria...",
        loaded: "Registro de auditoria actualizado",
        partialLoaded: "Registro de auditoria actualizado con datos parciales",
        noRows: "No se encontraron transacciones",
        loadError: "No se pudo cargar el registro de auditoria",
        loginRequired: "Inicia sesión para cargar la auditoria",
        keycloakUnavailable: "Keycloak JS no disponible",
        keycloakAuthFailed: "No se pudo autenticar con Keycloak",
        missingToken: "No hay token de acceso de Keycloak"
      };

  const connectorTargets = ["connector-1", "connector-2", "connector-3"];
  const statusRank = {
    REQUESTED: 10,
    INITIAL: 20,
    STARTED: 30,
    IN_PROGRESS: 40,
    RUNNING: 50,
    CONFIRMED: 60,
    APPROVED: 70,
    FINALIZED: 80,
    COMPLETED: 90,
    DECLINED: 90,
    TERMINATED: 90,
    FAILED: 90,
    CANCELLED: 90,
    ERROR: 90
  };

  const state = {
    accessToken: "",
    keycloak: null
  };

  function syncAccessToken() {
    const token = window.__DATASPACE_ACCESS_TOKEN || "";
    if (token && token !== state.accessToken) {
      state.accessToken = token;
    }
    return state.accessToken;
  }

  function setStatus(message, isError) {
    statusEl.textContent = message;
    statusEl.classList.remove("status-ok", "status-error");
    statusEl.classList.add(isError ? "status-error" : "status-ok");
  }

  function normalizeStatus(value) {
    return String(value || "UNKNOWN").trim().toUpperCase() || "UNKNOWN";
  }

  function getStatusRank(status) {
    return statusRank[status] || 0;
  }

  function normalizeNegotiation(raw) {
    return {
      transferId: raw.id || raw["@id"] || raw.negotiationId || "",
      consumerConnectorId: raw.consumerConnectorId || raw.consumerId || "",
      providerConnectorId: raw.providerConnectorId || raw.providerId || "",
      assetId: raw.assetId || raw.asset || "",
      status: normalizeStatus(raw.status)
    };
  }

  function buildRowKey(row) {
    return [row.transferId, row.consumerConnectorId, row.providerConnectorId, row.assetId].join("|");
  }

  function dedupeWithFinalStatus(rows) {
    const index = new Map();
    rows.forEach((row) => {
      const key = buildRowKey(row);
      const existing = index.get(key);
      if (!existing) {
        index.set(key, row);
        return;
      }
      if (getStatusRank(row.status) >= getStatusRank(existing.status)) {
        index.set(key, row);
      }
    });
    return Array.from(index.values());
  }

  function renderRows(rows) {
    table.innerHTML = "";

    const thead = document.createElement("thead");
    const header = document.createElement("tr");
    [labels.consumer, labels.provider, labels.asset, labels.status, labels.transferId].forEach((title) => {
      const th = document.createElement("th");
      th.textContent = title;
      header.appendChild(th);
    });
    thead.appendChild(header);
    table.appendChild(thead);

    const tbody = document.createElement("tbody");
    if (!rows.length) {
      const tr = document.createElement("tr");
      const td = document.createElement("td");
      td.colSpan = 5;
      td.textContent = labels.noRows;
      tr.appendChild(td);
      tbody.appendChild(tr);
      table.appendChild(tbody);
      return;
    }

    rows.forEach((row) => {
      const tr = document.createElement("tr");
      [
        row.consumerConnectorId || "-",
        row.providerConnectorId || "-",
        row.assetId || "-",
        row.status || "UNKNOWN",
        row.transferId || "-"
      ].forEach((value) => {
        const td = document.createElement("td");
        td.textContent = value;
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });

    table.appendChild(tbody);
  }

  async function connectorFetchNegotiations(connectorId) {
    if (state.keycloak) {
      try {
        const refreshed = await state.keycloak.updateToken(30);
        if ((refreshed || !window.__DATASPACE_ACCESS_TOKEN) && state.keycloak.token) {
          state.accessToken = state.keycloak.token;
          window.__DATASPACE_ACCESS_TOKEN = state.accessToken;
        }
      } catch (_err) {
        // fallback to last token value below
      }
    }

    const accessToken = syncAccessToken();
    if (!accessToken) {
      throw new Error(labels.missingToken);
    }

    const response = await fetch(`/api/${connectorId}/management/v3/negotiations`, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json"
      }
    });

    if (!response.ok) {
      const body = await response.text();
      throw new Error(`${connectorId}: ${response.status} ${response.statusText} ${body}`);
    }

    const rows = await response.json();
    return (Array.isArray(rows) ? rows : []).map(normalizeNegotiation);
  }

  async function initAuth() {
    if (typeof window.Keycloak !== "function") {
      try {
        const mod = await import("./vendor/keycloak.js");
        window.Keycloak = mod && (mod.default || mod.Keycloak || window.Keycloak);
      } catch (_err) {
        return false;
      }
    }
    if (typeof window.Keycloak !== "function") {
      return false;
    }

    const keycloakOptions =
      window.DATASPACE_SITE && typeof window.DATASPACE_SITE.keycloakConfig === "function"
        ? window.DATASPACE_SITE.keycloakConfig()
        : {
            url: (window.DATASPACE_SITE && window.DATASPACE_SITE.config.authBaseUrl) || `${window.location.origin}/auth`,
            realm: "dataspace",
            clientId: "dataspace-ui"
          };

    const keycloak = new window.Keycloak(keycloakOptions);

    const authenticated = await keycloak.init({
      onLoad: "check-sso",
      checkLoginIframe: false,
      pkceMethod: "S256"
    });

    if (!authenticated || !keycloak.token) {
      return false;
    }

    state.keycloak = keycloak;
    state.accessToken = keycloak.token;
    state.idToken = keycloak.idToken || "";
    window.__DATASPACE_ACCESS_TOKEN = state.accessToken;
    window.__DATASPACE_ID_TOKEN = state.idToken;

    window.setInterval(async () => {
      try {
        const refreshed = await keycloak.updateToken(30);
        if (refreshed && keycloak.token) {
          state.accessToken = keycloak.token;
          state.idToken = keycloak.idToken || state.idToken || "";
          window.__DATASPACE_ACCESS_TOKEN = state.accessToken;
          window.__DATASPACE_ID_TOKEN = state.idToken;
        }
      } catch (_err) {
        // noop
      }
    }, 10000);

    return true;
  }

  async function loadAudit() {
    setStatus(labels.loading, false);
    const allRows = [];
    const failures = [];
    const settled = await Promise.allSettled(connectorTargets.map((connectorId) => connectorFetchNegotiations(connectorId)));

    settled.forEach((result, index) => {
      if (result.status === "fulfilled") {
        allRows.push(...result.value);
        return;
      }
      failures.push(`${connectorTargets[index]}: ${result.reason && result.reason.message ? result.reason.message : "error"}`);
    });

    if (allRows.length === 0 && failures.length) {
      throw new Error(failures.join(" | "));
    }

    const finalRows = dedupeWithFinalStatus(allRows).sort((a, b) => {
      const left = a.transferId || "";
      const right = b.transferId || "";
      return right.localeCompare(left);
    });

    renderRows(finalRows);
    if (failures.length) {
      setStatus(`${labels.partialLoaded}. ${failures.join(" | ")}`, true);
      return;
    }

    setStatus(labels.loaded, false);
  }

  reloadBtn.addEventListener("click", () => {
    if (!state.accessToken) {
      setStatus(labels.loginRequired, false);
      return;
    }
    loadAudit().catch((err) => {
      console.error(err);
      renderRows([]);
      setStatus(`${labels.loadError}: ${err.message}`, true);
    });
  });

  initAuth()
    .then((authenticated) => {
      if (!authenticated) {
        renderRows([]);
        setStatus(labels.loginRequired, false);
        return;
      }
      return loadAudit();
    })
    .catch((err) => {
      console.error(err);
      renderRows([]);
      setStatus(`${labels.loadError}: ${err.message || labels.keycloakAuthFailed}`, true);
    });
})();
