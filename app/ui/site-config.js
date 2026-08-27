(function () {
  // Lo que se ve si nadie ha configurado nada todavia. Ninguno de estos
  // valores nombra una organizacion ni un dominio: los pone quien instala,
  // desde .env o desde el asistente de primer arranque, y llegan aqui por
  // window.DATASPACE_RUNTIME_CONFIG.
  const defaults = {
    brandName: "My Open Dataspace",
    publicBaseUrl: window.location.origin,
    authBaseUrl: `${window.location.origin}/auth`,
    contactEmail: "",
    dcatIdentifierPrefix: "urn:ods:dataset:",
    defaultPublisher: "",
    iconPath: "",
    brandMarkPath: "",
    logoPath: "",
    brandColor: "#1f5fd0",
    realm: "dataspace",
    federatedIdentityProviders: {}
  };

  const config = Object.freeze({
    ...defaults,
    ...(window.DATASPACE_RUNTIME_CONFIG || {})
  });

  const derived = Object.freeze({});

  function pageUrl(pathname) {
    return new URL(pathname, config.publicBaseUrl).toString();
  }

  function updateMeta(selector, attribute, value) {
    if (!value) return;
    const node = document.querySelector(selector);
    if (node) {
      node.setAttribute(attribute, value);
    }
  }


  function applyTextBindings(root) {
    const scope = root || document;

    scope.querySelectorAll("[data-site-mark-img]").forEach((node) => {
      const src = String(config.brandMarkPath || config.iconPath || "").trim();
      if (!src) return;
      node.setAttribute("src", src);
      node.setAttribute("alt", `${config.brandName} mark`);
    });

    scope.querySelectorAll("[data-site-logo-img]").forEach((node) => {
      const src = String(config.logoPath || "").trim();
      if (!src) return;
      node.setAttribute("src", src);
      node.setAttribute("alt", `${config.brandName} logo`);
    });

    scope.querySelectorAll("[data-site-brand]").forEach((node) => {
      node.textContent = config.brandName;
    });

    scope.querySelectorAll("[data-site-publisher]").forEach((node) => {
      if ("value" in node) {
        node.value = config.defaultPublisher;
      } else {
        node.textContent = config.defaultPublisher;
      }
    });

    scope.querySelectorAll("[data-site-contact-email]").forEach((node) => {
      const email = config.contactEmail;
      if (!email) return;
      if (node.tagName === "A") {
        node.href = `mailto:${email}`;
      }
      node.textContent = email;
    });

    scope.querySelectorAll("[data-site-identifier-prefix]").forEach((node) => {
      if ("value" in node) {
        node.value = config.dcatIdentifierPrefix;
      } else {
        node.textContent = config.dcatIdentifierPrefix;
      }
    });

    scope.querySelectorAll("[data-site-public-host]").forEach((node) => {
      node.textContent = new URL(config.publicBaseUrl).host;
    });
  }

  function applyPage(options) {
    const page = options || {};
    const fullUrl = page.path ? pageUrl(page.path) : "";

    if (page.title) {
      document.title = `${config.brandName} | ${page.title}`;
    }
    if (page.description) {
      updateMeta('meta[name="description"]', "content", page.description.replaceAll("__BRAND__", config.brandName));
    }
    if (page.author !== false) {
      updateMeta('meta[name="author"]', "content", config.defaultPublisher);
    }
    if (page.robots) {
      updateMeta('meta[name="robots"]', "content", page.robots);
    }
    if (fullUrl) {
      updateMeta('link[rel="canonical"]', "href", fullUrl);
      updateMeta('meta[property="og:url"]', "content", fullUrl);
    }
    if (page.ogTitle) {
      updateMeta('meta[property="og:title"]', "content", `${config.brandName} - ${page.ogTitle}`);
    }
    if (page.ogDescription) {
      updateMeta('meta[property="og:description"]', "content", page.ogDescription.replaceAll("__BRAND__", config.brandName));
    }
    if (page.ogImagePath) {
      updateMeta('meta[property="og:image"]', "content", pageUrl(page.ogImagePath));
    }
    if (page.twitterTitle) {
      updateMeta('meta[name="twitter:title"]', "content", `${config.brandName} - ${page.twitterTitle}`);
    }
    if (page.twitterDescription) {
      updateMeta('meta[name="twitter:description"]', "content", page.twitterDescription.replaceAll("__BRAND__", config.brandName));
    }
    if (page.structuredData) {
      let node = document.getElementById("dataspace-structured-data");
      if (!node) {
        node = document.createElement("script");
        node.id = "dataspace-structured-data";
        node.type = "application/ld+json";
        document.head.appendChild(node);
      }
      node.textContent = JSON.stringify(page.structuredData, null, 2);
    }

    const iconHref = String(config.iconPath || "").trim();
    if (iconHref) {
      document.querySelectorAll('link[rel="icon"], link[rel="shortcut icon"]').forEach((node) => node.remove());
      const icon = document.createElement("link");
      icon.rel = "icon";
      icon.href = iconHref;
      document.head.appendChild(icon);
    }

    applyTextBindings(document);
  }

  function keycloakConfig() {
    return {
      url: config.authBaseUrl,
      realm: config.realm || "dataspace",
      clientId: "dataspace-ui"
    };
  }

  window.DATASPACE_SITE = {
    config,
    derived,
    pageUrl,
    applyPage,
    applyTextBindings,
    keycloakConfig
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => applyTextBindings(document), { once: true });
  } else {
    applyTextBindings(document);
  }
})();
