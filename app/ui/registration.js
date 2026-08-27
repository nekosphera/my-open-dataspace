(function () {
  const form = document.getElementById("registerForm");
  if (!form) return;

  const lang = String(document.documentElement.lang || "es").toLowerCase().startsWith("en") ? "en" : "es";
  const msg = {
    es: {
      loadingCaptcha: "Cargando captcha...",
      missingFirstName: "Introduce al menos el nombre.",
      invalidEmail: "Introduce un correo electrónico válido.",
      invalidPassword: "La contraseña debe tener mínimo 9 caracteres, una mayúscula, un número y un carácter especial.",
      invalidCaptcha: "Captcha inválido. Inténtalo de nuevo.",
      duplicateConnector: "Ya existe un conector para esta cuenta de correo.",
      duplicateRequest: "Ya existe una solicitud pendiente o aprobada para esta cuenta de correo.",
      submitting: "Enviando solicitud...",
      onboardingDone: "Solicitud enviada correctamente.",
      onboardingError: "No se pudo registrar la solicitud.",
      reloadCaptcha: "No se pudo cargar captcha. Recarga la página."
    },
    en: {
      loadingCaptcha: "Loading captcha...",
      missingFirstName: "Enter at least the first name.",
      invalidEmail: "Enter a valid email address.",
      invalidPassword: "Password must be at least 9 characters, with one uppercase letter, one number, and one special character.",
      invalidCaptcha: "Invalid captcha. Please try again.",
      duplicateConnector: "A connector already exists for this email address.",
      duplicateRequest: "A pending or approved request already exists for this email address.",
      submitting: "Submitting request...",
      onboardingDone: "Request submitted successfully.",
      onboardingError: "The registration request could not be completed.",
      reloadCaptcha: "Captcha could not be loaded. Reload the page."
    }
  }[lang];

  const firstNameEl = document.getElementById("registerFirstName");
  const lastNameEl = document.getElementById("registerLastName");
  const emailEl = document.getElementById("registerEmail");
  const passwordEl = document.getElementById("registerPassword");
  const roleModeEl = document.getElementById("registerRoleMode");
  const captchaQuestionEl = document.getElementById("captchaQuestion");
  const captchaAnswerEl = document.getElementById("captchaAnswer");
  const statusEl = document.getElementById("registerStatus");
  const resultEl = document.getElementById("registerResult");
  const submitBtn = document.getElementById("registerSubmit");

  let captchaId = "";

  function setStatus(text, isError) {
    statusEl.textContent = text || "";
    statusEl.className = isError ? "status status-error" : "status status-ok";
  }

  async function loadCaptcha() {
    setStatus(msg.loadingCaptcha, false);
    const res = await fetch("/api/onboarding/captcha");
    if (!res.ok) throw new Error("captcha_http_error");
    const data = await res.json();
    captchaId = data.captchaId;
    captchaQuestionEl.textContent = data.question;
    setStatus("", false);
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    resultEl.textContent = "";

    const firstName = String(firstNameEl.value || "").trim();
    const lastName = String(lastNameEl.value || "").trim();
    const email = String(emailEl.value || "").trim().toLowerCase();
    const password = String(passwordEl.value || "");
    const requestedRoleMode = String(roleModeEl.value || "consumer").trim().toLowerCase();
    const captchaAnswer = String(captchaAnswerEl.value || "").trim();

    if (!firstName) {
      setStatus(msg.missingFirstName, true);
      return;
    }
    if (!email || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
      setStatus(msg.invalidEmail, true);
      return;
    }
    if (!/^(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{9,}$/.test(password)) {
      setStatus(msg.invalidPassword, true);
      return;
    }
    if (!captchaAnswer) {
      setStatus(msg.invalidCaptcha, true);
      return;
    }

    submitBtn.disabled = true;
    setStatus(msg.submitting, false);

    try {
      const res = await fetch("/api/onboarding/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          firstName,
          lastName,
          email,
          password,
          requestedRoleMode,
          captchaId,
          captchaAnswer,
          lang
        })
      });

      const data = await res.json();
      if (!res.ok || !data.ok) {
        if (data && data.error === "invalid_captcha") {
          throw new Error(msg.invalidCaptcha);
        }
        if (data && data.error === "invalid_password") {
          throw new Error(msg.invalidPassword);
        }
        if (data && data.error === "connector_exists") {
          throw new Error(msg.duplicateConnector);
        }
        if (data && data.error === "request_already_exists") {
          throw new Error(msg.duplicateRequest);
        }
        throw new Error((data && data.message) || msg.onboardingError);
      }

      resultEl.textContent = `${msg.onboardingDone}\n${data.message}`;
      setStatus("", false);
      form.reset();
      await loadCaptcha();
    } catch (err) {
      setStatus(err.message || msg.onboardingError, true);
      try {
        await loadCaptcha();
      } catch (_) {
        setStatus(msg.reloadCaptcha, true);
      }
    } finally {
      submitBtn.disabled = false;
    }
  });

  loadCaptcha().catch(() => setStatus(msg.reloadCaptcha, true));
})();
