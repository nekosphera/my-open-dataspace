#!/usr/bin/env bash
# Instala un nodo de My Open Dataspace.
#
# Pregunta cuatro cosas, genera las contraseñas que falten, escribe .env,
# levanta la composición, espera a que los servicios contesten e imprime la
# dirección y las credenciales iniciales.
#
# Es idempotente: ejecutarlo dos veces no rompe nada. Un .env que ya existe no
# se sobrescribe —lleva dentro las contraseñas del nodo, y regenerarlas deja
# la base de datos inaccesible—; se reutiliza, y sólo se le añaden las claves
# que le falten.
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${RAIZ}"

ENV_FILE="${RAIZ}/.env"
EJEMPLO="${RAIZ}/.env.example"

# Sin colores si la salida no es un terminal: un fichero de registro lleno de
# secuencias de escape no lo lee nadie.
if [[ -t 1 ]]; then
  NEGRITA=$'\e[1m'; VERDE=$'\e[32m'; AMARILLO=$'\e[33m'; ROJO=$'\e[31m'; FIN=$'\e[0m'
else
  NEGRITA=''; VERDE=''; AMARILLO=''; ROJO=''; FIN=''
fi

info()  { printf '%s\n' "$*"; }
ok()    { printf '%s✓%s %s\n' "${VERDE}" "${FIN}" "$*"; }
aviso() { printf '%s!%s %s\n' "${AMARILLO}" "${FIN}" "$*"; }
error() { printf '%s✗%s %s\n' "${ROJO}" "${FIN}" "$*" >&2; }

# --- Comprobaciones previas ---------------------------------------------

if ! command -v docker >/dev/null 2>&1; then
  error "Hace falta Docker. Instálalo desde https://docs.docker.com/get-docker/"
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  error "Hace falta Docker Compose v2 (el subcomando 'docker compose')."
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  error "Docker está instalado pero no responde. ¿Está arrancado el demonio?"
  exit 1
fi

[[ -f "${EJEMPLO}" ]] || { error "Falta .env.example; ¿estás en la raíz del repositorio?"; exit 1; }

# --- Utilidades -----------------------------------------------------------

# Una contraseña que no hay que recordar: la usan los contenedores entre sí.
generar_secreto() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -base64 24 | tr -d '\n/+=' | cut -c1-24
  else
    # Sin openssl, de /dev/urandom. Se filtra a alfanuméricos porque estos
    # valores viajan por .env y por variables de entorno, y un carácter raro
    # ahí se convierte en un fallo de arranque que nadie sabe leer.
    LC_ALL=C tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 24
  fi
}

leer_valor() {
  # leer_valor <fichero> <clave>
  sed -n "s/^$2=//p" "$1" | head -1 | sed 's/[[:space:]]*#.*$//' | sed 's/^"//;s/"$//'
}

fijar_valor() {
  # fijar_valor <fichero> <clave> <valor>. Sustituye si está, añade si no.
  local fichero="$1" clave="$2" valor="$3" tmp
  tmp="$(mktemp)"
  if grep -q "^${clave}=" "${fichero}"; then
    # El valor va por stdin del awk para no tener que escapar nada: una
    # contraseña con & o / rompe un sed y lo hace en silencio, sustituyendo
    # el carácter por otra cosa.
    VALOR="${valor}" awk -v k="${clave}" '
      $0 ~ "^" k "=" { printf "%s=\"%s\"\n", k, ENVIRON["VALOR"]; next }
      { print }
    ' "${fichero}" > "${tmp}"
  else
    cp "${fichero}" "${tmp}"
    printf '%s="%s"\n' "${clave}" "${valor}" >> "${tmp}"
  fi
  mv "${tmp}" "${fichero}"
}

preguntar() {
  # preguntar <variable_destino> <texto> <valor_por_omision>
  local destino="$1" texto="$2" omision="$3" respuesta
  if [[ "${DESATENDIDO}" == "true" ]]; then
    printf -v "${destino}" '%s' "${omision}"
    return
  fi
  if [[ -n "${omision}" ]]; then
    read -r -p "  ${texto} [${omision}]: " respuesta || true
  else
    read -r -p "  ${texto}: " respuesta || true
  fi
  printf -v "${destino}" '%s' "${respuesta:-${omision}}"
}

# --- Modo desatendido -----------------------------------------------------
#
# Sin terminal no se puede preguntar. En vez de quedarse colgado leyendo de un
# stdin cerrado, se toman los valores del .env.example y se dice.
DESATENDIDO=false
if [[ ! -t 0 ]] || [[ "${1:-}" == "--sin-preguntas" ]]; then
  DESATENDIDO=true
fi

# --- El .env --------------------------------------------------------------

NUEVO=false
if [[ -f "${ENV_FILE}" ]]; then
  ok "Ya hay un .env; se reutiliza. Sus contraseñas no se tocan."
else
  cp "${EJEMPLO}" "${ENV_FILE}"
  NUEVO=true
fi

if [[ "${NUEVO}" == "true" ]]; then
  info ""
  info "${NEGRITA}Cuatro preguntas y listo.${FIN}"
  info ""

  preguntar ORG_NAME    "Nombre de tu organización" "$(leer_valor "${EJEMPLO}" ODS_ORG_NAME)"
  preguntar ADMIN_EMAIL "Correo del administrador"  "$(leer_valor "${EJEMPLO}" ODS_ADMIN_EMAIL)"
  preguntar DOMINIO     "Dominio (vacío = sólo en local)" ""
  preguntar IDIOMA      "Idioma (es/en)"            "$(leer_valor "${EJEMPLO}" ODS_LANG)"

  # El identificador sale del nombre: minúsculas, sin acentos y con guiones.
  ORG_ID="$(printf '%s' "${ORG_NAME}" \
    | iconv -f UTF-8 -t ASCII//TRANSLIT 2>/dev/null || printf '%s' "${ORG_NAME}")"
  ORG_ID="$(printf '%s' "${ORG_ID}" | tr '[:upper:]' '[:lower:]' \
    | sed 's/[^a-z0-9]\+/-/g; s/^-//; s/-$//')"
  [[ -n "${ORG_ID}" ]] || ORG_ID="mi-organizacion"

  [[ "${IDIOMA}" == "en" ]] || IDIOMA="es"

  if [[ -n "${DOMINIO}" ]]; then
    PUBLICA="https://${DOMINIO}"
  else
    PUBLICA="http://localhost:$(leer_valor "${EJEMPLO}" ODS_HTTP_PORT)"
  fi

  fijar_valor "${ENV_FILE}" ODS_ORG_NAME    "${ORG_NAME}"
  fijar_valor "${ENV_FILE}" ODS_ORG_ID      "${ORG_ID}"
  fijar_valor "${ENV_FILE}" ODS_ADMIN_EMAIL "${ADMIN_EMAIL}"
  fijar_valor "${ENV_FILE}" ODS_LANG        "${IDIOMA}"
  fijar_valor "${ENV_FILE}" ODS_DOMAIN      "${DOMINIO}"
  fijar_valor "${ENV_FILE}" ODS_PUBLIC_URL  "${PUBLICA}"

  # Con dominio, la descarga tiene que poder entregar en él; sin dominio,
  # sólo en local. Es el control de destinos, y ponerlo en "cualquiera" por
  # comodidad es justamente lo que no se hace.
  if [[ -n "${DOMINIO}" ]]; then
    fijar_valor "${ENV_FILE}" ODS_DOWNLOAD_ALLOWED_HOSTS "localhost,${DOMINIO}"
  fi
fi

# Las contraseñas: se generan las que estén vacías y se deja en paz al resto.
GENERADAS=()
for clave in ODS_DB_PASSWORD ODS_KEYCLOAK_ADMIN_PASSWORD ODS_FUSEKI_ADMIN_PASSWORD; do
  if [[ -z "$(leer_valor "${ENV_FILE}" "${clave}")" ]]; then
    fijar_valor "${ENV_FILE}" "${clave}" "$(generar_secreto)"
    GENERADAS+=("${clave}")
  fi
done

chmod 600 "${ENV_FILE}" 2>/dev/null || true

if [[ ${#GENERADAS[@]} -gt 0 ]]; then
  ok "Generadas ${#GENERADAS[@]} contraseñas de servicio en .env (no hace falta recordarlas)."
fi

# --- Levantar -------------------------------------------------------------

info ""
info "${NEGRITA}Levantando el nodo…${FIN} (la primera vez tarda: hay que construir las imágenes)"
docker compose up -d --build

PUBLICA="$(leer_valor "${ENV_FILE}" ODS_PUBLIC_URL)"
PUERTO="$(leer_valor "${ENV_FILE}" ODS_HTTP_PORT)"
LOCAL="http://localhost:${PUERTO:-8080}"

info ""
info "Esperando a que conteste…"
LISTO=false
for _ in $(seq 1 90); do
  if curl -sf -o /dev/null "${LOCAL}/api/onboarding/health" 2>/dev/null; then
    LISTO=true
    break
  fi
  sleep 2
done

if [[ "${LISTO}" != "true" ]]; then
  error "El nodo no ha contestado a tiempo."
  info  "Mira qué pasa con:  docker compose logs --tail 50"
  exit 1
fi
ok "El nodo contesta."

# La identidad tarda más que el resto, y el asistente la necesita para crear
# el administrador. Se espera aquí para no mandar a nadie a una pantalla que
# va a fallar al pulsar Finalizar.
info "Esperando al servicio de identidad…"
for _ in $(seq 1 90); do
  if curl -sf -o /dev/null "${LOCAL}/auth/realms/dataspace/.well-known/openid-configuration" 2>/dev/null; then
    ok "La identidad contesta."
    break
  fi
  sleep 2
done

# --- Qué hacer ahora ------------------------------------------------------

CONFIGURADO=false
if ! curl -sf -o /dev/null "${LOCAL}/api/v1/setup" 2>/dev/null; then
  # El asistente devuelve 404 cuando el nodo ya pasó por él.
  CONFIGURADO=true
fi

info ""
info "${NEGRITA}Listo.${FIN}"
info ""
if [[ "${CONFIGURADO}" == "true" ]]; then
  info "  Tu nodo:     ${NEGRITA}${PUBLICA}${FIN}"
  info "  Consola:     ${PUBLICA}/console.html"
  info ""
  info "  Este nodo ya estaba configurado. Entra con el correo del"
  info "  administrador y la contraseña que pusiste en su día."
else
  info "  Abre ${NEGRITA}${PUBLICA}/setup${FIN} y responde cuatro preguntas más."
  info "  Ahí eliges la contraseña de administrador; no la genera nadie por ti."
  info ""
  info "  Menos de dos minutos, y al terminar tendrás un producto de datos"
  info "  de ejemplo ya publicado con el que probar el recorrido completo."
fi
info ""
if [[ -z "$(leer_valor "${ENV_FILE}" ODS_DOMAIN)" ]]; then
  aviso "Sin dominio: el nodo sirve por HTTP en local y no pide certificado."
  aviso "Para publicarlo, pon ODS_DOMAIN en .env y vuelve a ejecutar esto."
fi
info "  Parar:      docker compose down"
info "  Registros:  docker compose logs -f"
info ""
