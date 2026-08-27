#!/usr/bin/env bash
# Despliega My Open Dataspace en el Kubernetes de Docker Desktop.
#
# Uso (desde la carpeta del repositorio, con el .env ya creado):
#   ./k8s/desplegar.sh
#
# Hace, por orden:
#   1. Para la version de docker compose (libera el puerto 8080).
#   2. Construye las imagenes del nodo desde este codigo y, si el cluster no
#      comparte las imagenes de Docker, se las copia.
#   3. Crea la configuracion y las contrasenas a partir del .env.
#   4. Sube los ficheros de deploy/ y db/ (Caddy, Keycloak, SQL inicial).
#   5. Aplica k8s/manifiestos.yaml y espera a que todo este en marcha.
#   6. Abre el nodo en http://localhost:8080 (deja la terminal abierta).
set -euo pipefail

NS=my-open-dataspace
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
cd "$RAIZ"

paso() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
falla() { printf '\n\033[31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

[ -f .env ] || falla "no hay .env en $RAIZ. Ejecuta antes ./install.sh (o copia .env.example a .env)."
command -v kubectl >/dev/null || falla "no encuentro kubectl. Activa Kubernetes en Docker Desktop."

set -a; . ./.env; set +a
: "${ODS_ADMIN_EMAIL:?falta ODS_ADMIN_EMAIL en .env}"
: "${ODS_DB_PASSWORD:?falta ODS_DB_PASSWORD en .env}"
: "${ODS_KEYCLOAK_ADMIN_PASSWORD:?falta ODS_KEYCLOAK_ADMIN_PASSWORD en .env}"
: "${ODS_FUSEKI_ADMIN_PASSWORD:?falta ODS_FUSEKI_ADMIN_PASSWORD en .env}"
PUERTO="${ODS_HTTP_PORT:-8080}"
IMG_APP="${ODS_IMAGE_APP:-myopendataspace/app:dev}"
IMG_CON="${ODS_IMAGE_CONNECTOR:-myopendataspace/connector:dev}"

paso "Usando el Kubernetes de Docker Desktop"
kubectl config use-context docker-desktop >/dev/null || falla "no existe el contexto docker-desktop."
kubectl get nodes >/dev/null || falla "Kubernetes no responde. Comprueba que esta en verde en Docker Desktop."

paso "Parando la version de docker compose (los datos se conservan)"
if [ -n "$(docker ps -q --filter label=com.docker.compose.project=my-open-dataspace)" ]; then
  docker compose stop
else
  echo "no estaba en marcha"
fi

paso "Preparando las imagenes del nodo"
# Las de dev no estan publicadas en ningun registro y tienen que salir del
# codigo de esta carpeta: si no existen, el cluster se queda en ErrImagePull, y
# si son de antes, se despliega lo de antes. Se construyen siempre con la misma
# receta que docker compose; con la cache, si nada ha cambiado son segundos.
# Las de un registro (ghcr.io/...) las descarga el cluster.
for img in "$IMG_APP" "$IMG_CON"; do
  if [[ "$img" == */*/* ]]; then
    echo "  $img (la descarga el cluster del registro)"
  else
    echo "  $img: construyendo con docker compose build (la primera vez, unos minutos)"
    docker compose build "$( [ "$img" = "$IMG_APP" ] && echo app || echo connector )" \
      || falla "no se pudo construir $img"
  fi
done

NODO="$(kubectl get nodes -o jsonpath='{.items[0].metadata.name}')"
if docker ps --format '{{.Names}}' | grep -qx "$NODO"; then
  for img in "$IMG_APP" "$IMG_CON"; do
    docker image inspect "$img" >/dev/null 2>&1 || continue
    echo "  copiando $img al cluster"
    docker save "$img" | docker exec -i "$NODO" ctr -n k8s.io images import - >/dev/null
  done
  # Fuseki solo se publica para AMD64; se carga tal cual para que el cluster no la busque para ARM.
  echo "  stain/jena-fuseki:5.1.0 (AMD64)"
  docker pull --platform linux/amd64 stain/jena-fuseki:5.1.0 >/dev/null
  docker save --platform linux/amd64 stain/jena-fuseki:5.1.0 2>/dev/null \
    | docker exec -i "$NODO" ctr -n k8s.io images import --platform linux/amd64 - >/dev/null \
  || docker save stain/jena-fuseki:5.1.0 \
    | docker exec -i "$NODO" ctr -n k8s.io images import --all-platforms - >/dev/null
else
  echo "  el cluster comparte las imagenes de Docker; no hace falta copiarlas"
fi

aplica() { kubectl apply -f - >/dev/null; }

paso "Creando configuracion y contrasenas"
kubectl create namespace "$NS" --dry-run=client -o yaml | aplica

kubectl -n "$NS" create configmap ods-config --dry-run=client -o yaml \
  --from-literal=ODS_ORG_NAME="${ODS_ORG_NAME:-My Open Dataspace}" \
  --from-literal=ODS_ORG_ID="${ODS_ORG_ID:-}" \
  --from-literal=ODS_ADMIN_EMAIL="$ODS_ADMIN_EMAIL" \
  --from-literal=ODS_LANG="${ODS_LANG:-es}" \
  --from-literal=ODS_PUBLIC_URL="${ODS_PUBLIC_URL:-http://localhost:8080}" \
  --from-literal=ODS_DOMAIN="${ODS_DOMAIN:-}" \
  --from-literal=ODS_TLS="${ODS_TLS:-auto}" \
  --from-literal=ODS_CONNECTOR_ID="${ODS_CONNECTOR_ID:-connector}" \
  --from-literal=ODS_DOWNLOAD_ALLOWED_HOSTS="${ODS_DOWNLOAD_ALLOWED_HOSTS:-localhost}" \
  --from-literal=ODS_REALM="${ODS_REALM:-dataspace}" \
  --from-literal=ODS_SEED_DEMO="${ODS_SEED_DEMO:-true}" \
  --from-literal=ODS_FEDERATION_INTERVAL="${ODS_FEDERATION_INTERVAL:-300}" \
  --from-literal=ODS_SPARQL_PUBLIC="${ODS_SPARQL_PUBLIC:-false}" \
  --from-literal=ODS_IMAGE_CONNECTOR="$IMG_CON" \
  --from-literal=ODS_SMTP_HOST="${ODS_SMTP_HOST:-}" \
  --from-literal=ODS_SMTP_PORT="${ODS_SMTP_PORT:-587}" \
  --from-literal=ODS_SMTP_USER="${ODS_SMTP_USER:-}" \
  | aplica

kubectl -n "$NS" create secret generic ods-secret --dry-run=client -o yaml \
  --from-literal=ODS_DB_PASSWORD="$ODS_DB_PASSWORD" \
  --from-literal=ODS_KEYCLOAK_ADMIN_PASSWORD="$ODS_KEYCLOAK_ADMIN_PASSWORD" \
  --from-literal=ODS_FUSEKI_ADMIN_PASSWORD="$ODS_FUSEKI_ADMIN_PASSWORD" \
  --from-literal=ODS_SMTP_PASSWORD="${ODS_SMTP_PASSWORD:-}" \
  | aplica

paso "Subiendo ficheros de configuracion (Caddy, Keycloak, base de datos)"
kubectl -n "$NS" create configmap ods-db-init --from-file=db/ --dry-run=client -o yaml | aplica
kubectl -n "$NS" create configmap ods-keycloak-realm --from-file=deploy/keycloak/ --dry-run=client -o yaml | aplica
kubectl -n "$NS" create configmap ods-caddy \
  --from-file=Caddyfile=deploy/Caddyfile \
  --from-file=caddy-entrypoint.sh=deploy/caddy-entrypoint.sh \
  --dry-run=client -o yaml | aplica

paso "Aplicando manifiestos"
YA_ESTABA="$(kubectl -n "$NS" get deploy app -o name 2>/dev/null || true)"
# Las imagenes que diga el .env, no las de dev que trae el fichero.
sed -e "s#image: myopendataspace/app:dev#image: ${IMG_APP}#" \
    -e "s#image: myopendataspace/connector:dev#image: ${IMG_CON}#" \
    k8s/manifiestos.yaml | kubectl apply -f -

if [ -n "$YA_ESTABA" ]; then
  # Una configuracion o una imagen :dev nuevas no reinician nada por si
  # solas: sin esto, volver a desplegar dejaba corriendo lo de antes.
  paso "Reiniciando lo que lee la configuracion"
  kubectl -n "$NS" rollout restart deploy/keycloak deploy/connector deploy/app deploy/caddy
fi

paso "Esperando a que arranquen los seis servicios (puede tardar unos minutos la primera vez)"
for d in postgres fuseki keycloak connector app caddy; do
  kubectl -n "$NS" rollout status "deploy/$d" --timeout=600s \
    || falla "$d no arranca. Mira el motivo con: kubectl -n $NS logs deploy/$d"
done

paso "Listo. Abre http://localhost:$PUERTO"
echo "Deja esta ventana abierta mientras lo uses; Ctrl+C para cerrar el acceso."
# port-forward se ata a un pod concreto de Caddy y muere en cuanto ese pod se
# reinicia (otro despliegue, un reinicio de Kubernetes). Se vuelve a abrir
# solo, contra el pod nuevo, hasta que se pulse Ctrl+C.
trap 'echo; echo "Acceso cerrado."; exit 0' INT TERM
while true; do
  kubectl -n "$NS" port-forward svc/caddy "$PUERTO:80" || true
  echo "Se ha perdido la conexion con Caddy; reconectando en 3 s..."
  sleep 3
  kubectl -n "$NS" rollout status deploy/caddy --timeout=300s >/dev/null 2>&1 || true
done
