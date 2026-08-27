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

  // --- La marca, aplicada de verdad -------------------------------------
  //
  // El color que se elige en el asistente llegaba hasta runtime-config.js y
  // ahi se quedaba: ninguna regla de estilo lo leia, asi que elegirlo no
  // cambiaba nada. Aqui se convierte en la paleta que usa styles.css.
  //
  // Se derivan los tonos en vez de pedir cinco colores: quien instala elige
  // uno y la interfaz sigue siendo coherente. La tinta del texto no se toca --
  // es lo que se lee.

  function leerHex(valor) {
    const texto = String(valor || "").trim();
    const corto = /^#?([0-9a-f])([0-9a-f])([0-9a-f])$/i.exec(texto);
    const largo = /^#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(texto);
    if (largo) {
      return [parseInt(largo[1], 16), parseInt(largo[2], 16), parseInt(largo[3], 16)];
    }
    if (corto) {
      return [
        parseInt(corto[1] + corto[1], 16),
        parseInt(corto[2] + corto[2], 16),
        parseInt(corto[3] + corto[3], 16)
      ];
    }
    return null;
  }

  function aHsl([r, g, b]) {
    const rn = r / 255, gn = g / 255, bn = b / 255;
    const max = Math.max(rn, gn, bn), min = Math.min(rn, gn, bn);
    const l = (max + min) / 2;
    if (max === min) return [0, 0, l];
    const d = max - min;
    const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    let h;
    if (max === rn) h = ((gn - bn) / d + (gn < bn ? 6 : 0)) / 6;
    else if (max === gn) h = ((bn - rn) / d + 2) / 6;
    else h = ((rn - gn) / d + 4) / 6;
    return [h, s, l];
  }

  function aRgb(h, s, l) {
    if (s === 0) {
      const v = Math.round(l * 255);
      return [v, v, v];
    }
    const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
    const p2 = 2 * l - q;
    const canal = (tt) => {
      let x = tt;
      if (x < 0) x += 1;
      if (x > 1) x -= 1;
      if (x < 1 / 6) return p2 + (q - p2) * 6 * x;
      if (x < 1 / 2) return q;
      if (x < 2 / 3) return p2 + (q - p2) * (2 / 3 - x) * 6;
      return p2;
    };
    return [
      Math.round(canal(h + 1 / 3) * 255),
      Math.round(canal(h) * 255),
      Math.round(canal(h - 1 / 3) * 255)
    ];
  }

  const acotar = (v, min, max) => Math.min(max, Math.max(min, v));
  const aTexto = ([r, g, b]) => `#${[r, g, b].map((v) => v.toString(16).padStart(2, "0")).join("")}`;

  function aplicarMarca(color) {
    const base = leerHex(color);
    // Un color ilegible no se corrige a medias: se deja la paleta de reserva,
    // que es coherente, en vez de derivar cinco tonos de una suposicion.
    if (!base) return false;
    const raiz = document.documentElement;
    const [h, s, l] = aHsl(base);
    const sVivo = acotar(s, 0.25, 1);
    const hondo = aRgb(h, sVivo, acotar(l * 0.62, 0.08, 0.45));
    const claro = aRgb(acotar(h + 0.035, 0, 1), sVivo, acotar(l + 0.12, 0.2, 0.8));
    const cielo = aRgb(h, acotar(sVivo * 0.62, 0.15, 0.7), 0.9);
    const bruma = aRgb(h, acotar(sVivo * 0.55, 0.12, 0.6), 0.96);
    raiz.style.setProperty("--brand-blue", aTexto(base));
    raiz.style.setProperty("--brand-blue-rgb", base.join(", "));
    raiz.style.setProperty("--brand-blue-deep", aTexto(hondo));
    raiz.style.setProperty("--brand-cyan", aTexto(claro));
    raiz.style.setProperty("--brand-cyan-rgb", claro.join(", "));
    raiz.style.setProperty("--brand-sky", aTexto(cielo));
    raiz.style.setProperty("--brand-mist", aTexto(bruma));
    return true;
  }

  // Se aplica ya, no al cargar el documento: este guion va en <head> y
  // `documentElement` ya existe, asi que la pagina no llega a pintarse con un
  // color y cambiar al otro delante de quien mira.
  aplicarMarca(config.brandColor);


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
    keycloakConfig,
    aplicarMarca
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => applyTextBindings(document), { once: true });
  } else {
    applyTextBindings(document);
  }
})();
