#!/usr/bin/env bash
# Copia de seguridad de un nodo de My Open Dataspace.
#
#     ./deploy/backup.sh [directorio-destino]
#
# Se lleva las cuatro cosas que no se pueden reconstruir: el volcado de
# PostgreSQL —que incluye el realm de Keycloak—, los ficheros publicados, el
# estado del nodo (altas, participantes, registro de evidencias, nodos
# conocidos, claves de firma) y el almacén RDF.
#
# Lo que NO se lleva, porque se reconstruye solo: las imágenes, los
# certificados de Caddy —se vuelven a pedir— y el catálogo consolidado de los
# nodos remotos, que se rellena en la siguiente sincronización.
#
# El `.env` **no** entra. Lleva las contraseñas del nodo dentro y una copia de
# seguridad se acaba copiando a sitios donde un fichero de secretos no debería
# estar. Guárdalo tú, donde guardes los secretos.
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${RAIZ}"

DESTINO="${1:-${RAIZ}/backups}"
SELLO="$(date -u +%Y%m%dT%H%M%SZ)"
CARPETA="${DESTINO}/${SELLO}"

if ! docker compose ps --status running --format '{{.Service}}' | grep -q postgres; then
  echo "El nodo no está levantado: sin PostgreSQL en marcha no hay volcado que hacer." >&2
  echo "Arráncalo con 'docker compose up -d' y vuelve a intentarlo." >&2
  exit 1
fi

mkdir -p "${CARPETA}"
echo "Copia en ${CARPETA}"

# --- PostgreSQL -----------------------------------------------------------
# Todas las bases en un volcado: la de la aplicación y el conector, y la de
# Keycloak. Separarlas invita a restaurar una sin la otra, y entonces el
# conector existe y su realm no.
echo "  base de datos…"
docker compose exec -T postgres pg_dumpall -U dataspace \
  | gzip > "${CARPETA}/postgres.sql.gz"

# --- Estado del nodo y ficheros publicados --------------------------------
echo "  estado y ficheros…"
docker compose exec -T app tar czf - -C /var/lib/ods . > "${CARPETA}/estado.tar.gz"

# --- Almacén RDF ----------------------------------------------------------
# En frío no: Fuseki está sirviendo. Se pide un volcado por su propia API, que
# es consistente; copiar los ficheros de TDB2 con el servicio en marcha da una
# copia que a veces restaura y a veces no, y no se sabe cuál hasta que hace
# falta.
echo "  almacén RDF…"
docker compose exec -T app sh -c '
  curl -sf -u "admin:${ODS_FUSEKI_ADMIN_PASSWORD}" \
    -H "Accept: application/n-quads" \
    "${ODS_FUSEKI_URL}/${ODS_FUSEKI_DATASET}/get"
' | gzip > "${CARPETA}/fuseki.nq.gz"

# --- Qué hay aquí ---------------------------------------------------------
{
  echo "{"
  echo "  \"creadaEn\": \"${SELLO}\","
  echo "  \"nodo\": \"$(grep -E '^ODS_ORG_ID=' .env 2>/dev/null | cut -d= -f2- | tr -d '\"' || echo desconocido)\","
  echo "  \"contiene\": [\"postgres.sql.gz\", \"estado.tar.gz\", \"fuseki.nq.gz\"],"
  echo "  \"noContiene\": [\".env (llévalo tú, donde guardes los secretos)\"]"
  echo "}"
} > "${CARPETA}/manifiesto.json"

echo
echo "Hecha:"
du -h "${CARPETA}"/* | sed 's/^/  /'
echo
echo "Comprueba que sirve antes de necesitarla: docs/backup.md explica cómo"
echo "restaurarla en un nodo aparte. Una copia que nadie ha restaurado nunca"
echo "es una carpeta con datos dentro, no una copia de seguridad."
