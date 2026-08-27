#!/usr/bin/env bash
# Arranque de la imagen todo-en-uno.
#
# Cuatro procesos en un contenedor: PostgreSQL, Fuseki, el conector y la
# aplicación. Es lo que un contenedor no debería hacer, y por eso esta imagen
# es sólo para evaluación y docencia: no hay reinicio por proceso, no hay
# límites por servicio y un fallo de cualquiera se lleva el contenedor.
#
# La composición de seis contenedores es la que se instala de verdad.
set -euo pipefail

DATOS="${ONBOARDING_DATA_DIR:-/var/lib/ods}"
PGDATA="${PGDATA:-${DATOS}/pgdata}"
PGBIN="$(ls -d /usr/lib/postgresql/*/bin | head -1)"

aviso() { printf '%s\n' "$*"; }

aviso "======================================================================"
aviso "MY OPEN DATASPACE -- IMAGEN DE EVALUACION"
aviso ""
aviso "Sin proveedor de identidad, sin TLS y SIN AUTENTICACION: cualquiera"
aviso "que alcance este puerto puede publicar, negociar y descargar."
aviso ""
aviso "Es para probar el producto y para docencia. Para instalarlo de verdad:"
aviso "  git clone https://github.com/nekosphera/my-open-dataspace"
aviso "  cd my-open-dataspace && ./install.sh"
aviso "======================================================================"
aviso ""

mkdir -p "${DATOS}" "${DATOS}/files" "${PGDATA}"
chown -R postgres:postgres "${PGDATA}"
chmod 700 "${PGDATA}"

# --- PostgreSQL -----------------------------------------------------------
if [ ! -s "${PGDATA}/PG_VERSION" ]; then
  aviso "[ods] inicializando la base de datos…"
  su postgres -c "${PGBIN}/initdb -D ${PGDATA} -A trust --encoding=UTF8 --locale=C" >/dev/null
fi

# Sólo por el socket local y por loopback. Este PostgreSQL no tiene contraseña
# -- `-A trust` -- porque en esta imagen no hay nadie más en la red del
# contenedor; que no escuche fuera es lo que hace que eso siga siendo cierto.
# El registro va dentro de PGDATA, que es lo unico que pertenece al usuario
# postgres: en el volumen a secas, que es de root, no puede escribirlo y
# pg_ctl se queda esperando a un servidor que nunca arranca.
#
# El `|| true` es para que el fallo lo cuente la comprobacion de abajo, con
# el registro delante, en vez de morirse aqui por el `set -e` sin decir nada.
su postgres -c "${PGBIN}/pg_ctl -D ${PGDATA} -o '-c listen_addresses=127.0.0.1 -p 5432' -w -l ${PGDATA}/postgres.log start" || true

if ! su postgres -c "${PGBIN}/pg_isready -q -h 127.0.0.1"; then
  aviso "[ods] PostgreSQL no ha arrancado. Su registro:"
  tail -20 "${PGDATA}/postgres.log" 2>/dev/null || aviso "  (no hay registro)"
  exit 1
fi

su postgres -c "${PGBIN}/psql -tAc \"SELECT 1 FROM pg_database WHERE datname='dataspace'\"" \
  | grep -q 1 || su postgres -c "${PGBIN}/createdb dataspace"
aviso "[ods] base de datos lista"

# --- Fuseki ---------------------------------------------------------------
#
# La carpeta del almacén se crea antes: `--loc` no la crea, y Fuseki se
# limita a decir «Does not exist» y morirse.
#
# Con TDB2, que es lo que permite compactar sin parar el servicio y lo que
# el catálogo consolidado necesita.
ALMACEN="${DATOS}/fuseki/${ODS_FUSEKI_DATASET:-dataspace}"
mkdir -p "${ALMACEN}"
# FUSEKI_HOME, o Fuseki busca su carpeta `webapp` relativa al directorio
# de trabajo -- que aquí es /srv/ods -- y muere con «Can't find
# baseResource».
FUSEKI_HOME=/opt/fuseki \
FUSEKI_BASE="${DATOS}/fuseki" \
  java -Xmx512m -jar /opt/fuseki/fuseki-server.jar \
    --port=3030 --update --tdb2 --loc="${ALMACEN}" \
    "/${ODS_FUSEKI_DATASET:-dataspace}" \
    > "${DATOS}/fuseki.log" 2>&1 &
FUSEKI_PID=$!

# --- El conector ----------------------------------------------------------
DATABASE_URL="jdbc:postgresql://127.0.0.1:5432/dataspace" \
DATABASE_USER="postgres" \
DATABASE_PASSWORD="" \
MANAGEMENT_PORT="9090" \
EDC_CONNECTOR_ID="${ODS_CONNECTOR_ID:-connector}" \
EDC_DOWNLOAD_ALLOWED_HOSTS="${ODS_DOWNLOAD_ALLOWED_HOSTS:-localhost,127.0.0.1}" \
  java -Xmx512m -jar /opt/connector.jar > "${DATOS}/connector.log" 2>&1 &
CONNECTOR_PID=$!

# Si cualquiera de los dos se cae, el contenedor entero se va: es un contenedor
# y no un sistema de init, y fingir que sigue vivo con medio producto dentro es
# peor que morirse.
# Se le manda la señal al proceso principal -- el PID 1 del contenedor -- y no
# `exit`: esto corre en un subshell en segundo plano, así que un `exit` mataba
# el subshell y dejaba el contenedor en pie sirviendo el portal con el conector
# muerto. Que es justo el «medio producto vivo» que esto existe para evitar.
PRINCIPAL=$$
vigilar() {
  while true; do
    if ! kill -0 "${FUSEKI_PID}" 2>/dev/null; then
      aviso "[ods] Fuseki se ha caído; sus últimas líneas:"
      tail -15 "${DATOS}/fuseki.log" 2>/dev/null || true
      kill -TERM "${PRINCIPAL}" 2>/dev/null
      return 1
    fi
    if ! kill -0 "${CONNECTOR_PID}" 2>/dev/null; then
      aviso "[ods] el conector se ha caído; sus últimas líneas:"
      tail -15 "${DATOS}/connector.log" 2>/dev/null || true
      kill -TERM "${PRINCIPAL}" 2>/dev/null
      return 1
    fi
    sleep 5
  done
}
vigilar &

aviso "[ods] esperando al almacén RDF y al conector…"
for _ in $(seq 1 60); do
  if curl -sf -o /dev/null "http://127.0.0.1:3030/$/ping" 2>/dev/null; then break; fi
  sleep 2
done

# --- La aplicación --------------------------------------------------------
cd /srv/ods
python3 app/tools/render_ui_runtime_config.py --env-file /dev/null || true
aviso "[ods] abre http://localhost:${ONBOARDING_PORT:-8080}"
exec python3 app/onboarding_api.py
