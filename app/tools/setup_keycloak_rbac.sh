#!/usr/bin/env bash
set -euo pipefail

ENV_FILE=""
# Off by default. This script used to reset the password of every user in its
# matrix on every run, including users it found already there, which is how the
# DataSpaceHealth production E2E account stopped matching the credential in CI
# on 19 August 2026: a bootstrap run reset it to the value that shipped in the
# example env file, and nothing said so. Changing a password someone else set
# is now something you ask for.
RESET_PASSWORDS_REQUESTED=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --reset-passwords)
      RESET_PASSWORDS_REQUESTED=true
      shift
      ;;
    --env-file)
      if [[ $# -lt 2 ]]; then
        echo "ERROR: --env-file requires a path" >&2
        exit 1
      fi
      ENV_FILE="$2"
      shift 2
      ;;
    -h|--help)
      echo "Usage: $0 [--env-file /path/to/file.env] [--reset-passwords]"
      echo "  --reset-passwords  overwrite the password of users that"
      echo "                     already exist, with USER_DEFAULT_PASSWORD"
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument '$1'" >&2
      exit 1
      ;;
  esac
done

if [[ -z "${ENV_FILE}" && -f "./tools/setup_keycloak_rbac.env" ]]; then
  ENV_FILE="./tools/setup_keycloak_rbac.env"
fi

if [[ -n "${ENV_FILE}" ]]; then
  if [[ ! -f "${ENV_FILE}" ]]; then
    echo "ERROR: env file not found: ${ENV_FILE}" >&2
    exit 1
  fi
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi

# The flag wins over the env file, which is read above: an operator who did not
# ask for it on the command line does not get it from a file they inherited.
RESET_PASSWORDS="${RESET_PASSWORDS:-false}"
if [[ "${RESET_PASSWORDS_REQUESTED}" == true ]]; then
  RESET_PASSWORDS=true
fi
if [[ "${RESET_PASSWORDS}" == true && -z "${USER_DEFAULT_PASSWORD:-}" ]]; then
  echo "ERROR: --reset-passwords needs USER_DEFAULT_PASSWORD to be set" >&2
  exit 2
fi

for cmd in curl jq; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: missing dependency '$cmd'" >&2
    exit 1
  fi
done

KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8089}"
ADMIN_REALM="${ADMIN_REALM:-master}"
REALM="${REALM:-dataspace}"
ADMIN_USER="${ADMIN_USER:-admin}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin}"
# No default. A password written here is a password that reaches production
# accounts: the account in USER_MATRIX below is a real one. It is needed to
# create a user that does not exist yet, and to run with --reset-passwords;
# a run that only reconciles groups and roles needs no password at all.
USER_DEFAULT_PASSWORD="${USER_DEFAULT_PASSWORD:-}"

# Formato: usuario|correo|nombre|apellido|grupo1,grupo2
#
# Un solo usuario: el administrador del nodo, con la direccion que quien
# instala ha puesto en ODS_ADMIN_EMAIL. No hay una matriz de cuentas escrita
# aqui dentro -- la de origen traia tres direcciones reales, que es
# exactamente lo que un repositorio publico no puede llevar.
ODS_ADMIN_EMAIL="${ODS_ADMIN_EMAIL:-}"
if [[ -z "${USER_MATRIX:-}" ]]; then
  if [[ -z "${ODS_ADMIN_EMAIL}" ]]; then
    echo "ODS_ADMIN_EMAIL es obligatorio: es la cuenta que administra este nodo." >&2
    exit 1
  fi
  USER_MATRIX="${ODS_ADMIN_EMAIL}|${ODS_ADMIN_EMAIL}|Admin||connector-users,dataspace-users,dataspace-negotiators,dataspace-admins"
fi

# La cuenta de servicio del conector. Una sola: este producto entrega un
# conector, proveedor y consumidor a la vez.
SERVICE_ACCOUNT_CLIENTS="${SERVICE_ACCOUNT_CLIENTS:-edc-connector}"
ONBOARDING_API_URL="${ONBOARDING_API_URL:-http://localhost:8092}"
ONBOARDING_SYNC_PARTICIPANTS="${ONBOARDING_SYNC_PARTICIPANTS:-true}"

ACCESS_TOKEN=""

kc_admin_token() {
  local token_json
  token_json=$(curl -sS -X POST "${KEYCLOAK_URL}/realms/${ADMIN_REALM}/protocol/openid-connect/token" \
    -H 'Content-Type: application/x-www-form-urlencoded' \
    --data-urlencode 'grant_type=password' \
    --data-urlencode 'client_id=admin-cli' \
    --data-urlencode "username=${ADMIN_USER}" \
    --data-urlencode "password=${ADMIN_PASSWORD}")

  ACCESS_TOKEN=$(echo "${token_json}" | jq -r '.access_token // empty')
  if [[ -z "${ACCESS_TOKEN}" ]]; then
    echo "ERROR: unable to obtain Keycloak admin token" >&2
    echo "Response: ${token_json}" >&2
    exit 1
  fi
}

kc_get() {
  local path="$1"
  curl -sS -H "Authorization: Bearer ${ACCESS_TOKEN}" "${KEYCLOAK_URL}${path}"
}

kc_post() {
  local path="$1"
  local payload="$2"
  local status
  status=$(curl -sS -o /dev/null -w '%{http_code}' -X POST \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -H 'Content-Type: application/json' \
    -d "${payload}" \
    "${KEYCLOAK_URL}${path}")
  echo "${status}"
}

kc_put() {
  local path="$1"
  local payload="${2:-}"
  local status
  if [[ -n "${payload}" ]]; then
    status=$(curl -sS -o /dev/null -w '%{http_code}' -X PUT \
      -H "Authorization: Bearer ${ACCESS_TOKEN}" \
      -H 'Content-Type: application/json' \
      -d "${payload}" \
      "${KEYCLOAK_URL}${path}")
  else
    status=$(curl -sS -o /dev/null -w '%{http_code}' -X PUT \
      -H "Authorization: Bearer ${ACCESS_TOKEN}" \
      "${KEYCLOAK_URL}${path}")
  fi
  echo "${status}"
}

ensure_realm() {
  local realm_json
  realm_json=$(kc_get "/admin/realms/${REALM}" || true)
  if echo "${realm_json}" | jq -e '.realm == "'"${REALM}"'"' >/dev/null 2>&1; then
    return
  fi
  echo "ERROR: realm '${REALM}' not found" >&2
  exit 1
}

ensure_realm_role() {
  local role_name="$1"
  local description="$2"

  if kc_get "/admin/realms/${REALM}/roles/${role_name}" | jq -e --arg rn "${role_name}" '.name == $rn' >/dev/null 2>&1; then
    return
  fi

  local payload
  payload=$(jq -nc --arg name "${role_name}" --arg description "${description}" \
    '{name:$name,description:$description}')
  local status
  status=$(kc_post "/admin/realms/${REALM}/roles" "${payload}")
  if [[ "${status}" != "201" && "${status}" != "409" ]]; then
    echo "ERROR: could not create role '${role_name}' (HTTP ${status})" >&2
    exit 1
  fi
}

role_repr() {
  local role_name="$1"
  local data
  data=$(kc_get "/admin/realms/${REALM}/roles/${role_name}")
  if ! echo "${data}" | jq -e '.id and .name' >/dev/null 2>&1; then
    echo "ERROR: role '${role_name}' not found in realm '${REALM}'" >&2
    exit 1
  fi
  echo "${data}"
}

find_group_id() {
  local group_name="$1"
  kc_get "/admin/realms/${REALM}/groups?search=${group_name}&max=200" | jq -r --arg n "${group_name}" 'map(select(.name==$n)) | .[0].id // empty'
}

ensure_group() {
  local group_name="$1"
  local gid
  gid=$(find_group_id "${group_name}")
  if [[ -n "${gid}" ]]; then
    echo "${gid}"
    return
  fi

  local payload
  payload=$(jq -nc --arg name "${group_name}" '{name:$name}')
  local status
  status=$(kc_post "/admin/realms/${REALM}/groups" "${payload}")
  if [[ "${status}" != "201" && "${status}" != "409" ]]; then
    echo "ERROR: could not create group '${group_name}' (HTTP ${status})" >&2
    exit 1
  fi

  gid=$(find_group_id "${group_name}")
  if [[ -z "${gid}" ]]; then
    echo "ERROR: group '${group_name}' not found after creation" >&2
    exit 1
  fi
  echo "${gid}"
}

# The group membership has to reach the token, or the console cannot resolve a
# user without asking Keycloak as an administrator - which means holding an
# administrator credential in a service that only needs to know who is
# knocking. With this mapper the answer is in the signed token the user already
# arrived with.
#
# full.path false so the claim reads "connector-1-users" and not
# "/connector-1-users": the group names are flat here, and a leading slash is a
# difference nobody would notice until a comparison quietly stopped matching.
ensure_groups_claim() {
  local client_id="$1"
  local cid mapper_id payload status

  cid=$(kc_get "/admin/realms/${REALM}/clients?clientId=${client_id}" | jq -r '.[0].id // empty')
  if [[ -z "${cid}" ]]; then
    echo "WARN: client '${client_id}' not found; the console will fall back to the directory" >&2
    return 0
  fi

  mapper_id=$(kc_get "/admin/realms/${REALM}/clients/${cid}/protocol-mappers/models" |
    jq -r '.[] | select(.name == "groups") | .id // empty' | head -1)
  if [[ -n "${mapper_id}" ]]; then
    echo "Groups claim already on ${client_id}."
    return 0
  fi

  payload=$(jq -nc '{
    name: "groups",
    protocol: "openid-connect",
    protocolMapper: "oidc-group-membership-mapper",
    config: {
      "claim.name": "groups",
      "full.path": "false",
      "id.token.claim": "true",
      "access.token.claim": "true",
      "userinfo.token.claim": "true"
    }
  }')
  status=$(kc_post "/admin/realms/${REALM}/clients/${cid}/protocol-mappers/models" "${payload}")
  if [[ "${status}" != "201" && "${status}" != "409" ]]; then
    echo "ERROR: could not add the groups claim to '${client_id}' (HTTP ${status})" >&2
    exit 1
  fi
  echo "Groups claim added to ${client_id}."
}

bind_group_to_role() {
  local group_id="$1"
  local role_name="$2"
  local role_json
  role_json=$(role_repr "${role_name}")
  local status
  status=$(kc_post "/admin/realms/${REALM}/groups/${group_id}/role-mappings/realm" "[${role_json}]")
  if [[ "${status}" != "204" && "${status}" != "409" ]]; then
    echo "ERROR: could not map group '${group_id}' to role '${role_name}' (HTTP ${status})" >&2
    exit 1
  fi
}

find_user_id() {
  local username="$1"
  kc_get "/admin/realms/${REALM}/users?username=${username}&exact=true" | jq -r '.[0].id // empty'
}

ensure_user() {
  local username="$1"
  local email="$2"
  local first_name="$3"
  local last_name="$4"
  local password="$5"

  local uid
  uid=$(find_user_id "${username}")

  local created=false
  if [[ -z "${uid}" ]]; then
    if [[ -z "${password}" ]]; then
      echo "ERROR: creating '${username}' needs USER_DEFAULT_PASSWORD" >&2
      exit 1
    fi
    created=true
    local payload
    payload=$(jq -nc \
      --arg username "${username}" \
      --arg email "${email}" \
      --arg firstName "${first_name}" \
      --arg lastName "${last_name}" \
      --arg password "${password}" \
      '{username:$username,email:$email,firstName:$firstName,lastName:$lastName,enabled:true,emailVerified:true,credentials:[{type:"password",value:$password,temporary:false}]}')
    local status
    status=$(kc_post "/admin/realms/${REALM}/users" "${payload}")
    if [[ "${status}" != "201" && "${status}" != "409" ]]; then
      echo "ERROR: could not create user '${username}' (HTTP ${status})" >&2
      exit 1
    fi
    uid=$(find_user_id "${username}")
  else
    local update
    update=$(jq -nc \
      --arg username "${username}" \
      --arg email "${email}" \
      --arg firstName "${first_name}" \
      --arg lastName "${last_name}" \
      '{username:$username,email:$email,firstName:$firstName,lastName:$lastName,enabled:true,emailVerified:true}')
    local status
    status=$(kc_put "/admin/realms/${REALM}/users/${uid}" "${update}")
    if [[ "${status}" != "204" ]]; then
      echo "ERROR: could not update user '${username}' (HTTP ${status})" >&2
      exit 1
    fi
  fi

  if [[ -z "${uid}" ]]; then
    echo "ERROR: user '${username}' not found after creation" >&2
    exit 1
  fi

  # Only for a user this run created, or when the operator asked. A user that
  # was already there has a password somebody chose and something depends on.
  if [[ "${created}" == true || "${RESET_PASSWORDS}" == true ]]; then
    local reset_payload
    reset_payload=$(jq -nc --arg password "${password}" '{type:"password",temporary:false,value:$password}')
    local reset_status
    reset_status=$(kc_put "/admin/realms/${REALM}/users/${uid}/reset-password" "${reset_payload}")
    if [[ "${reset_status}" != "204" ]]; then
      echo "ERROR: could not set password for '${username}' (HTTP ${reset_status})" >&2
      exit 1
    fi
  fi

  echo "${uid}"
}

add_user_to_group() {
  local user_id="$1"
  local group_id="$2"
  local status
  status=$(kc_put "/admin/realms/${REALM}/users/${user_id}/groups/${group_id}")
  if [[ "${status}" != "204" ]]; then
    echo "ERROR: could not add user '${user_id}' to group '${group_id}' (HTTP ${status})" >&2
    exit 1
  fi
}

client_uuid() {
  local client_id="$1"
  kc_get "/admin/realms/${REALM}/clients?clientId=${client_id}" | jq -r '.[0].id // empty'
}

assign_roles_to_service_account() {
  local client_id="$1"
  local roles_csv="$2"

  local cid
  cid=$(client_uuid "${client_id}")
  if [[ -z "${cid}" ]]; then
    echo "WARN: client '${client_id}' not found, skipping service-account role mapping" >&2
    return
  fi

  local service_user_id
  service_user_id=$(kc_get "/admin/realms/${REALM}/clients/${cid}/service-account-user" | jq -r '.id // empty')
  if [[ -z "${service_user_id}" ]]; then
    echo "WARN: client '${client_id}' has no service account user, skipping" >&2
    return
  fi

  local roles_json="[]"
  local role
  IFS=',' read -ra parts <<< "${roles_csv}"
  for role in "${parts[@]}"; do
    role="$(echo "${role}" | xargs)"
    [[ -z "${role}" ]] && continue
    local rr
    rr=$(role_repr "${role}")
    roles_json=$(echo "${roles_json}" | jq --argjson roleObj "${rr}" '. + [$roleObj]')
  done

  local status
  status=$(kc_post "/admin/realms/${REALM}/users/${service_user_id}/role-mappings/realm" "${roles_json}")
  if [[ "${status}" != "204" && "${status}" != "409" ]]; then
    echo "ERROR: could not assign service-account roles to '${client_id}' (HTTP ${status})" >&2
    exit 1
  fi
}


sync_participant_registry() {
  local plan="$1"
  [[ "${ONBOARDING_SYNC_PARTICIPANTS}" == "true" ]] || return 0

  local payload connector_id status
  connector_id=$(echo "${plan}" | jq -r '.item.connectorId // empty')
  [[ -n "${connector_id}" ]] || return 0

  payload=$(echo "${plan}" | jq -c '{
    connectorId: .item.connectorId,
    roleProfile: (.item.roleProfile // "consumer"),
    clientId: (.item.keycloak.clientId // .item.clientId // ""),
    status: "active",
    identityAttributes: [.item.identityAttributes[]?.id]
  }')
  status=$(curl -sS -o /tmp/onboarding_participant_sync.json -w "%{http_code}" \
    -X POST "${ONBOARDING_API_URL%/}/api/v1/participants/sync" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json" \
    -d "${payload}" || true)
  if [[ "${status}" != "200" ]]; then
    echo "WARN: participant sync failed for ${connector_id} (HTTP ${status}); continuing" >&2
    return 0
  fi
  echo "Participant synced: ${connector_id}"
}


kc_admin_token
ensure_realm

echo "==> Creating realm roles"
ensure_realm_role "dataspace-user" "Read access to connector management APIs"
ensure_realm_role "dataspace-negotiator" "Permission to create negotiations"
ensure_realm_role "dataspace-admin" "Create/update access for assets, policies, and contracts"
ensure_realm_role "connector-user" "Pertenece al conector de este nodo"

echo "==> Creating groups and group role mappings"
GID_DS_USERS=$(ensure_group "dataspace-users")
GID_DS_NEG=$(ensure_group "dataspace-negotiators")
GID_DS_ADM=$(ensure_group "dataspace-admins")
GID_CONNECTOR=$(ensure_group "connector-users")

bind_group_to_role "${GID_DS_USERS}" "dataspace-user"
bind_group_to_role "${GID_DS_NEG}" "dataspace-negotiator"
bind_group_to_role "${GID_DS_ADM}" "dataspace-admin"
bind_group_to_role "${GID_CONNECTOR}" "connector-user"

echo "==> Creating users and assigning groups"
while IFS='|' read -r username email first_name last_name groups_csv; do
  [[ -z "${username}" ]] && continue

  uid=$(ensure_user "${username}" "${email}" "${first_name}" "${last_name}" "${USER_DEFAULT_PASSWORD}")

  IFS=',' read -ra glist <<< "${groups_csv}"
  for group_name in "${glist[@]}"; do
    group_name="$(echo "${group_name}" | xargs)"
    [[ -z "${group_name}" ]] && continue
    gid=$(ensure_group "${group_name}")
    add_user_to_group "${uid}" "${gid}"
  done

done <<< "$(printf "%b" "${USER_MATRIX}")"

echo "==> Assigning realm roles to connector service accounts"
IFS=',' read -ra saclients <<< "${SERVICE_ACCOUNT_CLIENTS}"
for c in "${saclients[@]}"; do
  c="$(echo "${c}" | xargs)"
  [[ -z "${c}" ]] && continue
  assign_roles_to_service_account "${c}" "dataspace-user,dataspace-negotiator,dataspace-admin"
done

echo "==> Putting the group membership into the console's token"
ensure_groups_claim "${KEYCLOAK_UI_CLIENT_ID:-dataspace-ui}"

echo "Done."
echo "Realm: ${REALM}"
if [[ "${RESET_PASSWORDS}" == true ]]; then
  echo "Every user in the matrix was given USER_DEFAULT_PASSWORD."
else
  echo "Users that already existed kept their passwords."
  echo "Pass --reset-passwords to overwrite them."
fi
