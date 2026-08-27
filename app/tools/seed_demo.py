#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Publica los productos de datos de ejemplo de seed/ en el conector del nodo.

Es lo que hace que un nodo recien instalado no ensene una pantalla vacia. Se
ejecuta en el arranque cuando ODS_SEED_DEMO esta activo, y a mano con
`python app/tools/seed_demo.py`.

Idempotente: un activo, una politica o un contrato que ya existen no se
vuelven a crear. Ejecutarlo dos veces no duplica nada.

No es fatal. Un nodo cuyo conector todavia no ha subido tiene que servir el
portal igual; lo unico que se pierde es el ejemplo, y se dice por que.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SEED_DIR = Path(os.getenv("ODS_SEED_DIR", "").strip() or (ROOT / "seed"))

CONNECTOR_URL = (
    os.getenv("ODS_CONNECTOR_URL", "").strip().rstrip("/") or "http://connector:8080"
)
MANAGEMENT = f"{CONNECTOR_URL}/management/v3"
PUBLIC_URL = os.getenv("ODS_PUBLIC_URL", "").strip().rstrip("/") or "http://localhost:8080"

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "").strip().rstrip("/") or "http://keycloak:8080/auth"
REALM = os.getenv("REALM_NAME", "").strip() or "dataspace"
CLIENT_ID = os.getenv("ODS_CONNECTOR_CLIENT_ID", "").strip() or "edc-connector"
ADMIN_USER = os.getenv("KEYCLOAK_ADMIN_USER", "").strip() or "admin"
ADMIN_PASSWORD = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "")


class SeedError(RuntimeError):
    pass


def request_json(url, method="GET", payload=None, token="", timeout=20, form=None):
    data = None
    headers = {"Accept": "application/json"}
    if form is not None:
        data = urllib.parse.urlencode(form).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, method=method, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read()
        return response.status, (json.loads(raw.decode("utf-8")) if raw else {})


def connector_token():
    """Un token de la cuenta de servicio del conector.

    El secreto no se guarda en ningun sitio de este arbol: se pide a Keycloak
    con las credenciales de administracion que la composicion ya le pasa a
    este servicio. Guardarlo en un fichero es exactamente el tipo de secreto
    que acaba versionado.
    """
    if os.getenv("ODS_EVALUATION_MODE", "").strip().lower() == "true":
        # Modo de evaluacion: no hay Keycloak y el conector no pide token.
        return ""
    if not ADMIN_PASSWORD:
        raise SeedError("sin KEYCLOAK_ADMIN_PASSWORD no se puede obtener el secreto del conector")

    _, admin = request_json(
        f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token",
        method="POST",
        form={
            "client_id": "admin-cli",
            "username": ADMIN_USER,
            "password": ADMIN_PASSWORD,
            "grant_type": "password",
        },
    )
    admin_token = admin.get("access_token", "")
    if not admin_token:
        raise SeedError("Keycloak no dio un token de administracion")

    _, clients = request_json(
        f"{KEYCLOAK_URL}/admin/realms/{REALM}/clients?clientId={urllib.parse.quote(CLIENT_ID)}",
        token=admin_token,
    )
    if not clients:
        raise SeedError(f"el cliente {CLIENT_ID} no existe en el realm {REALM}")

    _, secret = request_json(
        f"{KEYCLOAK_URL}/admin/realms/{REALM}/clients/{clients[0]['id']}/client-secret",
        token=admin_token,
    )
    client_secret = secret.get("value", "")
    if not client_secret:
        raise SeedError(f"el cliente {CLIENT_ID} no tiene secreto")

    _, token = request_json(
        f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/token",
        method="POST",
        form={
            "client_id": CLIENT_ID,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
        },
    )
    if not token.get("access_token"):
        raise SeedError("la cuenta de servicio del conector no dio un token")
    return token["access_token"]


def existing_ids(kind, token):
    """Lo que el conector ya tiene, para no crearlo dos veces."""
    try:
        _, items = request_json(f"{MANAGEMENT}/{kind}", token=token)
    except urllib.error.URLError:
        return set()
    if not isinstance(items, list):
        return set()
    return {str(item.get("@id") or item.get("id") or "") for item in items}


def load_manifest():
    manifest_path = SEED_DIR / "manifest.json"
    if not manifest_path.is_file():
        raise SeedError(f"no hay datos de ejemplo en {manifest_path}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def asset_payload(dataset):
    """El activo tal como el conector lo espera.

    La direccion del dato apunta a este mismo nodo. Que el fichero se sirva
    desde aqui es lo que mantiene la descarga mediada: el consumidor recibe la
    direccion al cerrar la transferencia, no antes.
    """
    file_name = Path(str(dataset.get("file", ""))).name
    return {
        "@id": dataset["dct:identifier"],
        "properties": {
            key: value for key, value in dataset.items() if key != "file"
        },
        "dataAddress": {
            "type": "HttpData",
            "baseUrl": f"{PUBLIC_URL}/api/onboarding/assets/seed/{file_name}",
            "proxyPath": "true",
            "proxyQueryParams": "true",
        },
    }


def publish(manifest, token):
    hechos = {"assets": 0, "policies": 0, "contracts": 0, "saltados": 0}

    ya_hay = existing_ids("assets", token)
    for dataset in manifest.get("datasets", []):
        asset_id = dataset.get("dct:identifier", "")
        if not asset_id or asset_id in ya_hay:
            hechos["saltados"] += 1
            continue
        request_json(f"{MANAGEMENT}/assets", method="POST", payload=asset_payload(dataset), token=token)
        hechos["assets"] += 1

    ya_hay = existing_ids("policydefinitions", token)
    for policy in manifest.get("policies", []):
        policy_id = policy.get("id", "")
        if not policy_id or policy_id in ya_hay:
            hechos["saltados"] += 1
            continue
        request_json(
            f"{MANAGEMENT}/policydefinitions",
            method="POST",
            payload={"@id": policy_id, "policy": {k: v for k, v in policy.items() if k != "id"}},
            token=token,
        )
        hechos["policies"] += 1

    ya_hay = existing_ids("contractdefinitions", token)
    for dataset in manifest.get("datasets", []):
        contract_id = dataset.get("ods:contractId", "")
        policy_id = dataset.get("ods:policyId", "")
        asset_id = dataset.get("dct:identifier", "")
        if not (contract_id and policy_id and asset_id) or contract_id in ya_hay:
            hechos["saltados"] += 1
            continue
        request_json(
            f"{MANAGEMENT}/contractdefinitions",
            method="POST",
            payload={
                "@id": contract_id,
                "accessPolicyId": policy_id,
                "contractPolicyId": policy_id,
                "assetsSelector": [
                    {"leftOperand": "id", "operator": "=", "rightOperand": asset_id}
                ],
            },
            token=token,
        )
        hechos["contracts"] += 1

    return hechos


def copy_seed_files():
    """Deja los ficheros de ejemplo donde el nodo los sirve."""
    files_dir = Path(os.getenv("ODS_FILES_DIR", "").strip() or "/var/lib/ods/files") / "seed"
    files_dir.mkdir(parents=True, exist_ok=True)
    copiados = 0
    for origen in sorted((SEED_DIR / "data").glob("*")):
        if not origen.is_file():
            continue
        destino = files_dir / origen.name
        if destino.exists():
            continue
        destino.write_bytes(origen.read_bytes())
        destino.with_suffix(destino.suffix + ".meta.json").write_text(
            json.dumps(
                {
                    "fileName": origen.name,
                    "contentType": "text/csv" if origen.suffix == ".csv" else "application/octet-stream",
                    "size": origen.stat().st_size,
                    "connectorId": os.getenv("ODS_CONNECTOR_ID", "connector"),
                    "source": "seed",
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        copiados += 1
    return copiados


def main():
    try:
        manifest = load_manifest()
        copiados = copy_seed_files()
        token = connector_token()
        hechos = publish(manifest, token)
    except (SeedError, urllib.error.URLError, OSError, ValueError) as exc:
        print(f"[seed] no se pudo publicar el ejemplo: {exc}", file=sys.stderr)
        return 1
    print(
        f"[seed] ficheros={copiados} activos={hechos['assets']} "
        f"politicas={hechos['policies']} contratos={hechos['contracts']} "
        f"ya_existian={hechos['saltados']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
