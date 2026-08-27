#!/usr/bin/env bash
set -euo pipefail

ENV_FILE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --env-file)
      if [[ $# -lt 2 ]]; then
        echo "ERROR: --env-file requires a path" >&2
        exit 1
      fi
      ENV_FILE="$2"
      shift 2
      ;;
    -h|--help)
      echo "Usage: $0 [--env-file /path/to/file.env]"
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument '$1'" >&2
      exit 1
      ;;
  esac
done

if [[ -z "${ENV_FILE}" && -f "./tools/fuseki_federation.env" ]]; then
  ENV_FILE="./tools/fuseki_federation.env"
fi

if [[ -n "${ENV_FILE}" ]]; then
  if [[ ! -f "${ENV_FILE}" ]]; then
    echo "ERROR: env file not found: ${ENV_FILE}" >&2
    exit 1
  fi
  # shellcheck disable=SC1090
  set -a
  source "${ENV_FILE}"
  set +a
fi

FUSEKI_BASE_URL="${FUSEKI_BASE_URL:-http://localhost:3030}"
FUSEKI_DATASET="${FUSEKI_DATASET:-dataspace}"
GRAPH_BASE_IRI="${GRAPH_BASE_IRI:-urn:dataspace:catalog}"
FUSEKI_ADMIN_USER="${FUSEKI_ADMIN_USER:-admin}"
FUSEKI_ADMIN_PASSWORD="${FUSEKI_ADMIN_PASSWORD:-admin}"

KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8089}"
KEYCLOAK_REALM="${KEYCLOAK_REALM:-dataspace}"
KEYCLOAK_ADMIN_USER="${KEYCLOAK_ADMIN_USER:-}"
KEYCLOAK_ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD:-}"

# De donde salen los nodos a federar.
#
# Con FEDERATION_NODES_FILE apuntando a un fichero de nodos conocidos, el
# federador lee de ahi: es lo que permite que un nodo se de de alta desde la
# consola y entre en la siguiente sincronizacion sin tocar configuracion ni
# reiniciar nada. Sin el, se usan las variables CONNECTOR*_ de abajo, que es
# como se ejecuta este guion suelto, fuera de un nodo.
FEDERATION_NODES_FILE="${FEDERATION_NODES_FILE:-}"

CONNECTOR1_NAME="${CONNECTOR1_NAME:-connector-1}"
CONNECTOR1_URL="${CONNECTOR1_URL:-http://localhost:8080}"
CONNECTOR1_CLIENT_ID="${CONNECTOR1_CLIENT_ID:-edc-connector}"
CONNECTOR1_CLIENT_SECRET="${CONNECTOR1_CLIENT_SECRET:-}"
# What each connector is for. A connector that consumes is not a provider that
# failed, and the two were indistinguishable in the count. Overridable per
# deployment, because a role is a declaration and declarations change.
CONNECTOR1_ROLE="${CONNECTOR1_ROLE:-provider}"

# No URL default, the same shape as the third connector below: a deployment
# that declares one connector has one connector. Inventing a second one at
# localhost:8081 made every run of a single-connector deployment warn about a
# missing secret for a connector nobody had configured - which is the first
# thing anyone following the published quickstart sees. Where a second
# connector does exist it is declared, so nothing that works today changes.
CONNECTOR2_NAME="${CONNECTOR2_NAME:-connector-2}"
CONNECTOR2_URL="${CONNECTOR2_URL:-}"
CONNECTOR2_CLIENT_ID="${CONNECTOR2_CLIENT_ID:-edc-connector-2}"
CONNECTOR2_CLIENT_SECRET="${CONNECTOR2_CLIENT_SECRET:-}"
# consumer, on all three domains. Its registry entry is consumer-only with
# capabilities ["consume"], so publishing nothing is what it is for - and the
# summary below used to count that as an empty provider, which reads as a
# federation missing a participant every single run.
CONNECTOR2_ROLE="${CONNECTOR2_ROLE:-consumer}"

CONNECTOR3_NAME="${CONNECTOR3_NAME:-}"
CONNECTOR3_URL="${CONNECTOR3_URL:-}"
CONNECTOR3_CLIENT_ID="${CONNECTOR3_CLIENT_ID:-edc-connector-3}"
CONNECTOR3_CLIENT_SECRET="${CONNECTOR3_CLIENT_SECRET:-}"
CONNECTOR3_ROLE="${CONNECTOR3_ROLE:-provider}"

FEDERATION_FETCH_RETRIES="${FEDERATION_FETCH_RETRIES:-5}"
FEDERATION_FETCH_RETRY_DELAY_SECONDS="${FEDERATION_FETCH_RETRY_DELAY_SECONDS:-1}"
FEDERATION_PUBLISH_EMPTY_CATALOG="${FEDERATION_PUBLISH_EMPTY_CATALOG:-false}"
FEDERATION_ENSURE_SERVICE_ACCOUNT_READ_ROLE="${FEDERATION_ENSURE_SERVICE_ACCOUNT_READ_ROLE:-true}"
FEDERATION_SERVICE_ACCOUNT_READ_ROLE="${FEDERATION_SERVICE_ACCOUNT_READ_ROLE:-dataspace-user}"
FEDERATION_RUN_ID="${FEDERATION_RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)-$$}"

for cmd in curl jq sed; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: missing dependency '$cmd'" >&2
    exit 1
  fi
done

KEYCLOAK_ADMIN_TOKEN=""

# What each declared connector turned out to contribute. Every run already knew
# this and said it one line at a time, so a connector that stopped publishing
# read exactly like one that never did - and connector-2 has been fetching zero
# assets on all three domains for as long as there are logs, in a WARN nobody
# reads. Reconciled at the end of the run instead, in one line, against what
# was declared.
FEDERATION_DECLARED=()
FEDERATION_CONTRIBUTING=()
FEDERATION_EMPTY=()
FEDERATION_UNAVAILABLE=()
FEDERATION_PROVIDERS=()

escape_literal() {
  printf "%s" "${1:-}" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' -e ':a;N;$!ba;s/\n/\\n/g'
}

sparql_update() {
  local update="$1"
  curl -fsS -X POST \
    -u "${FUSEKI_ADMIN_USER}:${FUSEKI_ADMIN_PASSWORD}" \
    "${FUSEKI_BASE_URL}/${FUSEKI_DATASET}/update" \
    --data-urlencode "update=${update}" >/dev/null
}

sparql_select_json() {
  local query="$1"
  curl -fsS -X POST \
    -u "${FUSEKI_ADMIN_USER}:${FUSEKI_ADMIN_PASSWORD}" \
    -H "Accept: application/sparql-results+json" \
    "${FUSEKI_BASE_URL}/${FUSEKI_DATASET}/query" \
    --data-urlencode "query=${query}"
}

# One line of the model this federator maintains: a subject, a predicate, a
# value and whether that value is an IRI or a literal. Both the catalog we
# want and the catalog already stored are expressed this way, so the two can
# be compared exactly and only the difference has to be written.
emit_triple() {
  local subject="$1" predicate="$2" object="$3" kind="$4"
  jq -cn --arg s "${subject}" --arg p "${predicate}" \
    --arg o "${object}" --arg t "${kind}" \
    '{s:$s,p:$p,o:$o,t:$t}' >>"${DESIRED_FILE}"
}

emit_literal() { emit_triple "$1" "$2" "$3" literal; }
emit_iri() { emit_triple "$1" "$2" "$3" uri; }

# A literal only when there is something to say. The urn:edc: triples below
# emit an empty string when a property is absent, which is a value that says
# "this asset has no title" rather than saying nothing; the standard terms do
# not repeat that.
emit_present_literal() {
  [[ -n "$3" ]] || return 0
  emit_triple "$1" "$2" "$3" literal
}

# The vocabularies the catalogue is read with, rather than the URN scheme it
# was written with.
#
# The asset properties arrive DCAT-keyed from the connector - the reader below
# already looks for properties["dcat:keyword"] and properties["dcat:mediaType"]
# - and were then buried in urn:edc: predicates invented here. Only two of the
# terms this federator wrote were standard. Req.-BB-DSO-008 of the DSSC
# Catalogue self-assessment asks for standardised metadata vocabularies, and a
# private URN scheme is not one; Req.-BB-DSO-001 asks for descriptions managed
# in DCAT, which the publication side already does.
#
# Both halves are written for now. ui/app.js queries `PREFIX edc: <urn:edc:>`,
# so removing the URNs would blank the console; they are the deprecated half
# and go when that query moves.
RDF_TYPE="http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
DCAT_NS="http://www.w3.org/ns/dcat#"
DCT_NS="http://purl.org/dc/terms/"
ODS_NS="urn:ods:"

drop_orphan_sync_graphs() {
  # Earlier versions staged each run in <graph>/.sync-<run id> and swapped it
  # in. A run that died between the swap steps left its staging graph behind,
  # where it still answers catalog queries and double counts assets. Nothing
  # creates them any more; these are the leftovers.
  local graph_iri="$1" orphan
  while IFS= read -r orphan; do
    [[ -z "${orphan}" ]] && continue
    echo "[federator] dropping orphaned staging graph <${orphan}>" >&2
    sparql_update "DROP SILENT GRAPH <${orphan}>"
  done < <(
    sparql_select_json "
      SELECT DISTINCT ?g WHERE {
        GRAPH ?g { ?s ?p ?o }
        FILTER(STRSTARTS(STR(?g), \"${graph_iri}/.sync-\"))
      }" | jq -r '.results.bindings[].g.value'
  )
}

# Write only what changed.
#
# This federator used to rebuild the catalog on every run: it staged a
# complete copy in a temporary graph, dropped the live graph and copied the
# staged one over it, once every FEDERATION_INTERVAL_SECONDS. TDB2 is
# append-only and reclaims nothing until it is compacted, so a catalog of a
# few hundred triples that never changed still grew the store by megabytes an
# hour. Measured on three participants in August 2026, that had reached 17 GB
# for 371 triples on one of them and 10 GB for 1165 on another, on hosts whose
# root filesystem was 80 % full.
#
# So: compare what the connector reports against what is stored, and issue a
# single update carrying just the difference. When nothing changed - the usual
# case - nothing is written at all, and the store stops growing.
sync_graph() {
  local graph_iri="$1" connector_name="$2" connector_url="$3"
  local assets_count="$4" policies_count="$5" contracts_count="$6"
  local marker_uri="${graph_iri}/sync"

  drop_orphan_sync_graphs "${graph_iri}"

  local current_file to_insert to_delete
  current_file="$(mktemp)"
  to_insert="$(mktemp)"
  to_delete="$(mktemp)"

  # The marker carries the run's own timestamp, so it is compared separately:
  # included in the comparison it would differ on every run and defeat the
  # whole point.
  sparql_select_json "
    SELECT ?s ?p ?o WHERE {
      GRAPH <${graph_iri}> { ?s ?p ?o }
      FILTER(STR(?s) != \"${marker_uri}\")
    }" |
    jq -c '.results.bindings[]
      | {s:.s.value, p:.p.value, o:.o.value,
         t:(if .o.type == "uri" then "uri" else "literal" end)}' \
      >"${current_file}"

  if grep -q '"s":"_:' "${current_file}"; then
    echo "[federator] WARN ${connector_name}: <${graph_iri}> holds blank nodes, which this federator cannot express; leaving it untouched" >&2
    rm -f "${current_file}" "${to_insert}" "${to_delete}"
    return
  fi

  sort -u "${DESIRED_FILE}" >"${DESIRED_FILE}.sorted"
  sort -u "${current_file}" >"${current_file}.sorted"
  comm -13 "${current_file}.sorted" "${DESIRED_FILE}.sorted" >"${to_insert}"
  comm -23 "${current_file}.sorted" "${DESIRED_FILE}.sorted" >"${to_delete}"

  local inserted removed
  inserted=$(wc -l <"${to_insert}")
  removed=$(wc -l <"${to_delete}")

  if [[ "${inserted}" -eq 0 && "${removed}" -eq 0 ]]; then
    echo "Unchanged ${connector_name}: assets=${assets_count}, policies=${policies_count}, contracts=${contracts_count}; nothing written"
    rm -f "${current_file}" "${current_file}.sorted" "${DESIRED_FILE}.sorted" \
      "${to_insert}" "${to_delete}"
    return
  fi

  local changed_at
  changed_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  local update="DELETE WHERE { GRAPH <${graph_iri}> { <${marker_uri}> ?p ?o } } ;"
  if [[ "${removed}" -gt 0 ]]; then
    update="${update}
DELETE DATA { GRAPH <${graph_iri}> {
$(render_triple <"${to_delete}")
} } ;"
  fi
  update="${update}
INSERT DATA { GRAPH <${graph_iri}> {
$(render_triple <"${to_insert}")
<${marker_uri}> <urn:edc:connector> \"$(escape_literal "${connector_name}")\" .
<${marker_uri}> <urn:edc:sourceUrl> \"$(escape_literal "${connector_url}")\" .
<${marker_uri}> <urn:edc:lastChangedAt> \"${changed_at}\" .
<${marker_uri}> <urn:edc:assets> \"${assets_count}\" .
<${marker_uri}> <urn:edc:policies> \"${policies_count}\" .
<${marker_uri}> <urn:edc:contracts> \"${contracts_count}\" .
<${marker_uri}> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <urn:edc:CatalogSync> .
} }"

  sparql_update "${update}"
  echo "Ingested ${connector_name}: assets=${assets_count}, policies=${policies_count}, contracts=${contracts_count}; +${inserted} -${removed} triples"
  # Which ones, by subject and predicate. A run that keeps reporting the same
  # difference is not converging, and a count alone cannot say why. Objects are
  # left out: the catalog is public but the log does not need to carry it.
  #
  # head reads the file and jq consumes what head gives it, rather than jq
  # writing into a head that stops listening. With pipefail the second shape
  # kills the run with SIGPIPE as soon as the difference is longer than the
  # pipe buffer - after the update has already been written, so the catalogue
  # is correct and the run reports failure. It survived until now because a
  # small difference fits in the buffer before head exits.
  if [[ "${FEDERATION_LOG_CHANGES:-true}" == true ]]; then
    head -20 "${to_insert}" | jq -r '"  + \(.s) \(.p)"'
    head -20 "${to_delete}" | jq -r '"  - \(.s) \(.p)"'
  fi
  rm -f "${current_file}" "${current_file}.sorted" "${DESIRED_FILE}.sorted" \
    "${to_insert}" "${to_delete}"
}

render_triple() {
  # Reads one model line on stdin and prints it as a SPARQL triple pattern.
  jq -r '
    if .t == "uri" then "<\(.s)> <\(.p)> <\(.o)> ."
    else "<\(.s)> <\(.p)> \"\(.o | gsub("\\\\"; "\\\\") | gsub("\""; "\\\"")
      | gsub("\n"; "\\n") | gsub("\r"; "\\r") | gsub("\t"; "\\t"))\" ."
    end'
}

normalize_positive_int() {
  local value="$1"
  local fallback="$2"
  if [[ "${value}" =~ ^[0-9]+$ ]] && [[ "${value}" -gt 0 ]]; then
    echo "${value}"
  else
    echo "${fallback}"
  fi
}

is_truthy() {
  case "${1:-}" in
    1|true|TRUE|yes|YES|y|Y) return 0 ;;
    *) return 1 ;;
  esac
}

FEDERATION_FETCH_RETRIES="$(normalize_positive_int "${FEDERATION_FETCH_RETRIES}" 5)"
FEDERATION_FETCH_RETRY_DELAY_SECONDS="$(normalize_positive_int "${FEDERATION_FETCH_RETRY_DELAY_SECONDS}" 1)"

ensure_dataset() {
  local datasets_json
  datasets_json=$(curl -fsS -u "${FUSEKI_ADMIN_USER}:${FUSEKI_ADMIN_PASSWORD}" "${FUSEKI_BASE_URL}/\$/datasets")
  if echo "${datasets_json}" | grep -q "\"/${FUSEKI_DATASET}\""; then
    return
  fi

  curl -fsS -X POST \
    -u "${FUSEKI_ADMIN_USER}:${FUSEKI_ADMIN_PASSWORD}" \
    "${FUSEKI_BASE_URL}/\$/datasets" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    --data "dbType=tdb2&dbName=${FUSEKI_DATASET}" >/dev/null
}

keycloak_get_admin_token() {
  if [[ -n "${KEYCLOAK_ADMIN_TOKEN}" ]]; then
    echo "${KEYCLOAK_ADMIN_TOKEN}"
    return
  fi

  if [[ -z "${KEYCLOAK_ADMIN_USER}" || -z "${KEYCLOAK_ADMIN_PASSWORD}" ]]; then
    echo ""
    return
  fi

  local resp token
  resp=$(curl -sS -X POST \
    "${KEYCLOAK_URL}/realms/master/protocol/openid-connect/token" \
    -H 'Content-Type: application/x-www-form-urlencoded' \
    --data-urlencode 'grant_type=password' \
    --data-urlencode 'client_id=admin-cli' \
    --data-urlencode "username=${KEYCLOAK_ADMIN_USER}" \
    --data-urlencode "password=${KEYCLOAK_ADMIN_PASSWORD}" || true)

  token=$(echo "${resp}" | jq -r '.access_token // empty')
  if [[ -z "${token}" ]]; then
    echo ""
    return
  fi

  KEYCLOAK_ADMIN_TOKEN="${token}"
  echo "${KEYCLOAK_ADMIN_TOKEN}"
}

keycloak_get_client_secret() {
  local client_id="$1"
  local admin_token client_query client_internal_id secret_resp secret

  admin_token=$(keycloak_get_admin_token)
  if [[ -z "${admin_token}" ]]; then
    echo ""
    return
  fi

  client_query=$(curl -sS \
    -H "Authorization: Bearer ${admin_token}" \
    "${KEYCLOAK_URL}/admin/realms/${KEYCLOAK_REALM}/clients?clientId=${client_id}" || true)

  client_internal_id=$(echo "${client_query}" | jq -r '.[0].id // empty')
  if [[ -z "${client_internal_id}" ]]; then
    echo ""
    return
  fi

  secret_resp=$(curl -sS \
    -H "Authorization: Bearer ${admin_token}" \
    "${KEYCLOAK_URL}/admin/realms/${KEYCLOAK_REALM}/clients/${client_internal_id}/client-secret" || true)

  secret=$(echo "${secret_resp}" | jq -r '.value // empty')
  echo "${secret}"
}

keycloak_ensure_service_account_read_role() {
  local client_id="$1"
  local admin_token client_query client_internal_id service_account role_repr status

  if ! is_truthy "${FEDERATION_ENSURE_SERVICE_ACCOUNT_READ_ROLE}"; then
    return
  fi

  admin_token=$(keycloak_get_admin_token)
  if [[ -z "${admin_token}" ]]; then
    return
  fi

  client_query=$(curl -sS \
    -H "Authorization: Bearer ${admin_token}" \
    "${KEYCLOAK_URL}/admin/realms/${KEYCLOAK_REALM}/clients?clientId=${client_id}" || true)

  client_internal_id=$(echo "${client_query}" | jq -r '.[0].id // empty')
  if [[ -z "${client_internal_id}" ]]; then
    echo "[federator] WARN Keycloak client '${client_id}' not found; cannot ensure service-account role" >&2
    return
  fi

  service_account=$(curl -sS \
    -H "Authorization: Bearer ${admin_token}" \
    "${KEYCLOAK_URL}/admin/realms/${KEYCLOAK_REALM}/clients/${client_internal_id}/service-account-user" || true)

  local service_account_id
  service_account_id=$(echo "${service_account}" | jq -r '.id // empty')
  if [[ -z "${service_account_id}" ]]; then
    echo "[federator] WARN Keycloak client '${client_id}' has no service account; cannot ensure read role" >&2
    return
  fi

  role_repr=$(curl -sS \
    -H "Authorization: Bearer ${admin_token}" \
    "${KEYCLOAK_URL}/admin/realms/${KEYCLOAK_REALM}/roles/${FEDERATION_SERVICE_ACCOUNT_READ_ROLE}" || true)

  if ! echo "${role_repr}" | jq -e '.id and .name' >/dev/null 2>&1; then
    echo "[federator] WARN Keycloak role '${FEDERATION_SERVICE_ACCOUNT_READ_ROLE}' not found; cannot ensure service-account role" >&2
    return
  fi

  status=$(curl -sS -o /dev/null -w '%{http_code}' -X POST \
    -H "Authorization: Bearer ${admin_token}" \
    -H 'Content-Type: application/json' \
    -d "[${role_repr}]" \
    "${KEYCLOAK_URL}/admin/realms/${KEYCLOAK_REALM}/users/${service_account_id}/role-mappings/realm" || true)

  if [[ "${status}" != "204" && "${status}" != "409" ]]; then
    echo "[federator] WARN could not ensure '${FEDERATION_SERVICE_ACCOUNT_READ_ROLE}' for '${client_id}' service account (HTTP ${status})" >&2
  fi
}

keycloak_get_client_token() {
  local client_id="$1"
  local client_secret="$2"
  local token_resp token

  token_resp=$(curl -sS -X POST \
    "${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/token" \
    -H 'Content-Type: application/x-www-form-urlencoded' \
    --data-urlencode 'grant_type=client_credentials' \
    --data-urlencode "client_id=${client_id}" \
    --data-urlencode "client_secret=${client_secret}" || true)

  token=$(echo "${token_resp}" | jq -r '.access_token // empty')
  echo "${token}"
}

# El catalogo publico de un nodo remoto, partido en las tres listas que el
# resto del guion ya sabe procesar.
#
# Un nodo remoto no se lee por su API de gestion: esa superficie no se publica,
# y aunque se publicara haria falta una credencial en el Keycloak de la otra
# organizacion. Lo que se lee es /api/v1/catalog, que es publico, de solo
# lectura y no lleva ni usuarios ni solicitudes ni el registro de operaciones.
#
# Devuelve 0 si trajo el catalogo entero, distinto de 0 si no; quien llama
# conserva entonces el grafo anterior, que es lo que hace que un nodo caido no
# vacie su propia oferta de la vista de los demas.
fetch_remote_catalog() {
  local base_url="$1" assets_file="$2" policies_file="$3" contracts_file="$4"
  local response body status attempt=0

  while [[ ${attempt} -lt "${FEDERATION_FETCH_RETRIES}" ]]; do
    response=$(curl -sS --max-time 20       -w $'
HTTP_STATUS:%{http_code}'       "${base_url}/api/v1/catalog" || true)
    body=$(printf "%s" "${response}" | sed '$d')
    status=$(printf "%s" "${response}" | sed -n '$s/^HTTP_STATUS://p')

    if [[ "${status}" == "200" ]] && jq -e 'has("assets")' <<<"${body}" >/dev/null 2>&1; then
      jq -c '.assets // []'   <<<"${body}" > "${assets_file}"
      jq -c '.policies // []' <<<"${body}" > "${policies_file}"
      jq -c '.contracts // []'<<<"${body}" > "${contracts_file}"
      return 0
    fi

    attempt=$((attempt + 1))
    [[ ${attempt} -lt "${FEDERATION_FETCH_RETRIES}" ]] && sleep "${FEDERATION_FETCH_RETRY_DELAY_SECONDS}"
  done

  echo "[federator] WARN ${base_url}/api/v1/catalog no contesto (ultimo estado: ${status:-sin respuesta})" >&2
  return 12
}

fetch_connector_json_to_file() {
  local base_url="$1"
  local bearer_token="$2"
  local path="$3"
  local output_file="$4"

  local response body status
  local attempt=0

  while [[ ${attempt} -lt "${FEDERATION_FETCH_RETRIES}" ]]; do
    response=$(curl -sS \
      -H "Authorization: Bearer ${bearer_token}" \
      -w $'\nHTTP_STATUS:%{http_code}' \
      "${base_url}${path}" || true)

    body=$(printf "%s" "${response}" | sed '$d')
    status=$(printf "%s" "${response}" | sed -n '$s/^HTTP_STATUS://p')

    if [[ "${status}" == "200" ]]; then
      if echo "${body}" | jq -e 'type == "array"' >/dev/null 2>&1; then
        printf "%s" "${body}" > "${output_file}"
        return 0
      fi
      echo "[federator] WARN ${base_url}${path} returned non-array JSON; keeping previous graph" >&2
      printf "[]" > "${output_file}"
      return 11
    fi

    if [[ "${status}" == "401" || "${status}" == "403" ]]; then
      echo "[federator] WARN ${base_url}${path} returned ${status} (auth/roles)" >&2
      printf "[]" > "${output_file}"
      return 10
    fi

    attempt=$((attempt + 1))
    if [[ ${attempt} -lt "${FEDERATION_FETCH_RETRIES}" ]]; then
      sleep "${FEDERATION_FETCH_RETRY_DELAY_SECONDS}"
    fi
  done

  echo "[federator] WARN ${base_url}${path} unreachable after retries" >&2
  printf "[]" > "${output_file}"
  return 12
}

ingest_connector() {
  local connector_name="$1"
  local connector_url="$2"
  local connector_client_id="$3"
  local connector_client_secret="$4"
  local connector_role="${5:-provider}"
  # El nodo propio se lee por la API de gestion de su conector, con la cuenta
  # de servicio de su Keycloak. Uno remoto, por su catalogo publico.
  local connector_local="${6:-false}"

  if [[ -z "${connector_name}" || -z "${connector_url}" ]]; then
    return
  fi
  # Declared here rather than in main: a connector without a URL is not
  # declared at all, and counting it would make an unconfigured deployment
  # look like a broken one.
  FEDERATION_DECLARED+=("${connector_name}")
  [[ "${connector_role}" == "provider" ]] && FEDERATION_PROVIDERS+=("${connector_name}")

  local connector_token=""
  if [[ "${connector_local}" == "true" ]]; then
    if [[ -z "${connector_client_secret}" ]]; then
      connector_client_secret=$(keycloak_get_client_secret "${connector_client_id}")
    fi

    if [[ -z "${connector_client_secret}" ]]; then
      echo "[federator] WARN missing client secret for ${connector_name} (${connector_client_id}); skipping" >&2
      FEDERATION_UNAVAILABLE+=("${connector_name}")
      return
    fi

    keycloak_ensure_service_account_read_role "${connector_client_id}"

    connector_token=$(keycloak_get_client_token "${connector_client_id}" "${connector_client_secret}")
    if [[ -z "${connector_token}" ]]; then
      echo "[federator] WARN cannot obtain token for ${connector_name} (${connector_client_id}); skipping" >&2
      FEDERATION_UNAVAILABLE+=("${connector_name}")
      return
    fi
  fi

  local graph_iri="${GRAPH_BASE_IRI}/${connector_name}"
  local assets_file policies_file contracts_file
  assets_file="$(mktemp)"
  policies_file="$(mktemp)"
  contracts_file="$(mktemp)"
  # The catalog this run wants, built locally. Nothing reaches Fuseki until
  # it has been compared with what is already there.
  DESIRED_FILE="$(mktemp)"

  local assets_status=0
  local policies_status=0
  local contracts_status=0
  if [[ "${connector_local}" == "true" ]]; then
    fetch_connector_json_to_file "${connector_url}" "${connector_token}" "/management/v3/assets" "${assets_file}" || assets_status=$?
    fetch_connector_json_to_file "${connector_url}" "${connector_token}" "/management/v3/policydefinitions" "${policies_file}" || policies_status=$?
    fetch_connector_json_to_file "${connector_url}" "${connector_token}" "/management/v3/contractdefinitions" "${contracts_file}" || contracts_status=$?
  else
    fetch_remote_catalog "${connector_url}" "${assets_file}" "${policies_file}" "${contracts_file}" || assets_status=$?
  fi

  if [[ "${assets_status}" -ne 0 || "${policies_status}" -ne 0 || "${contracts_status}" -ne 0 ]]; then
    echo "[federator] WARN ${connector_name}: incomplete sync (assets=${assets_status}, policies=${policies_status}, contracts=${contracts_status}); keeping previous graph <${graph_iri}>" >&2
    # Contado como no disponible, que es lo que hace que la consola lo marque
    # y conserve su ultima fecha correcta. Sin esta linea el nodo se quedaba
    # como «arriba» y «sin ofertas», que se lee como un nodo que ha retirado
    # su catalogo y no como uno que no contesta -- son cosas distintas y el
    # operador tiene que poder distinguirlas.
    FEDERATION_UNAVAILABLE+=("${connector_name}")
    rm -f "${assets_file}" "${policies_file}" "${contracts_file}" "${DESIRED_FILE}"
    return
  fi

  local assets_count=0
  local policies_count=0
  local contracts_count=0

  while IFS= read -r row; do
    [[ -z "${row}" ]] && continue
    local asset_id name base_url description language publisher license_url access_rights theme keywords media_type delivery_mode
    asset_id=$(echo "${row}" | jq -r '.id // .["@id"] // empty')
    [[ -z "${asset_id}" ]] && continue
    name=$(echo "${row}" | jq -r '.properties["dct:title"] // .properties.name // empty')
    base_url=$(echo "${row}" | jq -r '.properties.objectUrl // .dataAddress.baseUrl // empty')
    description=$(echo "${row}" | jq -r '.properties["dct:description"] // .properties.description // empty')
    language=$(echo "${row}" | jq -r '.properties["dct:language"] // .properties.language // empty')
    publisher=$(echo "${row}" | jq -r '.properties["dct:publisher"] // .properties.publisher // empty')
    license_url=$(echo "${row}" | jq -r '.properties["dct:license"] // .properties.licenseUrl // .properties.license // empty')
    access_rights=$(echo "${row}" | jq -r '.properties["dct:accessRights"] // .properties.accessRights // empty')
    theme=$(echo "${row}" | jq -r '.properties["dcat:theme"] // .properties.theme // empty')
    keywords=$(echo "${row}" | jq -r 'if (.properties["dcat:keyword"] // .properties.keywords) | type == "array" then (.properties["dcat:keyword"] // .properties.keywords | join(", ")) else (.properties["dcat:keyword"] // .properties.keywords // empty) end')
    media_type=$(echo "${row}" | jq -r '.properties["dcat:mediaType"] // .properties.contenttype // .properties.contentType // empty')
    delivery_mode=$(echo "${row}" | jq -r '.properties["ods:deliveryMode"] // .properties.deliveryMode // empty')

    # De que conector es esta oferta. Un nodo tiene un conector por
    # participante, asi que atribuirla al nodo hacia que a todo el mundo le
    # saliera todo como propio y no se pudiera negociar nada dentro del nodo.
    # El grafo con nombre sigue siendo por nodo: lo que cambia es a quien se
    # atribuye cada oferta dentro de el.
    local asset_connector
    asset_connector=$(echo "${row}" | jq -r '.properties["ods:connectorId"] // empty')
    [[ -z "${asset_connector}" ]] && asset_connector="${connector_name}"

    local asset_uri
    asset_uri="urn:dataspace:${connector_name}:asset:${asset_id}"

    emit_iri "${asset_uri}" "http://www.w3.org/1999/02/22-rdf-syntax-ns#type" "urn:edc:Asset"
    emit_literal "${asset_uri}" "urn:edc:assetId" "${asset_id}"
    emit_literal "${asset_uri}" "urn:edc:connector" "${asset_connector}"
    emit_literal "${asset_uri}" "urn:edc:name" "${name}"
    emit_literal "${asset_uri}" "urn:edc:description" "${description}"
    emit_literal "${asset_uri}" "urn:edc:language" "${language}"
    emit_literal "${asset_uri}" "urn:edc:publisher" "${publisher}"
    emit_literal "${asset_uri}" "urn:edc:licenseUrl" "${license_url}"
    emit_literal "${asset_uri}" "urn:edc:accessRights" "${access_rights}"
    emit_literal "${asset_uri}" "urn:edc:theme" "${theme}"
    emit_literal "${asset_uri}" "urn:edc:keywords" "${keywords}"
    emit_literal "${asset_uri}" "urn:edc:mediaType" "${media_type}"
    emit_literal "${asset_uri}" "urn:edc:deliveryMode" "${delivery_mode}"
    emit_literal "${asset_uri}" "urn:edc:baseUrl" "${base_url}"

    # The same asset, in DCAT. These are the terms the shapes in
    # generated/vocabularies/dcat-ap-mydataspace/1.0.0/shapes.ttl target, so
    # the federated graph is now describable by the same profile the
    # publication side validates against.
    emit_iri "${asset_uri}" "${RDF_TYPE}" "${DCAT_NS}Dataset"
    emit_present_literal "${asset_uri}" "${DCT_NS}identifier" "${asset_id}"
    emit_present_literal "${asset_uri}" "${DCT_NS}title" "${name}"
    emit_present_literal "${asset_uri}" "${DCT_NS}description" "${description}"
    emit_present_literal "${asset_uri}" "${DCT_NS}language" "${language}"
    emit_present_literal "${asset_uri}" "${DCT_NS}publisher" "${publisher}"
    emit_present_literal "${asset_uri}" "${DCT_NS}accessRights" "${access_rights}"
    emit_present_literal "${asset_uri}" "${DCAT_NS}theme" "${theme}"
    emit_present_literal "${asset_uri}" "${DCAT_NS}mediaType" "${media_type}"
    emit_present_literal "${asset_uri}" "${ODS_NS}deliveryMode" "${delivery_mode}"
    if [[ "${license_url}" == http://* || "${license_url}" == https://* ]]; then
      emit_iri "${asset_uri}" "${DCT_NS}license" "${license_url}"
    else
      emit_present_literal "${asset_uri}" "${DCT_NS}license" "${license_url}"
    fi

    # One keyword per triple. They arrive joined for the URN half, which is
    # why dcat:keyword could never have been a straight rename.
    if [[ -n "${keywords}" ]]; then
      local keyword
      while IFS= read -r keyword; do
        keyword="${keyword#"${keyword%%[![:space:]]*}"}"
        keyword="${keyword%"${keyword##*[![:space:]]}"}"
        [[ -n "${keyword}" ]] || continue
        emit_literal "${asset_uri}" "${DCAT_NS}keyword" "${keyword}"
      # With no trailing newline the last keyword is read and dropped.
      done < <(printf '%s\n' "${keywords}" | tr ',' "\n")
    fi

    # Where the data is actually obtained. dcat:accessURL belongs to a
    # distribution, not to the dataset, and Req.-BB-DSO-005 asks the catalogue
    # to carry the means of access.
    if [[ "${base_url}" == http://* || "${base_url}" == https://* ]]; then
      local distribution_uri="${asset_uri}:distribution"
      emit_iri "${asset_uri}" "${DCAT_NS}distribution" "${distribution_uri}"
      emit_iri "${distribution_uri}" "${RDF_TYPE}" "${DCAT_NS}Distribution"
      emit_iri "${distribution_uri}" "${DCAT_NS}accessURL" "${base_url}"
      emit_present_literal "${distribution_uri}" "${DCAT_NS}mediaType" "${media_type}"
    fi
    assets_count=$((assets_count + 1))
  done < <(jq -c 'if type=="array" then .[] else empty end' "${assets_file}")

  while IFS= read -r row; do
    [[ -z "${row}" ]] && continue
    local policy_id policy_name license_url
    policy_id=$(echo "${row}" | jq -r '.id // .["@id"] // empty')
    [[ -z "${policy_id}" ]] && continue
    policy_name=$(echo "${row}" | jq -r '.policy.name // .policy.title // empty')
    license_url=$(echo "${row}" | jq -r '.policy.licenseUrl // .policy.license.url // empty')

    local policy_uri
    policy_uri="urn:dataspace:${connector_name}:policy:${policy_id}"

    emit_iri "${policy_uri}" "http://www.w3.org/1999/02/22-rdf-syntax-ns#type" "urn:edc:Policy"
    emit_literal "${policy_uri}" "urn:edc:policyId" "${policy_id}"
    emit_literal "${policy_uri}" "urn:edc:connector" "${connector_name}"
    emit_literal "${policy_uri}" "urn:edc:policyName" "${policy_name}"
    emit_literal "${policy_uri}" "urn:edc:licenseUrl" "${license_url}"
    policies_count=$((policies_count + 1))
  done < <(jq -c 'if type=="array" then .[] else empty end' "${policies_file}")

  while IFS= read -r row; do
    [[ -z "${row}" ]] && continue
    local contract_id access_policy_id contract_policy_id selected_asset_id
    contract_id=$(echo "${row}" | jq -r '.id // .["@id"] // empty')
    [[ -z "${contract_id}" ]] && continue
    access_policy_id=$(echo "${row}" | jq -r '.accessPolicyId // empty')
    contract_policy_id=$(echo "${row}" | jq -r '.contractPolicyId // empty')
    # first() inside jq rather than head outside it. A contract definition
    # with two selectors on id would make jq write a second line into a head
    # that had already gone, and the SIGPIPE would abort the run through the
    # command substitution. first() stops on its own and emits nothing when
    # there is no match, which is the case the empty check below handles.
    selected_asset_id=$(echo "${row}" | jq -r 'first(.assetsSelector[]? | select((.leftOperand=="id") or (.operandLeft=="https://w3id.org/edc/v0.0.1/ns/id")) | (.rightOperand // .operandRight // empty)) // empty')

    local contract_uri access_policy_uri contract_policy_uri selected_asset_uri
    contract_uri="urn:dataspace:${connector_name}:contract:${contract_id}"
    access_policy_uri="urn:dataspace:${connector_name}:policy:${access_policy_id}"
    contract_policy_uri="urn:dataspace:${connector_name}:policy:${contract_policy_id}"
    selected_asset_uri="urn:dataspace:${connector_name}:asset:${selected_asset_id}"

    emit_iri "${contract_uri}" "http://www.w3.org/1999/02/22-rdf-syntax-ns#type" "urn:edc:ContractDefinition"
    emit_literal "${contract_uri}" "urn:edc:contractId" "${contract_id}"
    emit_iri "${contract_uri}" "urn:edc:accessPolicy" "${access_policy_uri}"
    emit_iri "${contract_uri}" "urn:edc:contractPolicy" "${contract_policy_uri}"
    emit_iri "${contract_uri}" "urn:edc:asset" "${selected_asset_uri}"
    emit_literal "${contract_uri}" "urn:edc:connector" "${connector_name}"
    contracts_count=$((contracts_count + 1))
  done < <(jq -c 'if type=="array" then .[] else empty end' "${contracts_file}")

  if [[ "${assets_count}" -eq 0 ]] && ! is_truthy "${FEDERATION_PUBLISH_EMPTY_CATALOG}"; then
    if [[ "${connector_role}" == "provider" ]]; then
      echo "[federator] WARN ${connector_name}: fetched zero assets; keeping previous graph <${graph_iri}> (set FEDERATION_PUBLISH_EMPTY_CATALOG=true to publish empty catalogs)" >&2
    else
      echo "[federator] ${connector_name}: consumer, nothing to publish" >&2
    fi
    rm -f "${assets_file}" "${policies_file}" "${contracts_file}" "${DESIRED_FILE}"
    # Only a provider can be empty. A consumer fetching zero assets is doing
    # what it is for, and counting it as an anomaly is how every run of this
    # federation reported a missing participant that was never missing.
    if [[ "${connector_role}" == "provider" ]]; then
      FEDERATION_EMPTY+=("${connector_name}")
    fi
    return
  fi

  FEDERATION_CONTRIBUTING+=("${connector_name}")
  sync_graph "${graph_iri}" "${connector_name}" "${connector_url}" \
    "${assets_count}" "${policies_count}" "${contracts_count}"

  rm -f "${assets_file}" "${policies_file}" "${contracts_file}" "${DESIRED_FILE}"
}

declare_registry_connectors() {
  # El catálogo declara lo que dice el registro de participantes.
  #
  # Antes declaraba tres conectores fijos que venían de estas variables de
  # entorno, así que un alta podía crear un participante -- con su grupo de
  # Keycloak y su consola -- que el catálogo no nombraba en ninguna parte. Esa
  # era la tercera fuente de verdad: el 23 de agosto de 2026 ningún conector
  # estaba a la vez en el catálogo, el registro y Keycloak en ningún dominio.
  #
  # Un conector del registro sin EDC propio se declara como consumidor: no se
  # le pide catálogo, y sale en federation_connector con outcome=consumer, que
  # es exactamente lo que es. No se inventa ninguna URL para él.
  local url payload connector_name already
  url="${ONBOARDING_API_URL:-http://onboarding-api:8092}/api/v1/participants"
  payload=$(curl -fsS --max-time 20 "${url}" 2>/dev/null) || {
    echo "[federator] WARN registro de participantes ilegible en ${url}; se declara sólo lo configurado" >&2
    return 0
  }
  while read -r connector_name; do
    [[ -n "${connector_name}" ]] || continue
    already=no
    for declared in "${FEDERATION_DECLARED[@]:-}"; do
      if [[ "${declared}" == "${connector_name}" ]]; then
        already=yes
        break
      fi
    done
    [[ "${already}" == yes ]] && continue
    FEDERATION_DECLARED+=("${connector_name}")
  done < <(printf '%s' "${payload}" | jq -r '.items[]?.attributes.connectorId // empty' | sort -u)
}

# Los nodos conocidos del propio nodo, uno por linea, en el formato que
# ingest_connector espera. Un fichero ilegible o con una lista vacia no es un
# error: es un nodo que todavia no conoce a nadie mas, y su propio catalogo
# tiene que federarse igual.
ingest_known_nodes() {
  local nodes_json name url
  nodes_json="$(jq -c '.[]?' "${FEDERATION_NODES_FILE}" 2>/dev/null || true)"
  while IFS= read -r node; do
    [[ -z "${node}" ]] && continue
    name="$(jq -r '.id // empty' <<<"${node}")"
    url="$(jq -r '.baseUrl // empty' <<<"${node}")"
    [[ -z "${name}" || -z "${url}" ]] && continue
    # Cada nodo, su propio grafo con nombre: es lo que permite retirar uno sin
    # tocar el resto del almacen.
    ingest_connector "${name}" "${url}"       "$(jq -r '.clientId // empty' <<<"${node}")"       "$(jq -r '.clientSecret // empty' <<<"${node}")"       "$(jq -r '.role // "provider"' <<<"${node}")"       "$(jq -r 'if .local then "true" else "false" end' <<<"${node}")"
  done <<< "${nodes_json}"
}

main() {
  local connector_name outcome empty unavailable
  ensure_dataset
  if [[ -n "${FEDERATION_NODES_FILE}" ]]; then
    ingest_known_nodes
  else
    ingest_connector "${CONNECTOR1_NAME}" "${CONNECTOR1_URL}" "${CONNECTOR1_CLIENT_ID}" "${CONNECTOR1_CLIENT_SECRET}" "${CONNECTOR1_ROLE}" "true"
    ingest_connector "${CONNECTOR2_NAME}" "${CONNECTOR2_URL}" "${CONNECTOR2_CLIENT_ID}" "${CONNECTOR2_CLIENT_SECRET}" "${CONNECTOR2_ROLE}" "true"
    if [[ -n "${CONNECTOR3_NAME}" && -n "${CONNECTOR3_URL}" ]]; then
      ingest_connector "${CONNECTOR3_NAME}" "${CONNECTOR3_URL}" "${CONNECTOR3_CLIENT_ID}" "${CONNECTOR3_CLIENT_SECRET}" "${CONNECTOR3_ROLE}" "true"
    fi
  fi
  declare_registry_connectors

  # One line that can be compared with the registry. A connector declared here
  # and contributing nothing is either a connector with nothing to publish -
  # which is a fact about the deployment, not a fault - or one that has stopped
  # publishing. Both need saying; only the reader can tell them apart, and the
  # reader could not see either before.
  printf 'federation_summary declared=%s providers=%s contributing=%s empty=%s unavailable=%s\n' \
    "${#FEDERATION_DECLARED[@]}" "${#FEDERATION_PROVIDERS[@]}" \
    "${#FEDERATION_CONTRIBUTING[@]}" "${#FEDERATION_EMPTY[@]}" "${#FEDERATION_UNAVAILABLE[@]}"
  for connector_name in "${FEDERATION_DECLARED[@]}"; do
    # A connector that consumes is not a provider that failed. Written as an
    # if rather than a && chain: under set -e a failing test as the last
    # command of a loop body is a way to leave the script without meaning to.
    outcome=consumer
    for provider in "${FEDERATION_PROVIDERS[@]:-}"; do
      if [[ "${provider}" == "${connector_name}" ]]; then
        outcome=contributing
        break
      fi
    done
    if [[ "${outcome}" != "consumer" ]]; then
      for empty in "${FEDERATION_EMPTY[@]:-}"; do
        if [[ "${empty}" == "${connector_name}" ]]; then
          outcome=empty
        fi
      done
    fi
    for unavailable in "${FEDERATION_UNAVAILABLE[@]:-}"; do
      [[ "${unavailable}" == "${connector_name}" ]] && outcome=unavailable
    done
    printf 'federation_connector=%s outcome=%s
' "${connector_name}" "${outcome}"
  done

  echo "Done. Fuseki dataset: ${FUSEKI_DATASET}"
  echo "SPARQL endpoint: ${FUSEKI_BASE_URL}/${FUSEKI_DATASET}/query"
  echo "Example query:"
  echo "  SELECT ?connector ?assetId ?name WHERE {"
  echo "    GRAPH ?g {"
  echo "      ?a <urn:edc:connector> ?connector ;"
  echo "         <urn:edc:assetId> ?assetId ;"
  echo "         <urn:edc:name> ?name ."
  echo "    }"
  echo "  } ORDER BY ?connector ?assetId"
}

# Sourcing the script exposes its functions without federating anything, so
# the delta logic can be exercised directly by the tests.
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
