#!/usr/bin/env bash
# Recoge lo que hace falta para diagnosticar un nodo, sin secretos dentro.
#
#     ./deploy/diagnostico.sh [dirección] > diagnostico.txt
#
# Pensado para pegar en una incidencia. Lo que recoge:
#
#   - qué versión es y cómo está instalado
#   - el estado de los seis contenedores y sus reinicios
#   - qué contesta cada superficie pública
#   - las últimas líneas del registro de cada servicio
#   - qué variables están puestas, **sin sus valores**
#
# Lo que NO recoge, y por eso se puede pegar sin releerlo entero: el `.env`,
# ninguna contraseña, ningún token, ni el contenido de los datos publicados.
# Las direcciones de correo se tapan.
#
# Aun así, míralo antes de pegarlo. Un registro puede llevar el nombre de tus
# máquinas y de tu organización, y eso lo decides tú, no este guion.
set -uo pipefail

DIRECCION="${1:-http://localhost:8080}"
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${RAIZ}"

titulo() { printf '\n=== %s ===\n' "$*"; }

# Tapa direcciones de correo y cabeceras de autorización. No es un
# anonimizador: es el mínimo para que pegar esto no filtre lo evidente.
tapar() {
  sed -E \
    -e 's/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/<correo>/g' \
    -e 's/(Authorization|Bearer|token|password|secret)[":= ]+[^ ",}]+/\1 <tapado>/Ig'
}

titulo "Versión y entorno"
printf 'commit:     %s\n' "$(git rev-parse --short HEAD 2>/dev/null || echo 'sin git')"
printf 'etiqueta:   %s\n' "$(git describe --tags --always 2>/dev/null || echo '-')"
printf 'sistema:    %s\n' "$(uname -sr 2>/dev/null || echo desconocido)"
printf 'docker:     %s\n' "$(docker --version 2>/dev/null || echo 'no responde')"
printf 'compose:    %s\n' "$(docker compose version --short 2>/dev/null || echo '-')"

# Los contenedores del nodo, venga de una composición o de un `docker run`.
#
# Sólo mirar `docker compose ps` dejaba la sección de registros vacía cuando
# alguien arranca la imagen todo-en-uno, que es el primer camino del README.
CONTENEDORES=""
ORIGEN=""
if docker compose ps -q >/dev/null 2>&1 && [ -n "$(docker compose ps -q 2>/dev/null)" ]; then
  CONTENEDORES="$(docker compose ps -q 2>/dev/null)"
  ORIGEN="composición"
else
  CONTENEDORES="$(docker ps -aq --filter 'ancestor=ghcr.io/nekosphera/my-open-dataspace' 2>/dev/null)"
  [ -z "${CONTENEDORES}" ] && CONTENEDORES="$(docker ps -aq --filter 'name=ods' 2>/dev/null)"
  [ -n "${CONTENEDORES}" ] && ORIGEN="docker run"
fi

nombre_de() { docker inspect -f '{{.Name}}' "$1" 2>/dev/null | sed 's|^/||'; }

titulo "Contenedores"
printf 'origen: %s\n\n' "${ORIGEN:-ninguno encontrado}"
# `RestartCount` es la columna que más dice: un servicio que reinicia en bucle
# se ve «Up» un segundo de cada tres y en un `ps` normal parece sano.
if [ -z "${CONTENEDORES}" ]; then
  printf 'No hay ningún contenedor del nodo en esta máquina.\n'
  printf 'Si lo levantaste con docker compose, ejecuta esto desde la carpeta\n'
  printf 'donde está el docker-compose.yml.\n'
  # Y por qué no los ve, que suele ser un .env que falta.
  docker compose ps 2>&1 | head -3
else
  # RestartCount es la columna que más dice: un servicio en bucle de reinicio
  # se ve «Up» un segundo de cada tres y en un ps normal parece sano.
  for cid in ${CONTENEDORES}; do
    printf '  %-26s %s\n' \
      "$(nombre_de "${cid}")" \
      "$(docker inspect -f '{{.State.Status}}, {{.RestartCount}} reinicios, salida {{.State.ExitCode}}' "${cid}" 2>/dev/null)"
  done
fi

titulo "Qué contesta el nodo"
for ruta in / /api/onboarding/health /api/v1/setup /api/v1/nodes /api/v1/catalog /console.html /auth/realms/dataspace/.well-known/openid-configuration; do
  # curl escribe 000 cuando ni siquiera conecta, y además sale con código
  # distinto de cero: sin esto salían las dos cosas pegadas, «000sin
  # respuesta», que se lee como un estado HTTP que no existe.
  codigo="$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "${DIRECCION}${ruta}" 2>/dev/null)"
  if [ -z "${codigo}" ] || [ "${codigo}" = "000" ]; then
    codigo="sin respuesta"
  fi
  printf '  %-56s %s\n' "${ruta}" "${codigo}"
done

titulo "Salud y modo"
curl -s --max-time 10 "${DIRECCION}/api/onboarding/health" 2>/dev/null | tapar
printf '\n'

titulo "Catálogo"
# Contado con grep, no con python ni jq: este guion se ejecuta justamente en
# la máquina donde algo va mal, y no puede depender de un intérprete que a lo
# mejor no está. En Git Bash sobre Windows, `python3` resuelve al atajo de la
# Tienda y falla en silencio.
CATALOGO="$(curl -s --max-time 10 "${DIRECCION}/api/v1/catalog" 2>/dev/null)"
if [ -z "${CATALOGO}" ]; then
  printf '  sin respuesta\n'
elif ! printf '%s' "${CATALOGO}" | grep -q '"assets"'; then
  printf '  el nodo no devolvió un catálogo. Contestó:\n'
  printf '%s' "${CATALOGO}" | head -c 300 | tapar
  printf '\n'
else
  contar() { printf '%s' "${CATALOGO}" | grep -o "\"$1\"" | wc -l | tr -d ' '; }
  printf '  nodo:      %s\n' "$(printf '%s' "${CATALOGO}" | sed -n 's/.*"nodeId": *"\([^"]*\)".*/\1/p')"
  printf '  activos:   %s\n' "$(contar '@id')"
  printf '  registros: assets=%s policies=%s contracts=%s\n' \
    "$(contar assets)" "$(contar policies)" "$(contar contracts)"
fi

titulo "Configuración puesta (sin valores)"
# Qué variables hay, no qué valen. Casi todo problema de configuración es una
# variable que falta, no una mal escrita.
if [ -f .env ]; then
  grep -oE '^ODS_[A-Z0-9_]+=' .env | tr -d '=' | while read -r clave; do
    valor="$(grep -E "^${clave}=" .env | head -1 | cut -d= -f2- | tr -d '"')"
    if [ -z "${valor}" ]; then estado="vacía"; else estado="puesta"; fi
    printf '  %-34s %s\n' "${clave}" "${estado}"
  done
else
  printf '  no hay .env en %s\n' "${RAIZ}"
fi

titulo "Registros"
if [ -z "${CONTENEDORES}" ]; then
  printf 'Ninguno: no se encontró ningún contenedor del nodo.\n'
else
  for cid in ${CONTENEDORES}; do
    printf '\n--- %s ---\n' "$(nombre_de "${cid}")"
    docker logs --tail 40 "${cid}" 2>&1 | tapar
  done
fi

titulo "Fin"
printf 'Repásalo antes de pegarlo en una incidencia.\n'
