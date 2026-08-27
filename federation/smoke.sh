#!/usr/bin/env bash
# Prove the bundle, end to end, on a machine that has nothing installed.
#
# Stands up the catalogue store, points the federator at a stub data space,
# and then asks the graph what it holds. If this passes, the quickstart in the
# README is true; if it fails, the README is fiction.
#
#   ./smoke.sh
#
# Needs docker, python3, curl and jq. Leaves nothing behind.
set -Eeuo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$here"

export FUSEKI_ADMIN_PASSWORD="${FUSEKI_ADMIN_PASSWORD:-smoke-only}"
export FUSEKI_DATASET="${FUSEKI_DATASET:-catalogue}"
export CONNECTOR1_NAME=connector-1
export CONNECTOR1_URL=http://host.docker.internal:8099
export CONNECTOR1_CLIENT_SECRET=stub-secret
export KEYCLOAK_URL=http://host.docker.internal:8099
export FEDERATION_INTERVAL_SECONDS=3600

stub_pid=""
cleanup() {
  set +e
  [[ -n "$stub_pid" ]] && kill "$stub_pid" 2>/dev/null
  docker compose down -v >/dev/null 2>&1
}
trap cleanup EXIT

echo "[smoke] a data space of one connector"
python3 smoke/stub_dataspace.py --port 8099 &
stub_pid=$!
for _ in $(seq 1 30); do
  curl -fsS "http://127.0.0.1:8099/management/v3/assets" >/dev/null 2>&1 && break
  sleep 1
done
curl -fsS "http://127.0.0.1:8099/management/v3/assets" >/dev/null

echo "[smoke] the catalogue store"
docker compose up -d fuseki
for _ in $(seq 1 60); do
  curl -fsS "http://127.0.0.1:3030/$/ping" >/dev/null 2>&1 && break
  sleep 2
done
curl -fsS "http://127.0.0.1:3030/$/ping" >/dev/null

echo "[smoke] federating"
docker compose run --rm --no-deps \
  -e CONNECTOR1_URL -e KEYCLOAK_URL -e CONNECTOR1_CLIENT_SECRET \
  federator /bin/sh -c '
    apk add --no-cache bash curl jq >/dev/null
    cp /catalejo/federator/federate-catalogues.sh /tmp/federate.sh
    chmod +x /tmp/federate.sh
    /bin/bash /tmp/federate.sh
  '

echo "[smoke] asking the graph what it holds"
datasets=$(
  curl -fsS -H "Accept: application/sparql-results+json" \
    --data-urlencode 'query=SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE { GRAPH ?g { ?s a <http://www.w3.org/ns/dcat#Dataset> } }' \
    "http://127.0.0.1:3030/${FUSEKI_DATASET}/query" |
    python3 -c 'import json,sys; print(json.load(sys.stdin)["results"]["bindings"][0]["n"]["value"])'
)
echo "[smoke] dcat:Dataset in the graph: ${datasets}"
[[ "${datasets}" -ge 1 ]] || {
  echo "[smoke] the federation wrote no dataset" >&2
  exit 1
}

echo "[smoke] validating a record against the profile"
python3 -m pip install --quiet --disable-pip-version-check -r requirements.txt
PYTHONPATH=src python3 -m catalejo.cli \
  vocabularies/dcat-ap/1.0.0/shapes.ttl smoke/conforming.json >/dev/null
echo "[smoke] a conforming record is accepted"

if PYTHONPATH=src python3 -m catalejo.cli \
  vocabularies/dcat-ap/1.0.0/shapes.ttl smoke/failing.json >/dev/null 2>&1; then
  echo "[smoke] a record outside the profile was accepted; the shapes are not being applied" >&2
  exit 1
fi
echo "[smoke] a record outside the profile is refused"

echo "[smoke] the bundle works"
