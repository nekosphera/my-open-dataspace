#!/usr/bin/env bash
# Toma las capturas del README contra un nodo levantado.
#
#     ./deploy/capturas.sh [dirección] [carpeta-destino]
#
# Con Chrome o Edge en modo headless. No hace falta instalar nada más: si has
# llegado hasta aquí tienes un navegador.
#
# **Levanta el nodo con el nombre «Organización de Ejemplo».** Una captura
# hecha sobre un nodo configurado con el nombre de una organización real mete
# esa marca en el repositorio por la puerta de atrás, que es justo lo que la
# lista de la sección 14 prohíbe.
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIRECCION="${1:-http://localhost:8080}"
DESTINO="${2:-${RAIZ}/docs/imagenes}"

# El primero que aparezca. Chrome y Edge toman la misma captura: los dos son
# Chromium y `--screenshot` se comporta igual.
NAVEGADOR=""
for candidato in \
  "${CHROME:-}" \
  "/c/Program Files/Google/Chrome/Application/chrome.exe" \
  "/c/Program Files (x86)/Google/Chrome/Application/chrome.exe" \
  "/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" \
  "/c/Program Files/Microsoft/Edge/Application/msedge.exe" \
  "$(command -v google-chrome || true)" \
  "$(command -v chromium || true)" \
  "$(command -v chromium-browser || true)"
do
  if [[ -n "${candidato}" && -x "${candidato}" ]]; then
    NAVEGADOR="${candidato}"
    break
  fi
done

if [[ -z "${NAVEGADOR}" ]]; then
  echo "No encuentro Chrome, Chromium ni Edge." >&2
  echo "Pásame la ruta:  CHROME=/ruta/al/navegador ./deploy/capturas.sh" >&2
  exit 1
fi

if ! curl -sf -o /dev/null "${DIRECCION}/api/onboarding/health"; then
  echo "El nodo no contesta en ${DIRECCION}." >&2
  echo "Levántalo con ./install.sh y completa el asistente antes de capturar." >&2
  exit 1
fi

# Un nodo sin configurar redirige todo a /setup, así que las capturas saldrían
# todas iguales y ninguna enseñaría el producto.
if curl -sf -o /dev/null "${DIRECCION}/api/v1/setup"; then
  echo "Este nodo todavía no ha pasado por el asistente." >&2
  echo "Abre ${DIRECCION}/setup, complétalo, y vuelve a ejecutar esto." >&2
  exit 1
fi

mkdir -p "${DESTINO}"
PERFIL="$(mktemp -d)"
trap 'rm -rf "${PERFIL}"' EXIT

capturar() {
  local nombre="$1" ruta="$2" alto="${3:-900}"
  echo "  ${nombre}…"
  "${NAVEGADOR}" \
    --headless=new --disable-gpu --no-sandbox --hide-scrollbars \
    --user-data-dir="${PERFIL}/${nombre}" \
    --window-size="1280,${alto}" \
    --virtual-time-budget=6000 \
    --screenshot="${DESTINO}/${nombre}.png" \
    "${DIRECCION}${ruta}" 2>/dev/null
}

echo "Capturando ${DIRECCION} en ${DESTINO}"
capturar portal        "/"              1100
capturar catalogo      "/home.html"     1400
capturar acceso        "/login.html"     900

echo
echo "Hechas:"
ls -1 "${DESTINO}"/*.png | sed 's/^/  /'
echo
echo "Míralas antes de darlas por buenas. Lo que no puede salir en ellas:"
echo "  - el nombre de una organización real"
echo "  - una dirección de correo que exista"
echo "  - un dominio que no sea localhost"
