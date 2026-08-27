#!/usr/bin/env python3
import hashlib
import json
import os
import random
import re
import shlex
import smtplib
import string
import subprocess
import sys
import threading
import time
import base64
import mimetypes
import jwt
from email.message import EmailMessage
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib import error as urllib_error, parse, request
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.fernet import Fernet

ROOT = Path(__file__).resolve().parents[1]
# The catalogue profile and its validation live in federation/, the package
# published upstream as Catalejo. The service uses it rather than carrying a
# second copy: one implementation, two consumers -- this API and the
# federator that keeps the consolidated catalogue in step.
sys.path.insert(0, str(ROOT / "federation" / "src"))
from catalejo.profile import (  # noqa: E402
    CatalogueProfile,
    metadata_aliases,
    metadata_value,
    shorten_term,
)
# Where the self-service state lives: registrations, wallet, credentials and
# participants.
#
# This must be a volume, not a path inside the image. If it lives in the tree
# the container was built from, every upgrade replaces the tree and takes the
# registrations, the participants and the evidence ledger with it - a
# registration would live exactly until the next `docker compose pull` and
# then stop existing. The compose file mounts a named volume here.
DATA_DIR = Path(os.getenv("ONBOARDING_DATA_DIR", "").strip() or (ROOT / "onboarding"))
CONNECTORS_DIR = DATA_DIR / "connectors"
WALLET_DIR = DATA_DIR / "wallet"
PARTICIPANTS_DIR = DATA_DIR / "participants"
CONTRACTS_DIR = DATA_DIR / "contracts"
IDENTITY_ATTRIBUTES_DIR = DATA_DIR / "identity_attributes"
REQUESTS_FILE = DATA_DIR / "connector_requests.json"
REQUESTS_SECRET_FILE = DATA_DIR / "connector_requests.key"
EVIDENCE_LEDGER_FILE = DATA_DIR / "evidence_ledger.jsonl"
# Los otros nodos del espacio de datos. Es lo que convierte esto en un espacio
# de datos y no en un catalogo aislado: se anade la direccion de otro nodo y su
# oferta pasa a formar parte del catalogo consolidado, junto a la propia.
KNOWN_NODES_FILE = DATA_DIR / "known_nodes.json"
# Si este nodo ya paso por el asistente de primer arranque. Vive en el volumen
# de estado y no en el arbol: si viviera en el arbol, cada actualizacion de la
# imagen devolveria el nodo a la pantalla de configuracion.
SETUP_MARKER_FILE = DATA_DIR / "setup-complete.json"
# Lo que el asistente decide y el .env no traia: la marca, sobre todo. Se
# fusiona sobre las variables de entorno al renderizar la interfaz, de modo
# que quien instalo puede seguir mandando desde .env lo que quiera fijar.
SITE_OVERRIDES_FILE = DATA_DIR / "site.json"
# Los ficheros publicados. Es un volumen de disco: la especificacion
# descarta el almacen de objetos, asi que un activo es un fichero bajo
# esta carpeta y su direccion es una ruta de este mismo nodo.
FILES_DIR = Path(os.getenv("ODS_FILES_DIR", "").strip() or (DATA_DIR / "files"))
UI_DIR = ROOT / "app" / "ui"
# Los perfiles de metadatos y de politica. Una organizacion anade el suyo
# copiando una carpeta aqui dentro; no hay que tocar codigo.
PROFILES_DIR = Path(os.getenv("ODS_PROFILES_DIR", "").strip() or (ROOT / "profiles"))

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://identity-hub:8080")
KEYCLOAK_ADMIN_USER = os.getenv("KEYCLOAK_ADMIN_USER", "admin")
KEYCLOAK_ADMIN_PASSWORD = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin")
REALM_NAME = os.getenv("REALM_NAME", "dataspace")


HOST = os.getenv("ONBOARDING_HOST", "0.0.0.0")
PORT = int(os.getenv("ONBOARDING_PORT", "8092"))
# Quien firma el registro de operaciones: la identidad del propio nodo, que
# es lo unico que quien instala controla. El registro sigue firmado y sigue
# siendo verificable con la clave publica que el nodo expone.
AUDIT_ISSUER = os.getenv("ODS_PUBLIC_URL", "").strip() or os.getenv("ODS_ORG_ID", "").strip() or "urn:ods:node"
AUDIT_SIGNING_KID = os.getenv("ODS_AUDIT_SIGNING_KID", "").strip()
AUDIT_PRIVATE_KEY_FILE = os.getenv("ODS_AUDIT_PRIVATE_KEY_FILE", str(DATA_DIR / "audit-signing-key.pem")).strip()
# El correo del administrador del nodo. Sin valor por omision a proposito:
# lo pone quien instala, y de aqui sale tambien el remitente de los avisos.
REQUESTS_MASTER_EMAIL = os.getenv("ODS_ADMIN_EMAIL", "").strip().lower()
REQUESTS_FROM_EMAIL = os.getenv("ODS_SMTP_FROM", REQUESTS_MASTER_EMAIL).strip().lower()
REQUESTS_SMTP_HOST = os.getenv("ODS_SMTP_HOST", "").strip()
REQUESTS_SMTP_PORT = int(os.getenv("ODS_SMTP_PORT", "587"))
REQUESTS_SMTP_USER = os.getenv("ODS_SMTP_USER", REQUESTS_MASTER_EMAIL).strip()
REQUESTS_SMTP_PASSWORD = os.getenv("ODS_SMTP_PASSWORD", "").strip()
REQUESTS_SMTP_STARTTLS = os.getenv("ODS_SMTP_STARTTLS", "true").strip().lower() not in {"0", "false", "no"}

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PASSWORD_RE = re.compile(r"^(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{9,}$")

# El conector de este nodo. Uno solo, proveedor y consumidor a la vez.
#
# Estaba fijado a un identificador literal en una docena de sitios; ahora sale del
# entorno, con "connector" por omision, que es lo que permite que dos nodos
# instalados por separado no se llamen igual cuando se federan.
CONNECTOR_ID = os.getenv("ODS_CONNECTOR_ID", "").strip() or "connector"
CONNECTOR_CLIENT_ID = os.getenv("ODS_CONNECTOR_CLIENT_ID", "").strip() or "edc-connector"
# La superficie de gestion del conector, por la red interna de la composicion.
# No se publica por Caddy: abrirla es dar la consola de administracion del
# conector a internet.
DEFAULT_LANG = "en" if os.getenv("ODS_LANG", "").strip().lower().startswith("en") else "es"
# Modo de evaluacion: la imagen todo-en-uno, sin proveedor de identidad.
#
# Es un interruptor de seguridad y se trata como tal: se activa solo con la
# variable puesta a "true", se apaga solo si hay un dominio configurado
# -- tener las dos cosas significa que alguien lo ha heredado sin querer de
# una plantilla de evaluacion -- y se anuncia en el arranque.
EVALUATION_MODE = (
    os.getenv("ODS_EVALUATION_MODE", "").strip().lower() == "true"
    and not os.getenv("ODS_DOMAIN", "").strip()
)
CONNECTOR_MANAGEMENT_URL = (
    os.getenv("ODS_CONNECTOR_URL", "").strip().rstrip("/") or "http://connector:8080"
)

CONSUMER_GROUP_NAMES = ["dataspace-users", "dataspace-negotiators"]
CONSUMER_SERVICE_ACCOUNT_ROLES = ["dataspace-user", "dataspace-negotiator", "dataspace-admin"]
PROVIDER_GROUP_NAMES = ["dataspace-users", "dataspace-admins"]
REQUEST_REVIEWER_GROUPS = {"dataspace-admins", "connector-users"}
STATIC_CONNECTOR_IDS = {CONNECTOR_ID}
# Quien es el dueno del conector de este nodo, para el lookup que decide en
# que consola aterriza una persona al entrar. Sin esta entrada el lookup solo
# tiene CONNECTORS_DIR, que esta vacio en un nodo cuyo conector se declara en
# vez de registrarse, y cualquiera cae en /home.html.
#
# Una sola entrada: este producto entrega un conector. Antes habia tres, y una
# de ellas se quedaba sin dueno y sin nada publicado, de modo que quien
# aterrizaba en su consola veia una pantalla vacia y lo leia como que el
# acceso estaba roto.
STATIC_CONNECTOR_DIRECTORY = {
    CONNECTOR_ID: {
        "connectorId": CONNECTOR_ID,
        "email": REQUESTS_MASTER_EMAIL,
        "additionalEmails": [],
        "status": "active",
        "source": "predefined",
    },
}
# El perfil con el que el conector predefinido entra en el registro de
# participantes. Proveedor y consumidor a la vez: es un solo conector y tiene
# que poder publicar y consumir.
PREDEFINED_CONNECTOR_PROFILE = {
    CONNECTOR_ID: {"roleMode": "both", "keycloakClientId": CONNECTOR_CLIENT_ID},
}
ROLE_PROFILE_DESCRIPTIONS = {
    "consumer": {
        "connectorType": "consumer-only",
        "roles": ["consumer"],
        "capabilities": ["consume"],
        "keycloakGroups": ["{connectorId}-users", "dataspace-users", "dataspace-negotiators"],
        "labels": {"es": "Consumidor", "en": "Consumer"},
    },
    "provider": {
        "connectorType": "provider-only",
        "roles": ["provider"],
        "capabilities": ["publish"],
        "keycloakGroups": ["{connectorId}-users", "dataspace-users", "dataspace-admins"],
        "labels": {"es": "Proveedor", "en": "Provider"},
    },
    "both": {
        "connectorType": "provider-consumer",
        "roles": ["provider", "consumer"],
        "capabilities": ["publish", "consume"],
        "keycloakGroups": [
            "{connectorId}-users",
            "dataspace-users",
            "dataspace-negotiators",
            "dataspace-admins",
        ],
        "labels": {"es": "Proveedor y consumidor", "en": "Provider and consumer"},
    },
}
IDENTITY_ATTRIBUTE_PROFILES = {
    "dataspace.consumer": {
        "label": {"es": "Consumidor de dataspace", "en": "Dataspace consumer"},
        "roles": ["consumer"],
        "capabilities": ["consume"],
        "keycloakGroups": ["dataspace-users", "dataspace-negotiators"],
        "rbacRoles": ["dataspace-user", "dataspace-negotiator"],
        "assignable": True,
    },
    "dataspace.provider": {
        "label": {"es": "Proveedor de dataspace", "en": "Dataspace provider"},
        "roles": ["provider"],
        "capabilities": ["publish"],
        "keycloakGroups": ["dataspace-users", "dataspace-admins"],
        "rbacRoles": ["dataspace-user", "dataspace-admin"],
        "assignable": True,
    },
    "dataspace.auditor": {
        "label": {"es": "Auditor de gobernanza", "en": "Governance auditor"},
        "roles": ["auditor"],
        "capabilities": ["audit-read"],
        "keycloakGroups": ["dataspace-users", "dataspace-admins"],
        "rbacRoles": ["dataspace-user", "dataspace-admin"],
        "assignable": False,
    },
    "dataspace.negotiator": {
        "label": {"es": "Negociador de contratos", "en": "Contract negotiator"},
        "roles": ["consumer"],
        "capabilities": ["negotiate"],
        "keycloakGroups": ["dataspace-negotiators"],
        "rbacRoles": ["dataspace-negotiator"],
        "assignable": True,
    },
}
POLICY_PROFILE_DESCRIPTIONS = {
    "public-open-data": {
        "label": {"es": "Datos abiertos públicos", "en": "Public open data"},
        "accessRights": ["public"],
        "allowedRoles": ["consumer", "provider"],
        "defaultDecision": "grant",
        "obligations": ["attribution", "keep-source-link"],
    },
    "controlled-governed-reuse": {
        "label": {"es": "Reutilización gobernada", "en": "Controlled governed reuse"},
        "accessRights": ["controlled-governed-reuse", "contractual-dashboard"],
        "allowedRoles": ["consumer", "provider"],
        "defaultDecision": "grant",
        "obligations": ["signed-traceability", "access-logging", "contract-reference"],
    },
    "restricted-provider-review": {
        "label": {"es": "Acceso restringido con revisión", "en": "Restricted provider review"},
        "accessRights": ["restricted"],
        "allowedRoles": ["provider"],
        "defaultDecision": "review",
        "obligations": ["manual-approval", "signed-traceability", "access-logging"],
    },
}
METADATA_PROFILE_DESCRIPTIONS = {
    "ods-dcat-ap-1.0.0": {
        "label": {"es": "Perfil DCAT-AP", "en": "DCAT-AP profile"},
        "required": [
            "dct:identifier",
            "dct:title",
            "dct:description",
            "dct:publisher",
            "dct:license",
            "dct:accessRights",
            "dcat:theme",
            "dcat:keyword",
            "dcat:mediaType",
            "ods:deliveryMode",
        ],
        "controlledValues": {
            "dct:accessRights": ["public", "restricted", "contractual-dashboard", "controlled-governed-reuse"],
            "ods:deliveryMode": ["dashboard", "download", "api", "streaming"],
        },
        "vocabularies": ["dcat-ap", "odrl"],
        "shapes": ["generated/vocabularies/dcat-ap/1.0.0/shapes.ttl"],
    }
}

captcha_store = {}
captcha_lock = threading.Lock()
_audit_signing_key_cache = None
_requests_secret_cache = None
_keycloak_jwks_client = None


def json_response(handler, code, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def utc_now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def unix_now():
    return int(time.time())


def ensure_requests_storage():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not REQUESTS_FILE.exists():
        REQUESTS_FILE.write_text("[]\n", encoding="utf-8")


def load_requests():
    ensure_requests_storage()
    try:
        payload = json.loads(REQUESTS_FILE.read_text(encoding="utf-8"))
    except Exception:
        payload = []
    return payload if isinstance(payload, list) else []


def save_requests(items):
    ensure_requests_storage()
    REQUESTS_FILE.write_text(json.dumps(items, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_requests_secret():
    global _requests_secret_cache
    if _requests_secret_cache:
        return _requests_secret_cache
    REQUESTS_SECRET_FILE.parent.mkdir(parents=True, exist_ok=True)
    if REQUESTS_SECRET_FILE.exists():
        secret = REQUESTS_SECRET_FILE.read_bytes().strip()
    else:
        secret = Fernet.generate_key()
        REQUESTS_SECRET_FILE.write_bytes(secret)
    _requests_secret_cache = secret
    return secret


def requests_cipher():
    return Fernet(load_requests_secret())


def encrypt_pending_password(password: str) -> str:
    return requests_cipher().encrypt(password.encode("utf-8")).decode("utf-8")


def decrypt_pending_password(payload: str) -> str:
    return requests_cipher().decrypt(payload.encode("utf-8")).decode("utf-8")


def canonicalize_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def last_evidence_hash():
    if not EVIDENCE_LEDGER_FILE.exists():
        return ""
    try:
        lines = [line for line in EVIDENCE_LEDGER_FILE.read_text(encoding="utf-8").splitlines() if line.strip()]
    except Exception:
        return ""
    if not lines:
        return ""
    try:
        return str(json.loads(lines[-1]).get("evidenceHash", "") or "")
    except Exception:
        return ""


def seal_evidence(payload):
    EVIDENCE_LEDGER_FILE.parent.mkdir(parents=True, exist_ok=True)
    previous_hash = last_evidence_hash()
    sealed_at = utc_now()
    payload_hash = hashlib.sha256(canonicalize_json(payload).encode("utf-8")).hexdigest()
    evidence_hash = hashlib.sha256(
        canonicalize_json(
            {
                "payload": payload,
                "previousHash": previous_hash,
                "sealedAt": sealed_at,
            }
        ).encode("utf-8")
    ).hexdigest()
    seal = {
        "sealedAt": sealed_at,
        "evidenceHash": evidence_hash,
        "previousHash": previous_hash,
        "sealProfile": "ods-hash-chain-1.0",
        "ensAlignment": "technical-integrity-chain-pending-qualified-time-stamp",
    }
    evidence = payload.get("evidence", {}) if isinstance(payload.get("evidence"), dict) else {}
    catalog_metadata = evidence.get("catalogMetadata", {}) if isinstance(evidence.get("catalogMetadata"), dict) else {}
    ledger_record = {
        **seal,
        "payloadHash": payload_hash,
        "eventId": payload.get("eventId", ""),
        # Both names, the way the line below already does it for the type.
        # The API accepts auditTraceId and echoes it back in the 202, and this
        # read only traceId, so every event posted the documented way sealed a
        # record with no trace on it at all. Three records in the ledger on
        # 23 August 2026 and every one of them unattributable: the chain was
        # intact, the hashes verified, and nothing could be found by the id its
        # sender was given.
        "traceId": payload.get("traceId", "") or payload.get("auditTraceId", ""),
        "type": payload.get("type", "") or payload.get("eventType", ""),
        "subject": payload.get("subject", {}) if isinstance(payload.get("subject"), dict) else payload.get("subject", ""),
        "actor": payload.get("actor", {}) if isinstance(payload.get("actor"), dict) else payload.get("actor", ""),
        "resource": payload.get("resource", {}) if isinstance(payload.get("resource"), dict) else payload.get("resource", ""),
        "catalogMetadataHash": catalog_metadata.get("hash", ""),
        "catalogMetadataProfile": catalog_metadata.get("profile", ""),
        "signatureKid": payload.get("signatureKid", ""),
    }
    with EVIDENCE_LEDGER_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(ledger_record, ensure_ascii=False) + "\n")
    return seal


def read_evidence_ledger():
    if not EVIDENCE_LEDGER_FILE.exists():
        return []
    items = []
    try:
        lines = EVIDENCE_LEDGER_FILE.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []
    for index, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except Exception:
            record = {"malformed": True, "rawLine": line}
        if isinstance(record, dict):
            record.setdefault("sequence", index)
            items.append(record)
    return items


def evidence_record_matches(record, trace_id="", event_type="", participant_id="", event_id=""):
    if trace_id and str(record.get("traceId", "") or "") != trace_id:
        return False
    if event_type and str(record.get("type", "") or "") != event_type:
        return False
    if event_id and str(record.get("eventId", "") or "") != event_id:
        return False
    if participant_id:
        subject = record.get("subject", {}) if isinstance(record.get("subject"), dict) else {}
        actor = record.get("actor", {}) if isinstance(record.get("actor"), dict) else {}
        resource = record.get("resource", {}) if isinstance(record.get("resource"), dict) else {}
        candidates = {
            str(subject.get("id", "") or ""),
            str(subject.get("participantId", "") or ""),
            str(actor.get("participantId", "") or ""),
            str(resource.get("participantId", "") or ""),
        }
        if participant_id not in candidates:
            return False
    return True


def list_evidence_records(trace_id="", event_type="", participant_id="", event_id="", limit=100):
    try:
        max_items = max(1, min(int(limit or 100), 1000))
    except Exception:
        max_items = 100
    items = [
        record
        for record in read_evidence_ledger()
        if evidence_record_matches(record, trace_id=trace_id, event_type=event_type, participant_id=participant_id, event_id=event_id)
    ]
    return items[-max_items:]


def evidence_trace_summary():
    traces = {}
    for record in read_evidence_ledger():
        trace_id = str(record.get("traceId", "") or "").strip()
        if not trace_id:
            trace_id = f"event:{record.get('eventId', record.get('sequence', 'unknown'))}"
        trace = traces.setdefault(
            trace_id,
            {
                "traceId": trace_id,
                "eventCount": 0,
                "firstSeen": "",
                "lastSeen": "",
                "eventTypes": [],
                "latestEvidenceHash": "",
                "catalogMetadataHashes": [],
            },
        )
        trace["eventCount"] += 1
        sealed_at = str(record.get("sealedAt", "") or "")
        if sealed_at and (not trace["firstSeen"] or sealed_at < trace["firstSeen"]):
            trace["firstSeen"] = sealed_at
        if sealed_at and sealed_at > trace["lastSeen"]:
            trace["lastSeen"] = sealed_at
        event_type = str(record.get("type", "") or "").strip()
        if event_type and event_type not in trace["eventTypes"]:
            trace["eventTypes"].append(event_type)
        if record.get("evidenceHash"):
            trace["latestEvidenceHash"] = record["evidenceHash"]
        catalog_hash = str(record.get("catalogMetadataHash", "") or "").strip()
        if catalog_hash and catalog_hash not in trace["catalogMetadataHashes"]:
            trace["catalogMetadataHashes"].append(catalog_hash)
    return sorted(traces.values(), key=lambda item: item.get("lastSeen", ""), reverse=True)


def verify_evidence_ledger():
    records = read_evidence_ledger()
    issues = []
    previous_hash = ""
    seen_hashes = set()
    for record in records:
        sequence = record.get("sequence", 0)
        evidence_hash = str(record.get("evidenceHash", "") or "")
        record_previous_hash = str(record.get("previousHash", "") or "")
        if record.get("malformed"):
            issues.append({"sequence": sequence, "error": "malformed_json"})
            continue
        if not evidence_hash:
            issues.append({"sequence": sequence, "error": "missing_evidence_hash"})
        elif evidence_hash in seen_hashes:
            issues.append({"sequence": sequence, "error": "duplicate_evidence_hash", "evidenceHash": evidence_hash})
        if record_previous_hash != previous_hash:
            issues.append(
                {
                    "sequence": sequence,
                    "error": "broken_hash_chain",
                    "expectedPreviousHash": previous_hash,
                    "actualPreviousHash": record_previous_hash,
                }
            )
        if evidence_hash:
            seen_hashes.add(evidence_hash)
            previous_hash = evidence_hash
    return {
        "ok": not issues,
        "recordCount": len(records),
        "latestEvidenceHash": previous_hash,
        "issues": issues,
    }


def base64url_encode_bytes(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def connector_key_dir() -> Path:
    return WALLET_DIR / "keys"


def connector_key_path(connector_id: str) -> Path:
    return connector_key_dir() / f"{connector_id}-audit-signing-key.pem"


def connector_signature_kid(connector_id: str) -> str:
    return f"{AUDIT_ISSUER}#{connector_id}-key-1"


def _load_private_key_from_path(path: Path):
    return serialization.load_pem_private_key(path.read_bytes(), password=None)


def _public_jwk_from_private_key(private_key) -> dict:
    public_numbers = private_key.public_key().public_numbers()
    x = public_numbers.x.to_bytes(32, "big")
    y = public_numbers.y.to_bytes(32, "big")
    return {
        "kty": "EC",
        "crv": "P-256",
        "x": base64url_encode_bytes(x),
        "y": base64url_encode_bytes(y),
    }


def ensure_wallet_signing_key(connector_id: str) -> Path:
    key_path = connector_key_path(connector_id)
    key_path.parent.mkdir(parents=True, exist_ok=True)
    if not key_path.exists():
        private_key = ec.generate_private_key(ec.SECP256R1())
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        key_path.write_bytes(pem)
    return key_path






def infer_signing_connector_id(payload):
    actor = payload.get("actor", {}) or {}
    if isinstance(actor, dict):
        connector_id = str(actor.get("connectorId", "") or "").strip()
        if connector_id:
            return connector_id

    for field_name in ("consumerConnectorId", "providerConnectorId"):
        connector_id = str(payload.get(field_name, "") or "").strip()
        if connector_id:
            return connector_id

    subject = payload.get("subject", {}) or {}
    if isinstance(subject, dict):
        if str(subject.get("type", "") or "").strip() == "connector":
            connector_id = str(subject.get("id", "") or "").strip()
            if connector_id:
                return connector_id

    resource = payload.get("resource", {}) or {}
    if isinstance(resource, dict):
        connector_id = str(resource.get("consumerConnectorId", "") or "").strip()
        if connector_id:
            return connector_id

    evidence = payload.get("evidence", {}) or {}
    if isinstance(evidence, dict):
        connector_id = str(evidence.get("connectorId", "") or "").strip()
        if connector_id:
            return connector_id

    return ""


def load_audit_signing_key():
    global _audit_signing_key_cache
    if _audit_signing_key_cache is not None:
        return _audit_signing_key_cache
    key_path = ensure_governance_signing_key()
    _audit_signing_key_cache = key_path.read_text(encoding="utf-8")
    return _audit_signing_key_cache


SIGNATURE_ENVELOPE_FIELDS = {"signature", "signatureIssuer", "signatureKid", "signatureAlgorithm"}
LOCAL_AUDIT_ONLY_FIELDS = {"evidenceSeal"}


def normalize_event_for_signing(payload):
    return {
        key: value
        for key, value in payload.items()
        if key not in SIGNATURE_ENVELOPE_FIELDS and key not in LOCAL_AUDIT_ONLY_FIELDS
    }










def sign_audit_event(payload):
    connector_id = infer_signing_connector_id(payload)
    if connector_id:
        key_path = ensure_wallet_signing_key(connector_id)
        private_key = key_path.read_text(encoding="utf-8")
        kid = connector_signature_kid(connector_id)
    else:
        private_key = load_audit_signing_key()
        kid = AUDIT_SIGNING_KID or f"{AUDIT_ISSUER}#node-key-1"
    signing_payload = dict(payload)
    if connector_id:
        signing_payload.setdefault("signatureSignerConnectorId", connector_id)
    normalized_event = normalize_event_for_signing(signing_payload)
    claims = {
        "iss": AUDIT_ISSUER,
        "sub": str(normalized_event.get("subject", "")).strip(),
        "iat": int(time.time()),
        "jti": str(normalized_event.get("eventId", "")).strip(),
        "event": normalized_event,
        "eventHash": hashlib.sha256(canonicalize_json(normalized_event).encode("utf-8")).hexdigest(),
    }
    token = jwt.encode(
        claims,
        private_key,
        algorithm="ES256",
        headers={"kid": kid, "typ": "JWT"},
    )
    signed_event = dict(normalized_event)
    signed_event["signature"] = token
    signed_event["signatureIssuer"] = AUDIT_ISSUER
    signed_event["signatureKid"] = kid
    signed_event["signatureAlgorithm"] = "ES256"
    signed_event["evidenceSeal"] = seal_evidence(signed_event)
    return signed_event


def audit_event_or_local(payload):
    """Firma el evento; si la firma falla, lo devuelve sin firmar y lo dice.

    No se reenvia a ningun servicio externo: el registro de operaciones vive
    en este nodo y se consulta desde su consola.
    """
    try:
        return sign_audit_event(payload)
    except Exception:
        event = dict(payload)
        event["signatureStatus"] = "not-signed"
        return event






def kc_request(method, path, token=None, payload=None, query=None):
    url = f"{KEYCLOAK_URL}{path}"
    if query:
        url = f"{url}?{parse.urlencode(query)}"
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = request.Request(url, method=method, headers=headers, data=data)
    with request.urlopen(req, timeout=20) as resp:
        raw = resp.read()
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))


def get_admin_token():
    token_url = f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token"
    form = parse.urlencode(
        {
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": KEYCLOAK_ADMIN_USER,
            "password": KEYCLOAK_ADMIN_PASSWORD,
        }
    ).encode("utf-8")
    req = request.Request(token_url, method="POST", data=form)
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    token = data.get("access_token")
    if not token:
        raise RuntimeError("No se pudo obtener token admin de Keycloak")
    return token


def ensure_service_account_roles(client_internal_id, token, role_names):
    service_account = kc_request(
        "GET",
        f"/admin/realms/{REALM_NAME}/clients/{client_internal_id}/service-account-user",
        token=token,
    )
    service_account_user_id = str(service_account.get("id", "") or "").strip()
    if not service_account_user_id:
        raise RuntimeError("No se pudo obtener la cuenta de servicio del cliente Keycloak")

    assigned_roles = kc_request(
        "GET",
        f"/admin/realms/{REALM_NAME}/users/{service_account_user_id}/role-mappings/realm",
        token=token,
    ) or []
    assigned_names = {str(role.get("name", "")).strip() for role in assigned_roles if role.get("name")}

    missing_role_reprs = []
    for role_name in role_names:
        if role_name in assigned_names:
            continue
        role_repr = kc_request(
            "GET",
            f"/admin/realms/{REALM_NAME}/roles/{role_name}",
            token=token,
        )
        if str(role_repr.get("name", "")).strip() != role_name:
            raise RuntimeError(f"No se encontro el rol de Keycloak requerido: {role_name}")
        missing_role_reprs.append(role_repr)

    if not missing_role_reprs:
        return

    kc_request(
        "POST",
        f"/admin/realms/{REALM_NAME}/users/{service_account_user_id}/role-mappings/realm",
        token=token,
        payload=missing_role_reprs,
    )


def ensure_keycloak_client(connector_id, role_mode="consumer"):
    client_id = f"participant-{connector_id}"
    token = get_admin_token()
    clients = kc_request(
        "GET",
        f"/admin/realms/{REALM_NAME}/clients",
        token=token,
        query={"clientId": client_id},
    )
    if clients:
        internal_id = clients[0]["id"]
    else:
        kc_request(
            "POST",
            f"/admin/realms/{REALM_NAME}/clients",
            token=token,
            payload={
                "clientId": client_id,
                "name": client_id,
                "enabled": True,
                "protocol": "openid-connect",
                "publicClient": False,
                "serviceAccountsEnabled": True,
                "standardFlowEnabled": True,
                "directAccessGrantsEnabled": True,
            },
        )
        clients = kc_request(
            "GET",
            f"/admin/realms/{REALM_NAME}/clients",
            token=token,
            query={"clientId": client_id},
        )
        if not clients:
            raise RuntimeError("No se pudo crear cliente en Keycloak")
        internal_id = clients[0]["id"]

    secret_data = kc_request(
        "GET",
        f"/admin/realms/{REALM_NAME}/clients/{internal_id}/client-secret",
        token=token,
    )
    secret = secret_data.get("value", "")
    if not secret:
        raise RuntimeError("No se pudo obtener secreto del cliente Keycloak")
    ensure_service_account_roles(internal_id, token, CONSUMER_SERVICE_ACCOUNT_ROLES)
    return client_id, secret


def ensure_keycloak_user(email, password, first_name="", last_name=""):
    """Devuelve (user_id, created) y escribe la contraseña **sólo si la creó**.

    Aprobar una solicitud no puede cambiarle la contraseña a una cuenta que ya
    existía: una solicitud sólo pasa un captcha, no prueba que quien la envía
    sea el dueño de la dirección. Con un reset-password incondicional, cualquiera
    que conozca la dirección de un administrador y mande una solicitud a su
    nombre le sustituye la contraseña.

    Crear un usuario sí necesita contraseña, así que ese caso no cambia. Quien
    de verdad quiera fijar la de una cuenta existente lo hace explícitamente
    -- ver ensure_admin_user, que es el único sitio con motivo para ello.
    """
    token = get_admin_token()
    users = kc_request(
        "GET",
        f"/admin/realms/{REALM_NAME}/users",
        token=token,
        query={"username": email, "exact": "true"},
    )

    if not users:
        # Some realms keep usernames short (e.g., "francisco") while login uses email.
        users = kc_request(
            "GET",
            f"/admin/realms/{REALM_NAME}/users",
            token=token,
            query={"email": email, "exact": "true"},
        )

    if users:
        user_id = users[0]["id"]
        kc_request(
            "PUT",
            f"/admin/realms/{REALM_NAME}/users/{user_id}",
            token=token,
            payload={
                "username": email,
                "email": email,
                "firstName": str(first_name or "").strip(),
                "lastName": str(last_name or "").strip(),
                "enabled": True,
                "emailVerified": True,
            },
        )
    else:
        kc_request(
            "POST",
            f"/admin/realms/{REALM_NAME}/users",
            token=token,
            payload={
                "username": email,
                "email": email,
                "firstName": str(first_name or "").strip(),
                "lastName": str(last_name or "").strip(),
                "enabled": True,
                "emailVerified": True,
            },
        )
        users = kc_request(
            "GET",
            f"/admin/realms/{REALM_NAME}/users",
            token=token,
            query={"username": email, "exact": "true"},
        )
        if not users:
            raise RuntimeError("No se pudo crear usuario en Keycloak")
        user_id = users[0]["id"]
        kc_request(
            "PUT",
            f"/admin/realms/{REALM_NAME}/users/{user_id}/reset-password",
            token=token,
            payload={"type": "password", "value": password, "temporary": False},
        )
        return user_id, True

    return user_id, False


def find_group_id(group_name, token):
    groups = kc_request(
        "GET",
        f"/admin/realms/{REALM_NAME}/groups",
        token=token,
        query={"search": group_name},
    )
    for group in groups or []:
        if str(group.get("name", "")).strip() == group_name:
            return group.get("id")
    return ""


def ensure_group_exists(group_name, token):
    group_id = find_group_id(group_name, token)
    if group_id:
        return group_id
    kc_request(
        "POST",
        f"/admin/realms/{REALM_NAME}/groups",
        token=token,
        payload={"name": group_name},
    )
    group_id = find_group_id(group_name, token)
    if not group_id:
        raise RuntimeError(f"No se encontro el grupo de Keycloak requerido: {group_name}")
    return group_id


def ensure_user_in_group(user_id, group_name, token):
    groups = kc_request(
        "GET",
        f"/admin/realms/{REALM_NAME}/users/{user_id}/groups",
        token=token,
    )
    for group in groups or []:
        if str(group.get("name", "")).strip() == group_name:
            return

    group_id = ensure_group_exists(group_name, token)
    kc_request(
        "PUT",
        f"/admin/realms/{REALM_NAME}/users/{user_id}/groups/{group_id}",
        token=token,
    )


def ensure_consumer_access(user_id):
    token = get_admin_token()
    for group_name in CONSUMER_GROUP_NAMES:
        ensure_user_in_group(user_id, group_name, token)


def ensure_request_access(user_id, connector_id, role_mode):
    token = get_admin_token()
    for group_name in keycloak_groups_for_mode(connector_id, role_mode):
        ensure_user_in_group(user_id, group_name, token)




def write_wallet(connector_id, email, client_id, client_secret, role_mode="consumer"):
    WALLET_DIR.mkdir(parents=True, exist_ok=True)
    ensure_wallet_signing_key(connector_id)
    allowed_roles = requested_roles_for_mode(role_mode)
    wallet_doc = {
        "connector_id": connector_id,
        "owner": email,
        "client_id": client_id,
        "client_secret": client_secret,
        "permissions": {"publish": "provider" in allowed_roles, "consume": "consumer" in allowed_roles},
        "roles": allowed_roles,
        "signing_kid": connector_signature_kid(connector_id),
        "created_at": int(time.time()),
    }
    (WALLET_DIR / f"{connector_id}.json").write_text(
        json.dumps(wallet_doc, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def write_connector_registration(connector_id, email, client_id, role_mode="consumer"):
    CONNECTORS_DIR.mkdir(parents=True, exist_ok=True)
    connector_type = connector_type_for_mode(role_mode)
    notes_by_type = {
        "consumer-only": "Este conector solo puede consumir data assets del catálogo.",
        "provider-only": "Este conector solo puede publicar y administrar data assets propios.",
        "provider-consumer": "Este conector puede publicar y consumir data assets.",
    }
    doc = {
        "connector_id": connector_id,
        "email": email,
        "keycloak_client_id": client_id,
        "type": connector_type,
        "roles": requested_roles_for_mode(role_mode),
        "status": "deployed",
        "created_at": int(time.time()),
        "notes": notes_by_type.get(connector_type, ""),
    }
    (CONNECTORS_DIR / f"{connector_id}.json").write_text(
        json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def make_connector_id(email):
    digest = hashlib.sha1(email.encode("utf-8")).hexdigest()[:10]
    return f"connector-{digest}"


def normalize_role_mode(value):
    raw = str(value or "").strip().lower()
    if raw in {"provider", "consumer", "both"}:
        return raw
    return "consumer"


def requested_roles_for_mode(value):
    mode = normalize_role_mode(value)
    if mode == "provider":
        return ["provider"]
    if mode == "both":
        return ["provider", "consumer"]
    return ["consumer"]


def connector_type_for_mode(value):
    mode = normalize_role_mode(value)
    if mode == "provider":
        return "provider-only"
    if mode == "both":
        return "provider-consumer"
    return "consumer-only"


def keycloak_groups_for_mode(connector_id, value):
    mode = normalize_role_mode(value)
    groups = [f"{connector_id}-users", "dataspace-users"]
    if mode in {"consumer", "both"}:
        groups.append("dataspace-negotiators")
    if mode in {"provider", "both"}:
        groups.append("dataspace-admins")
    return groups


def identity_attribute_ids_for_mode(value):
    mode = normalize_role_mode(value)
    attribute_ids = []
    if mode in {"consumer", "both"}:
        attribute_ids.extend(["dataspace.consumer", "dataspace.negotiator"])
    if mode in {"provider", "both"}:
        attribute_ids.append("dataspace.provider")
    return sorted(set(attribute_ids))


def mode_label(mode, lang="es"):
    normalized = normalize_role_mode(mode)
    if str(lang or "es").lower().startswith("en"):
        return {
            "consumer": "Consumer",
            "provider": "Provider",
            "both": "Provider and consumer",
        }.get(normalized, "Consumer")
    return {
        "consumer": "Consumidor",
        "provider": "Proveedor",
        "both": "Proveedor y consumidor",
    }.get(normalized, "Consumidor")


def role_profile_doc(mode, connector_id="{connectorId}"):
    normalized = normalize_role_mode(mode)
    profile = ROLE_PROFILE_DESCRIPTIONS[normalized]
    return {
        "id": normalized,
        "label": profile["labels"],
        "connectorType": connector_type_for_mode(normalized),
        "roles": requested_roles_for_mode(normalized),
        "capabilities": profile["capabilities"],
        "keycloakGroups": [
            group.replace("{connectorId}", str(connector_id or "{connectorId}").strip() or "{connectorId}")
            for group in profile["keycloakGroups"]
        ],
        "governance": {
            "participantStatusRequired": "active",
            "credentialType": "MembershipCredential",
            "auditEvents": [
                "participant.upserted",
                "credential.issued",
                "credential.revoked",
                "participant.status.changed",
            ],
        },
    }


def list_role_profiles(connector_id="{connectorId}"):
    return [role_profile_doc(mode, connector_id) for mode in ("consumer", "provider", "both")]


def identity_attribute_path(attribute_id):
    return IDENTITY_ATTRIBUTES_DIR / canonical_filename(attribute_id)


def identity_attribute_doc(attribute_id):
    profile = IDENTITY_ATTRIBUTE_PROFILES.get(str(attribute_id or "").strip())
    if not profile:
        return None
    return {
        "id": str(attribute_id),
        "label": profile["label"],
        "roles": profile["roles"],
        "capabilities": profile["capabilities"],
        "keycloakGroups": profile["keycloakGroups"],
        "rbacRoles": profile["rbacRoles"],
        "assignable": bool(profile.get("assignable", True)),
        "source": "atributos de identidad del participante",
    }


def list_identity_attributes(assignable_only=False):
    items = []
    for attribute_id in sorted(IDENTITY_ATTRIBUTE_PROFILES):
        doc = identity_attribute_doc(attribute_id)
        if not doc:
            continue
        if assignable_only and not doc.get("assignable"):
            continue
        items.append(doc)
    if IDENTITY_ATTRIBUTES_DIR.exists():
        for path in sorted(IDENTITY_ATTRIBUTES_DIR.glob("*.json")):
            try:
                doc = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(doc, dict) or not doc.get("id"):
                continue
            if doc["id"] in IDENTITY_ATTRIBUTE_PROFILES:
                continue
            if assignable_only and not doc.get("assignable", True):
                continue
            items.append(doc)
    return items


def upsert_identity_attribute(payload):
    payload = payload if isinstance(payload, dict) else {}
    attribute_id = str(payload.get("id") or payload.get("attributeId") or "").strip()
    if not attribute_id:
        raise ValueError("missing_identity_attribute_id")
    base = identity_attribute_doc(attribute_id) or {}
    doc = {
        **base,
        "id": attribute_id,
        "label": payload.get("label", base.get("label", {"es": attribute_id, "en": attribute_id})),
        "roles": normalize_list(payload.get("roles", base.get("roles", []))),
        "capabilities": normalize_list(payload.get("capabilities", base.get("capabilities", []))),
        "keycloakGroups": normalize_list(payload.get("keycloakGroups", base.get("keycloakGroups", []))),
        "rbacRoles": normalize_list(payload.get("rbacRoles", base.get("rbacRoles", []))),
        "assignable": bool(payload.get("assignable", base.get("assignable", True))),
        "source": "atributos de identidad del participante",
        "updatedAt": utc_now(),
    }
    IDENTITY_ATTRIBUTES_DIR.mkdir(parents=True, exist_ok=True)
    identity_attribute_path(attribute_id).write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return doc


def participant_identity_attributes(participant):
    participant = participant if isinstance(participant, dict) else {}
    attrs = participant.get("identityAttributes", [])
    if isinstance(attrs, list):
        return sorted({str(item).strip() for item in attrs if str(item).strip()})
    return []


def assign_identity_attributes_to_participant(participant_id, attribute_ids, action="assign"):
    participant = load_participant(participant_id)
    if not participant:
        raise ValueError("participant_not_found")
    requested = sorted({str(item).strip() for item in normalize_list(attribute_ids) if str(item).strip()})
    unknown = [item for item in requested if not identity_attribute_doc(item) and not identity_attribute_path(item).exists()]
    if unknown:
        raise ValueError(f"unknown_identity_attributes:{','.join(unknown)}")
    current = set(participant_identity_attributes(participant))
    if action == "unassign":
        current.difference_update(requested)
        event_type = "participant.identity_attributes.unassigned"
    else:
        current.update(requested)
        event_type = "participant.identity_attributes.assigned"
    participant["identityAttributes"] = sorted(current)
    participant.setdefault("attributes", {})
    participant["attributes"]["identityAttributes"] = sorted(current)
    return save_participant(participant, event_type, {"identityAttributes": requested})




def normalize_list(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def policy_profile_doc(profile_id):
    profile = POLICY_PROFILE_DESCRIPTIONS[profile_id]
    return {
        "id": profile_id,
        "label": profile["label"],
        "accessRights": profile["accessRights"],
        "allowedRoles": profile["allowedRoles"],
        "defaultDecision": profile["defaultDecision"],
        "obligations": profile["obligations"],
        "source": "perfil de politica ODRL",
    }


def list_policy_profiles():
    return [policy_profile_doc(profile_id) for profile_id in POLICY_PROFILE_DESCRIPTIONS]


def access_rights_from_metadata(metadata):
    metadata = metadata if isinstance(metadata, dict) else {}
    return str(metadata.get("dct:accessRights") or metadata.get("accessRights") or "").strip() or "restricted"


def policy_profile_for_context(metadata, policy):
    access_rights = access_rights_from_metadata(metadata)
    for profile_id, profile in POLICY_PROFILE_DESCRIPTIONS.items():
        if access_rights in profile["accessRights"]:
            return profile_id
    policy_inner = policy.get("policy", policy) if isinstance(policy, dict) else {}
    if str(policy_inner.get("profile", "") or "").strip() in POLICY_PROFILE_DESCRIPTIONS:
        return str(policy_inner.get("profile")).strip()
    return "restricted-provider-review"


def metadata_profile_doc(profile_id="ods-dcat-ap-1.0.0"):
    profile = METADATA_PROFILE_DESCRIPTIONS[profile_id]
    return {
        "id": profile_id,
        "label": profile["label"],
        "required": profile["required"],
        "controlledValues": profile["controlledValues"],
        "vocabularies": profile["vocabularies"],
        "shapes": profile["shapes"],
        "source": "perfil de metadatos DCAT-AP",
    }


def list_metadata_profiles():
    return [metadata_profile_doc(profile_id) for profile_id in METADATA_PROFILE_DESCRIPTIONS]


def policy_actions(policy, key):
    policy_inner = policy.get("policy", policy) if isinstance(policy, dict) else {}
    values = []
    raw = policy_inner.get(key, [])
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                values.extend(normalize_list(item.get("action") or item.get("actions") or item.get("name")))
            else:
                values.extend(normalize_list(item))
    else:
        values.extend(normalize_list(raw))
    return [value.lower() for value in values]


def policy_scalar(policy, key):
    policy_inner = policy.get("policy", policy) if isinstance(policy, dict) else {}
    return str(policy_inner.get(key, "") or "").strip()


def participant_attributes_for_decision(participant_id="", participant=None):
    doc = participant if isinstance(participant, dict) else None
    if not doc and participant_id:
        doc = load_participant(participant_id)
    doc = doc if isinstance(doc, dict) else {}
    return {
        "participantId": str(doc.get("participantId", participant_id) or participant_id).strip(),
        "status": str(doc.get("status", "") or "").strip() or "unknown",
        "roles": normalize_list(doc.get("roles", [])),
        "credentialIds": normalize_list(doc.get("credentialIds", [])),
        "attributes": doc.get("attributes", {}) if isinstance(doc.get("attributes"), dict) else {},
    }


def evaluate_policy_decision(payload):
    payload = payload if isinstance(payload, dict) else {}
    participant = participant_attributes_for_decision(
        participant_id=str(payload.get("participantId", "") or "").strip(),
        participant=payload.get("participant") if isinstance(payload.get("participant"), dict) else None,
    )
    metadata = payload.get("metadata", {}) if isinstance(payload.get("metadata"), dict) else {}
    policy = payload.get("policy", {}) if isinstance(payload.get("policy"), dict) else {}
    action = str(payload.get("action", "use") or "use").strip().lower()
    purpose = str(payload.get("purpose", "") or "").strip()
    profile_id = str(payload.get("profile", "") or "").strip() or policy_profile_for_context(metadata, policy)
    profile = POLICY_PROFILE_DESCRIPTIONS.get(profile_id, POLICY_PROFILE_DESCRIPTIONS["restricted-provider-review"])
    validation = validate_policy_metadata(policy) if policy else {"ok": True, "missing": [], "warnings": []}

    reasons = []
    obligations = list(profile["obligations"])
    decision = profile["defaultDecision"]

    if participant["status"] != "active":
        decision = "deny"
        reasons.append("participant_not_active")

    if not set(participant["roles"]).intersection(set(profile["allowedRoles"])):
        decision = "deny"
        reasons.append("participant_role_not_allowed")

    prohibited = policy_actions(policy, "prohibition")
    permitted = policy_actions(policy, "permission")
    duties = policy_actions(policy, "duty")
    if action in prohibited:
        decision = "deny"
        reasons.append("action_prohibited_by_policy")
    if permitted and action not in permitted and "*" not in permitted:
        decision = "deny"
        reasons.append("action_not_permitted_by_policy")
    if duties:
        obligations.extend([duty for duty in duties if duty not in obligations])

    expected_purpose = policy_scalar(policy, "purpose")
    if expected_purpose and purpose and expected_purpose.lower() not in purpose.lower() and purpose.lower() not in expected_purpose.lower():
        if decision != "deny":
            decision = "review"
        reasons.append("purpose_requires_review")
    if not validation.get("ok"):
        if decision != "deny":
            decision = "review"
        reasons.append("policy_metadata_incomplete")

    access_rights = access_rights_from_metadata(metadata)
    if access_rights == "restricted" and decision == "grant":
        decision = "review"
        reasons.append("restricted_access_requires_review")

    if not reasons:
        reasons.append("policy_profile_matched")

    return {
        "ok": True,
        "decision": decision,
        "profile": policy_profile_doc(profile_id if profile_id in POLICY_PROFILE_DESCRIPTIONS else "restricted-provider-review"),
        "participant": participant,
        "action": action,
        "purpose": purpose,
        "accessRights": access_rights,
        "obligations": sorted(set(obligations)),
        "reasons": reasons,
        "validation": validation,
        "decidedAt": utc_now(),
    }


def canonical_filename(value):
    digest = hashlib.sha1(str(value or "").encode("utf-8")).hexdigest()
    return f"{digest}.json"


def participant_id_for_connector(connector_id):
    return f"participant:ods:{str(connector_id or '').strip()}"


def participant_path(participant_id):
    return PARTICIPANTS_DIR / canonical_filename(participant_id)




def contract_path(contract_id):
    return CONTRACTS_DIR / canonical_filename(contract_id)


def load_contract(contract_id):
    path = contract_path(contract_id)
    if not path.exists():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return doc if isinstance(doc, dict) else None


def list_contracts(status_filter="all", participant_id="", asset_id="", policy_id="", limit=100):
    if not CONTRACTS_DIR.exists():
        return []
    try:
        max_items = max(1, min(int(limit or 100), 1000))
    except Exception:
        max_items = 100
    items = []
    for path in sorted(CONTRACTS_DIR.glob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(doc, dict) or not doc.get("contractId"):
            continue
        if status_filter and status_filter != "all" and str(doc.get("status", "") or "") != status_filter:
            continue
        if participant_id and participant_id not in {
            str(doc.get("consumerParticipantId", "") or ""),
            str(doc.get("providerParticipantId", "") or ""),
        }:
            continue
        if asset_id and str(doc.get("assetId", "") or "") != asset_id:
            continue
        if policy_id and str(doc.get("policyId", "") or "") != policy_id:
            continue
        items.append(doc)
    return sorted(items, key=lambda item: str(item.get("updatedAt", "")), reverse=True)[:max_items]


def contract_history_event(event_type, contract_id, payload):
    return {
        "eventId": f"evt-{hashlib.sha1(f'{contract_id}:{event_type}:{time.time()}'.encode('utf-8')).hexdigest()[:16]}",
        "type": event_type,
        "occurredAt": utc_now(),
        "contractId": contract_id,
        "payload": payload,
    }


def save_contract(doc, event_type="", event_payload=None):
    CONTRACTS_DIR.mkdir(parents=True, exist_ok=True)
    contract_id = str(doc.get("contractId", "") or "").strip()
    if not contract_id:
        raise ValueError("missing_contract_id")
    now = utc_now()
    existing = load_contract(contract_id) or {}
    history = existing.get("history", []) if isinstance(existing.get("history"), list) else []
    if event_type:
        history.append(contract_history_event(event_type, contract_id, event_payload or {}))
    doc["history"] = history
    doc.setdefault("createdAt", existing.get("createdAt") or now)
    doc["updatedAt"] = now
    contract_path(contract_id).write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if event_type:
        audit_event_or_local(
            {
                "eventId": f"evt-{hashlib.sha1(f'{contract_id}:{event_type}:{now}'.encode('utf-8')).hexdigest()[:16]}",
                "traceId": doc.get("traceId", f"trace-contract-{hashlib.sha1(contract_id.encode('utf-8')).hexdigest()[:12]}"),
                "type": event_type,
                "occurredAt": now,
                "subject": {"type": "contract", "id": contract_id},
                "actor": {
                    "consumerParticipantId": doc.get("consumerParticipantId", ""),
                    "providerParticipantId": doc.get("providerParticipantId", ""),
                },
                "resource": {
                    "contractId": contract_id,
                    "assetId": doc.get("assetId", ""),
                    "policyId": doc.get("policyId", ""),
                },
                "decision": "record",
                "evidence": {
                    "contractStatus": doc.get("status", ""),
                    "policyDecision": (doc.get("policyDecision", {}) or {}).get("decision", ""),
                },
            }
        )
    return doc


def make_contract_id(asset_id, policy_id, consumer_participant_id):
    digest = hashlib.sha1(f"{asset_id}:{policy_id}:{consumer_participant_id}:{time.time()}".encode("utf-8")).hexdigest()[:16]
    return f"contract-{digest}"


def create_contract(payload):
    payload = payload if isinstance(payload, dict) else {}
    asset_id = str(payload.get("assetId", "") or "").strip()
    policy_id = str(payload.get("policyId", "") or "").strip()
    if not asset_id or not policy_id:
        raise ValueError("missing_asset_or_policy")
    consumer_participant_id = str(payload.get("consumerParticipantId") or payload.get("participantId") or "").strip()
    provider_participant_id = str(payload.get("providerParticipantId", "") or "").strip()
    contract_id = str(payload.get("contractId", "") or "").strip() or make_contract_id(asset_id, policy_id, consumer_participant_id)
    policy_decision = evaluate_policy_decision(
        {
            "participantId": consumer_participant_id,
            "participant": payload.get("consumerParticipant") if isinstance(payload.get("consumerParticipant"), dict) else payload.get("participant"),
            "metadata": payload.get("metadata", {}) if isinstance(payload.get("metadata"), dict) else {},
            "policy": payload.get("policy", {}) if isinstance(payload.get("policy"), dict) else {},
            "action": payload.get("action", "use"),
            "purpose": payload.get("purpose", ""),
            "profile": payload.get("policyProfile", ""),
        }
    )
    status = "active" if policy_decision.get("decision") == "grant" else "review"
    if policy_decision.get("decision") == "deny":
        status = "denied"
    trace_id = str(payload.get("traceId", "") or "").strip() or f"trace-contract-{hashlib.sha1(contract_id.encode('utf-8')).hexdigest()[:12]}"
    doc = {
        "contractId": contract_id,
        "assetId": asset_id,
        "policyId": policy_id,
        "status": status,
        "consumerParticipantId": consumer_participant_id,
        "providerParticipantId": provider_participant_id,
        "consumerConnectorId": str(payload.get("consumerConnectorId", "") or "").strip(),
        "providerConnectorId": str(payload.get("providerConnectorId", "") or "").strip(),
        "purpose": str(payload.get("purpose", "") or "").strip(),
        "action": str(payload.get("action", "use") or "use").strip(),
        "policyDecision": policy_decision,
        "obligations": policy_decision.get("obligations", []),
        "metadata": payload.get("metadata", {}) if isinstance(payload.get("metadata"), dict) else {},
        "policy": payload.get("policy", {}) if isinstance(payload.get("policy"), dict) else {},
        "traceId": trace_id,
        "source": "ciclo de vida del contrato",
    }
    return save_contract(doc, "contract.created", {"status": status, "assetId": asset_id, "policyId": policy_id})


def change_contract_status(contract_id, status, reason=""):
    doc = load_contract(contract_id)
    if not doc:
        raise ValueError("contract_not_found")
    normalized_status = str(status or "").strip()
    if normalized_status not in {"draft", "review", "active", "completed", "suspended", "revoked", "expired", "denied"}:
        raise ValueError("invalid_status")
    doc["status"] = normalized_status
    return save_contract(doc, "contract.status.changed", {"status": normalized_status, "reason": str(reason or "").strip()})




def ensure_governance_signing_key() -> Path:
    key_path = Path(AUDIT_PRIVATE_KEY_FILE)
    key_path.parent.mkdir(parents=True, exist_ok=True)
    if not key_path.exists():
        private_key = ec.generate_private_key(ec.SECP256R1())
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        key_path.write_bytes(pem)
    return key_path


def participant_history_event(event_type, participant_id, payload):
    return {
        "eventId": f"evt-{hashlib.sha1(f'{participant_id}:{event_type}:{time.time()}'.encode('utf-8')).hexdigest()[:16]}",
        "type": event_type,
        "occurredAt": utc_now(),
        "participantId": participant_id,
        "payload": payload,
    }


def load_participant(participant_id):
    path = participant_path(participant_id)
    if not path.exists():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return doc if isinstance(doc, dict) else None


def save_participant(doc, event_type="", event_payload=None):
    PARTICIPANTS_DIR.mkdir(parents=True, exist_ok=True)
    participant_id = str(doc.get("participantId", "") or "").strip()
    if not participant_id:
        raise ValueError("missing_participant_id")
    now = utc_now()
    existing = load_participant(participant_id) or {}
    history = existing.get("history", []) if isinstance(existing.get("history"), list) else []
    if event_type:
        history.append(participant_history_event(event_type, participant_id, event_payload or {}))
    doc["history"] = history
    doc.setdefault("createdAt", existing.get("createdAt") or now)
    doc["updatedAt"] = now
    participant_path(participant_id).write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if event_type:
        audit_event_or_local(
            {
                "eventId": f"evt-{hashlib.sha1(f'{participant_id}:{event_type}:{now}'.encode('utf-8')).hexdigest()[:16]}",
                "traceId": f"trace-participant-{hashlib.sha1(participant_id.encode('utf-8')).hexdigest()[:12]}",
                "type": event_type,
                "occurredAt": now,
                "subject": {"type": "participant", "id": participant_id},
                "actor": {"participantId": participant_id, "connectorId": doc.get("attributes", {}).get("connectorId", "")},
                "resource": {"participantId": participant_id},
                "decision": "record",
            }
        )
    return doc


def build_participant_doc(connector_id, email, client_id="", role_mode="consumer", status="active", credential_ids=None):
    roles = requested_roles_for_mode(role_mode)
    identity_attributes = identity_attribute_ids_for_mode(role_mode)
    participant_id = participant_id_for_connector(connector_id)
    return {
        "participantId": participant_id,
        "nodeId": AUDIT_ISSUER,
        "status": status,
        "roles": roles,
        "identityAttributes": identity_attributes,
        "attributes": {
            "dataspaceId": organisation_id() or CONNECTOR_ID,
            "connectorId": connector_id,
            "email": normalize_user_identity(email),
            "keycloakClientId": client_id,
            "organizationType": "participant",
            "capabilities": ["consume"] + (["publish"] if "provider" in roles else []),
            "identityAttributes": identity_attributes,
        },
        "credentialIds": credential_ids or [],
    }


def upsert_participant_for_connector(connector_id, email, client_id="", role_mode="consumer", status="active"):
    participant_id = participant_id_for_connector(connector_id)
    existing = load_participant(participant_id) or {}
    credential_ids = existing.get("credentialIds", []) if isinstance(existing.get("credentialIds"), list) else []
    doc = build_participant_doc(connector_id, email, client_id, role_mode, status, credential_ids)
    return save_participant(doc, "participant.upserted", {"connectorId": connector_id, "roles": doc["roles"], "status": status})


def sync_participant_from_bootstrap(payload):
    payload = payload if isinstance(payload, dict) else {}
    connector_id = str(payload.get("connectorId", "") or "").strip()
    if not connector_id:
        raise ValueError("missing_connector_id")
    role_mode = normalize_role_mode(payload.get("roleProfile") or payload.get("mode") or "consumer")
    client_id = str(payload.get("clientId", "") or payload.get("keycloakClientId", "") or connector_id).strip()
    email = normalize_user_identity(payload.get("email") or payload.get("owner") or f"{connector_id}@localhost.invalid")
    status = str(payload.get("status", "active") or "active").strip()
    if status not in {"active", "suspended", "revoked", "retired"}:
        raise ValueError("invalid_status")
    participant = upsert_participant_for_connector(connector_id, email, client_id, role_mode=role_mode, status=status)
    requested_attributes = normalize_list(payload.get("identityAttributes", identity_attribute_ids_for_mode(role_mode)))
    if requested_attributes:
        participant["identityAttributes"] = sorted(set(requested_attributes))
        participant.setdefault("attributes", {})
        participant["attributes"]["identityAttributes"] = participant["identityAttributes"]
        participant = save_participant(
            participant,
            "participant.identity_attributes.synced",
            {"connectorId": connector_id, "identityAttributes": participant["identityAttributes"]},
        )
    return participant


def list_participants():
    migrate_connectors_to_participants()
    items = []
    if not PARTICIPANTS_DIR.exists():
        return items
    for path in sorted(PARTICIPANTS_DIR.glob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(doc, dict) and doc.get("participantId"):
            items.append(doc)
    return items














def seed_predefined_participants():
    """Los tres conectores predefinidos son participantes, y se anotan como tales.

    Quien es participante se respondía en tres sitios que no se hablaban:
    STATIC_CONNECTOR_DIRECTORY en el código, el registro de participantes y los
    grupos de Keycloak. El 23 de agosto de 2026 no había un solo conector
    presente en los tres a la vez en ningún dominio, y el registro -- el que
    consulta gobernanza para federar -- estaba vacío en los dos participantes.

    A partir de aquí el registro es la fuente: los predefinidos se siembran en
    él una vez, los generados los escribe el alta, y el catálogo, la
    registración ante gobernanza y los grupos se derivan de él.

    Idempotente: si el participante ya existe no se toca, para no pisar un
    estado que alguien haya cambiado a mano (suspended, revoked).
    """
    for connector_id, entry in STATIC_CONNECTOR_DIRECTORY.items():
        participant_id = participant_id_for_connector(connector_id)
        if load_participant(participant_id):
            continue
        profile = PREDEFINED_CONNECTOR_PROFILE.get(connector_id, {})
        upsert_participant_for_connector(
            connector_id,
            entry.get("email", ""),
            profile.get("keycloakClientId", f"edc-{connector_id}"),
            role_mode=profile.get("roleMode", "consumer"),
            status=str(entry.get("status", "active") or "active"),
        )


def migrate_connectors_to_participants():
    seed_predefined_participants()
    if not CONNECTORS_DIR.exists():
        return
    for path in sorted(CONNECTORS_DIR.glob("connector-*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        connector_id = str(doc.get("connector_id", "") or "").strip()
        email = normalize_user_identity(doc.get("email", ""))
        if not connector_id:
            continue
        participant_id = participant_id_for_connector(connector_id)
        if load_participant(participant_id):
            continue
        roles = doc.get("roles", []) if isinstance(doc.get("roles"), list) else []
        role_mode = "consumer"
        if "provider" in roles and "consumer" in roles:
            role_mode = "both"
        elif "provider" in roles:
            role_mode = "provider"
        upsert_participant_for_connector(
            connector_id,
            email,
            str(doc.get("keycloak_client_id", "") or "").strip(),
            role_mode=role_mode,
            status="active" if str(doc.get("status", "") or "").strip() in {"", "deployed", "active"} else str(doc.get("status")),
        )


NODE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")


def local_node_entry():
    """El nodo propio, siempre el primero de la lista.

    No se guarda en el fichero: se compone del conector de este nodo en cada
    lectura. Guardarlo dejaria una copia que se queda vieja en cuanto cambia
    ODS_CONNECTOR_ID o la direccion publica.
    """
    return {
        "id": CONNECTOR_ID,
        "label": dataspace_label(),
        "baseUrl": CONNECTOR_MANAGEMENT_URL,
        "local": True,
        # El estado y la fecha salen de la ultima sincronizacion, no de una
        # constante: un nodo propio que se declara siempre «up» y «nunca
        # sincronizado» a la vez es justo lo que nadie sabe interpretar.
        "status": LOCAL_NODE_STATE["status"],
        "addedAt": "",
        "lastSyncAt": LOCAL_NODE_STATE["lastSyncAt"],
    }


def load_known_nodes():
    if not KNOWN_NODES_FILE.exists():
        return []
    try:
        payload = json.loads(KNOWN_NODES_FILE.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return []
    return [item for item in payload if isinstance(item, dict)] if isinstance(payload, list) else []


def save_known_nodes(items):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    KNOWN_NODES_FILE.write_text(
        json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def list_known_nodes():
    """El nodo propio primero, y despues los remotos en el orden en que se anadieron."""
    return [local_node_entry()] + load_known_nodes()


def add_known_node(label, base_url, node_id=""):
    label = str(label or "").strip()
    base_url = str(base_url or "").strip().rstrip("/")
    if not base_url:
        raise ValueError("missing_base_url")
    parsed = parse.urlparse(base_url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("invalid_base_url")

    node_id = str(node_id or "").strip().lower() or slugify_fragment(label or parsed.netloc)
    if not NODE_ID_RE.match(node_id):
        raise ValueError("invalid_node_id")
    if node_id == CONNECTOR_ID:
        # El nodo propio ya esta en la lista y no se anade dos veces: su
        # oferta entraria en el grafo consolidado por duplicado.
        raise ValueError("node_is_local")

    items = load_known_nodes()
    if any(item.get("id") == node_id for item in items):
        raise ValueError("node_already_known")

    entry = {
        "id": node_id,
        "label": label or parsed.netloc,
        "baseUrl": base_url,
        "local": False,
        # Un nodo recien anadido no esta caido: esta sin sincronizar todavia,
        # que no es lo mismo y la consola tiene que poder distinguirlo.
        "status": "pending",
        "addedAt": utc_now(),
        "lastSyncAt": "",
        "lastError": "",
    }
    items.append(entry)
    save_known_nodes(items)
    return entry


def remove_known_node(node_id):
    node_id = str(node_id or "").strip().lower()
    items = load_known_nodes()
    remaining = [item for item in items if item.get("id") != node_id]
    if len(remaining) == len(items):
        return False
    save_known_nodes(remaining)
    return True


def mark_node_sync(node_id, ok, error=""):
    """Anota el resultado de la ultima sincronizacion de un nodo.

    Un nodo que no contesta se marca como no disponible y **conserva su ultima
    fecha de sincronizacion correcta**: su grafo sigue en Fuseki y su oferta se
    sigue viendo, con la fecha a la vista para que se sepa de cuando es. Un
    nodo caido no vacia la vista de los demas.
    """
    items = load_known_nodes()
    for item in items:
        if item.get("id") != str(node_id or "").strip().lower():
            continue
        if ok:
            item["status"] = "up"
            item["lastSyncAt"] = utc_now()
            item["lastError"] = ""
        else:
            item["status"] = "unreachable"
            item["lastError"] = str(error or "")[:400]
        save_known_nodes(items)
        return item
    return None


# --- El catalogo federado consolidado -----------------------------------
#
# Es la vista que hace que esto sea un espacio de datos y no un catalogo
# aislado. Vive aqui, dentro de este servicio, y no en un contenedor propio:
# el intervalo, la lista de nodos y el boton de «actualizar ahora» de la
# consola estan todos de este lado, y sacarlo fuera obliga a duplicarlos.
FEDERATOR_SCRIPT = ROOT / "federation" / "federator" / "federate-catalogues.sh"
FUSEKI_URL = os.getenv("ODS_FUSEKI_URL", "").strip().rstrip("/") or "http://fuseki:3030"
FUSEKI_DATASET = os.getenv("ODS_FUSEKI_DATASET", "").strip() or "dataspace"
FUSEKI_ADMIN_USER = os.getenv("ODS_FUSEKI_ADMIN_USER", "").strip() or "admin"
FUSEKI_ADMIN_PASSWORD = os.getenv("ODS_FUSEKI_ADMIN_PASSWORD", "")
GRAPH_BASE_IRI = "urn:ods:catalog"
# El punto de consulta SPARQL, cerrado por omision. Quien quiera exponerlo en
# solo lectura lo activa aqui; abrirlo publica el catalogo consolidado entero
# -- incluida la oferta de los demas nodos -- a cualquiera que lo pida.
SPARQL_PUBLIC = os.getenv("ODS_SPARQL_PUBLIC", "false").strip().lower() in ("true", "1", "yes")
# Lo unico que se admite. Fuseki separa /query de /update, pero una consulta
# tambien puede modificar si se cuela por la puerta de la actualizacion, y
# aqui no hay ninguna razon para aceptar nada que no sea leer.
SPARQL_READ_ONLY = ("select", "ask", "describe", "construct")
try:
    FEDERATION_INTERVAL = max(30, int(os.getenv("ODS_FEDERATION_INTERVAL", "300") or 300))
except ValueError:
    FEDERATION_INTERVAL = 300

FEDERATION_STATE = {"lastRunAt": "", "lastResult": "", "running": False}
# El nodo propio no se guarda en el fichero de nodos conocidos, asi que su
# estado vive aqui. Se pierde al reiniciar, que es correcto: la primera
# sincronizacion tras el arranque lo vuelve a poner.
LOCAL_NODE_STATE = {"status": "pending", "lastSyncAt": ""}
FEDERATION_LOCK = threading.Lock()


def sparql_update(update):
    """Manda un UPDATE a Fuseki. Devuelve True si lo acepto."""
    data = parse.urlencode({"update": update}).encode("utf-8")
    req = request.Request(f"{FUSEKI_URL}/{FUSEKI_DATASET}/update", method="POST", data=data)
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    credentials = base64.b64encode(
        f"{FUSEKI_ADMIN_USER}:{FUSEKI_ADMIN_PASSWORD}".encode("utf-8")
    ).decode("ascii")
    req.add_header("Authorization", f"Basic {credentials}")
    try:
        with request.urlopen(req, timeout=20):
            return True
    except Exception as exc:  # noqa: BLE001 - se dice, no se traga
        print(f"[federation] WARN no se pudo actualizar Fuseki: {exc}")
        return False


def sparql_first_keyword(query):
    """La primera palabra clave de la consulta, saltandose prefijos y comentarios.

    Se recorre en vez de usar una expresion regular porque los tres sitios
    donde puede aparecer una almohadilla no se distinguen a ojo: un comentario,
    el fragmento de un IRI -- `<http://www.w3.org/ns/dcat#>`, que sale en casi
    cualquier consulta con prefijos -- y el interior de un literal. Quitar
    comentarios con `#[^\n]*` se come el resto de la linea a partir del IRI y
    convierte una SELECT legitima en algo que no se parece a nada.
    """
    texto = str(query or "")
    limpio = []
    i, n = 0, len(texto)
    while i < n:
        c = texto[i]
        if c == "#":
            # Comentario: hasta el final de la linea.
            salto = texto.find("\n", i)
            i = n if salto == -1 else salto
            continue
        if c == "<":
            # IRI: se copia entero, almohadillas incluidas.
            cierre = texto.find(">", i)
            if cierre == -1:
                break
            limpio.append(texto[i:cierre + 1])
            i = cierre + 1
            continue
        if c in "\"'":
            # Literal: se copia entero.
            cierre = texto.find(c, i + 1)
            if cierre == -1:
                break
            limpio.append(texto[i:cierre + 1])
            i = cierre + 1
            continue
        limpio.append(c)
        i += 1

    restante = "".join(limpio)
    # PREFIX y BASE pueden venir en cualquier numero y en cualquier orden.
    while True:
        sin_prefijo = re.sub(
            r"^\s*(?:prefix\s+[^\s:]*:\s*<[^>]*>|base\s*<[^>]*>)\s*",
            "",
            restante,
            count=1,
            flags=re.I,
        )
        if sin_prefijo == restante:
            break
        restante = sin_prefijo

    partes = restante.strip().split(None, 1)
    return partes[0].lower() if partes else ""


def sparql_query_is_read_only(query):
    """Solo pasan SELECT, ASK, DESCRIBE y CONSTRUCT.

    Se mira la primera palabra clave, no si la cadena contiene «insert»:
    buscar la palabra en cualquier parte rechaza una consulta legitima que la
    tenga dentro de un literal, y no mirar nada deja pasar un DELETE detras de
    un PREFIX.
    """
    return sparql_first_keyword(query) in SPARQL_READ_ONLY


def sparql_select(query):
    """Ejecuta una consulta de lectura contra Fuseki y devuelve su respuesta."""
    data = parse.urlencode({"query": query}).encode("utf-8")
    req = request.Request(f"{FUSEKI_URL}/{FUSEKI_DATASET}/query", method="POST", data=data)
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("Accept", "application/sparql-results+json")
    credentials = base64.b64encode(
        f"{FUSEKI_ADMIN_USER}:{FUSEKI_ADMIN_PASSWORD}".encode("utf-8")
    ).decode("ascii")
    req.add_header("Authorization", f"Basic {credentials}")
    with request.urlopen(req, timeout=30) as response:
        return response.read(), response.headers.get("Content-Type", "application/sparql-results+json")


def drop_node_graph(node_id):
    """Retira el grafo de un nodo sin tocar el resto del almacen."""
    graph_iri = f"{GRAPH_BASE_IRI}/{node_id}"
    return sparql_update(f"DROP SILENT GRAPH <{graph_iri}>")


def run_federation_now():
    """Sincroniza el catalogo consolidado una vez.

    No lanza nunca. El catalogo consolidado no puede bloquear la operacion:
    publicar, negociar y descargar tienen que seguir funcionando con Fuseki
    caido, y lo unico que se pierde es la vista consolidada.
    """
    if not FEDERATOR_SCRIPT.exists():
        return {"ok": False, "detail": "federator_not_found"}
    if FEDERATION_STATE["running"]:
        return {"ok": False, "detail": "already_running"}

    with FEDERATION_LOCK:
        FEDERATION_STATE["running"] = True
        try:
            environment = dict(os.environ)
            environment.update({
                "FEDERATION_NODES_FILE": str(KNOWN_NODES_FILE),
                "FUSEKI_BASE_URL": FUSEKI_URL,
                "FUSEKI_DATASET": FUSEKI_DATASET,
                "FUSEKI_ADMIN_USER": FUSEKI_ADMIN_USER,
                "FUSEKI_ADMIN_PASSWORD": FUSEKI_ADMIN_PASSWORD,
                "GRAPH_BASE_IRI": GRAPH_BASE_IRI,
                "KEYCLOAK_URL": KEYCLOAK_URL,
                "KEYCLOAK_REALM": REALM_NAME,
                # El federador resuelve por si mismo el secreto de la cuenta
                # de servicio de cada conector; para eso necesita hablar con
                # la administracion de Keycloak. Sin esto, todos los nodos
                # -- incluido el propio -- salen como no disponibles.
                "KEYCLOAK_ADMIN_USER": KEYCLOAK_ADMIN_USER,
                "KEYCLOAK_ADMIN_PASSWORD": KEYCLOAK_ADMIN_PASSWORD,
                # Un catalogo vacio no se publica: se conserva el grafo
                # anterior. Un nodo que deja de contestar no debe vaciar su
                # propia oferta de la vista de los demas.
                "FEDERATION_PUBLISH_EMPTY_CATALOG": "false",
            })
            # El nodo propio tiene que entrar en la lista que lee el guion, y
            # en el fichero solo estan los remotos.
            nodes_payload = [
                {
                    "id": node["id"],
                    "baseUrl": node["baseUrl"],
                    "clientId": CONNECTOR_CLIENT_ID if node.get("local") else "",
                    "clientSecret": "",
                    "role": node.get("role", "provider"),
                    # Lo que decide si se lee por la API de gestion con token o
                    # por el catalogo publico del nodo.
                    "local": bool(node.get("local")),
                }
                for node in list_known_nodes()
            ]
            nodes_file = DATA_DIR / "federation_nodes.json"
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            nodes_file.write_text(json.dumps(nodes_payload, ensure_ascii=False), encoding="utf-8")
            environment["FEDERATION_NODES_FILE"] = str(nodes_file)

            completed = subprocess.run(
                ["bash", str(FEDERATOR_SCRIPT)],
                capture_output=True,
                text=True,
                timeout=300,
                env=environment,
                cwd=str(ROOT),
            )
            salida = completed.stdout or ""
            for linea in salida.splitlines():
                if not linea.startswith("federation_connector="):
                    continue
                # federation_connector=<id> outcome=<estado>
                partes = dict(
                    trozo.split("=", 1) for trozo in linea.split() if "=" in trozo
                )
                node_id = partes.get("federation_connector", "")
                outcome = partes.get("outcome", "")
                if not node_id:
                    continue
                if node_id == CONNECTOR_ID:
                    LOCAL_NODE_STATE["status"] = (
                        "unreachable" if outcome == "unavailable" else "up"
                    )
                    if outcome != "unavailable":
                        LOCAL_NODE_STATE["lastSyncAt"] = utc_now()
                else:
                    mark_node_sync(node_id, outcome != "unavailable", outcome)
            FEDERATION_STATE["lastRunAt"] = utc_now()
            FEDERATION_STATE["lastResult"] = "ok" if completed.returncode == 0 else "failed"
            return {
                "ok": completed.returncode == 0,
                "lastRunAt": FEDERATION_STATE["lastRunAt"],
                "summary": next(
                    (l for l in salida.splitlines() if l.startswith("federation_summary")),
                    "",
                ),
            }
        except Exception as exc:  # noqa: BLE001 - se dice, no se traga
            FEDERATION_STATE["lastResult"] = f"error: {exc}"
            print(f"[federation] WARN la sincronizacion fallo: {exc}")
            return {"ok": False, "detail": str(exc)}
        finally:
            FEDERATION_STATE["running"] = False


SEED_SCRIPT = ROOT / "app" / "tools" / "seed_demo.py"


def seed_demo_when_ready(attempts=30, delay=5):
    """Publica el ejemplo en cuanto el conector conteste.

    Reintenta porque el conector y este servicio arrancan a la vez y el
    conector tarda mas: sin reintentos, el ejemplo se pierde en cada arranque
    limpio y el nodo ensena la pantalla vacia que este ejemplo existe para
    evitar. No es fatal, y si se rinde lo dice.
    """
    if not SEED_SCRIPT.exists():
        return
    for intento in range(attempts):
        try:
            completed = subprocess.run(
                [sys.executable, str(SEED_SCRIPT)],
                capture_output=True, text=True, timeout=120, cwd=str(ROOT),
            )
            if completed.returncode == 0:
                print((completed.stdout or "").strip())
                # Publicado: el catalogo consolidado tiene algo que recoger.
                run_federation_now()
                return
            if intento == attempts - 1:
                print(f"[seed] WARN {(completed.stderr or '').strip()}")
        except Exception as exc:  # noqa: BLE001 - se dice, no se traga
            if intento == attempts - 1:
                print(f"[seed] WARN {exc}")
        time.sleep(delay)


def federation_loop():
    """Sincroniza cada ODS_FEDERATION_INTERVAL segundos, para siempre."""
    while True:
        try:
            run_federation_now()
        except Exception as exc:  # noqa: BLE001 - el bucle no se muere
            print(f"[federation] WARN {exc}")
        time.sleep(FEDERATION_INTERVAL)


# --- El paso hacia la API de gestion del conector ------------------------
#
# La consola necesita publicar activos, crear politicas y abrir negociaciones,
# y todo eso vive en la API de gestion del conector, que NO se publica: en la
# composicion no hay una ruta de Caddy que llegue a ella.
#
# Este paso la alcanza por la red interna y **reenvia el token de quien llama**
# tal cual. No es un puente que concede permisos: el conector sigue decidiendo
# con el mismo RBAC de siempre, y quien no tenga el rol recibe su 403 igual que
# si hablara con el directamente. Lo unico que cambia es por donde entra.
CONNECTOR_PROXY_PREFIX = "/api/connector"
# Solo la superficie que la consola usa. Una lista blanca y no un reenvio de
# todo: abrir el paso entero es publicar la API de administracion del conector
# con un rodeo.
CONNECTOR_PROXY_ALLOWED = (
    "assets",
    "policydefinitions",
    "contractdefinitions",
    "negotiations",
)


def proxy_to_connector(handler, method, path, body=None):
    suffix = path[len(CONNECTOR_PROXY_PREFIX):].lstrip("/")
    if not suffix.startswith("v3/"):
        return json_response(handler, 404, {"error": "not_found"})
    recurso = suffix[len("v3/"):].split("/", 1)[0].split("?", 1)[0]
    if recurso not in CONNECTOR_PROXY_ALLOWED:
        return json_response(handler, 404, {"error": "not_found"})

    authorization = handler.headers.get("Authorization", "")
    if not authorization and not EVALUATION_MODE:
        # Sin token no se pasa: el conector contestaria 401 igual, pero
        # decirlo aqui ahorra el salto y deja el motivo claro.
        return json_response(handler, 401, {"error": "missing_token"})

    url = f"{CONNECTOR_MANAGEMENT_URL}/management/{suffix}"
    req = request.Request(url, method=method, data=body)
    if authorization:
        req.add_header("Authorization", authorization)
    req.add_header("Accept", "application/json")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with request.urlopen(req, timeout=30) as response:
            payload = response.read()
            status = response.status
            content_type = response.headers.get("Content-Type", "application/json")
    except urllib_error.HTTPError as exc:
        # El cuerpo del error del conector es la parte util -- dice que rol
        # falta, o que la negociacion no esta cerrada -- y tragarselo para
        # devolver un 502 generico es lo que convierte un mensaje claro en un
        # «no se pudo».
        payload = exc.read()
        status = exc.code
        content_type = exc.headers.get("Content-Type", "application/json")
    except Exception as exc:  # noqa: BLE001 - se dice, no se traga
        return json_response(handler, 502, {"error": "connector_unreachable", "detail": str(exc)[:200]})

    handler.send_response(status)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(payload)))
    handler.end_headers()
    handler.wfile.write(payload)
    return None


# --- El catalogo publico de este nodo ------------------------------------
#
# Es lo unico que un nodo expone para que otro pueda federarlo, y existe
# porque la alternativa no funciona: el federador de origen leia la API de
# gestion del conector con un token de Keycloak. Eso vale dentro de un nodo y
# es imposible entre organizaciones -- el nodo A no tiene credenciales en el
# Keycloak del nodo B -- y ademas obligaria a publicar la superficie de
# administracion del conector, que es justo lo que la seccion 3 no hace.
#
# Aqui se publica la oferta y nada mas: que hay, bajo que politica y bajo que
# contrato. Ni usuarios, ni solicitudes, ni el registro de operaciones.
CATALOG_CACHE = {"at": 0.0, "payload": None}
CATALOG_CACHE_SECONDS = 30


def connector_service_token():
    """Un token de la cuenta de servicio del conector de ESTE nodo.

    El secreto no vive en el arbol: se pide a Keycloak con las credenciales de
    administracion que la composicion ya pasa a este servicio.
    """
    if EVALUATION_MODE:
        # No hay Keycloak del que pedirlo, y el conector no lo mira.
        return ""
    token = get_admin_token()
    clients = kc_request(
        "GET", f"/admin/realms/{REALM_NAME}/clients", token=token,
        query={"clientId": CONNECTOR_CLIENT_ID},
    ) or []
    if not clients:
        raise RuntimeError(f"el cliente {CONNECTOR_CLIENT_ID} no existe")
    secret = kc_request(
        "GET", f"/admin/realms/{REALM_NAME}/clients/{clients[0]['id']}/client-secret",
        token=token,
    ) or {}
    client_secret = secret.get("value", "")
    if not client_secret:
        raise RuntimeError(f"el cliente {CONNECTOR_CLIENT_ID} no tiene secreto")

    data = parse.urlencode({
        "client_id": CONNECTOR_CLIENT_ID,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
    }).encode("utf-8")
    req = request.Request(
        f"{KEYCLOAK_URL}/realms/{REALM_NAME}/protocol/openid-connect/token",
        method="POST", data=data,
    )
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))["access_token"]


def local_catalog(force=False):
    """La oferta de este nodo, leida de su propio conector.

    Con cache corta: el federador de cada nodo remoto llama aqui, y sin ella
    un espacio de datos de diez nodos convierte cada sincronizacion en diez
    lecturas completas de la base.
    """
    now = time.time()
    if not force and CATALOG_CACHE["payload"] is not None and now - CATALOG_CACHE["at"] < CATALOG_CACHE_SECONDS:
        return CATALOG_CACHE["payload"]

    token = connector_service_token()
    catalog = {
        "nodeId": CONNECTOR_ID,
        "label": dataspace_label(),
        "publicUrl": default_public_base_url(),
        # El contacto del participante, que es el cuarto sitio al que el
        # correo del administrador tiene que llegar -- los otros tres son el
        # usuario administrador del realm, el registro ACME del certificado y
        # el destinatario de los avisos. Es lo que permite que quien vea esta
        # oferta desde otro nodo sepa a quien escribir.
        "contactPoint": {
            "organisation": dataspace_label(),
            "organisationId": organisation_id(),
            "email": admin_email(),
        },
        "generatedAt": utc_now(),
    }
    for clave, ruta in (
        ("assets", "assets"),
        ("policies", "policydefinitions"),
        ("contracts", "contractdefinitions"),
    ):
        req = request.Request(f"{CONNECTOR_MANAGEMENT_URL}/management/v3/{ruta}")
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Accept", "application/json")
        with request.urlopen(req, timeout=20) as response:
            raw = response.read()
            catalog[clave] = json.loads(raw.decode("utf-8")) if raw else []

    CATALOG_CACHE["at"] = now
    CATALOG_CACHE["payload"] = catalog
    return catalog


# --- Asistente de primer arranque ---------------------------------------
#
# Es lo que separa un producto que la gente instala de uno que abandona: un
# nodo recien levantado no ensena una consola vacia ni un fichero que editar,
# sino cuatro preguntas.
#
# El estado «configurado» vive en el volumen y no en el .env a proposito. La
# imagen todo-en-uno se arranca con `docker run` y sin ningun .env, y tiene que
# poder configurarse igual; y una instalacion que ya paso por aqui no puede
# volver a la pantalla de configuracion porque alguien actualizo la imagen.


def is_configured():
    return SETUP_MARKER_FILE.exists()


def load_site_overrides():
    if not SITE_OVERRIDES_FILE.exists():
        return {}
    try:
        payload = json.loads(SITE_OVERRIDES_FILE.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


def save_site_overrides(values):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SITE_OVERRIDES_FILE.write_text(
        json.dumps(values, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def admin_email():
    """El correo del administrador, con lo que el asistente haya decidido.

    Leerlo solo del entorno era un fallo silencioso: el asistente guardaba la
    direccion nueva, la interfaz la mostraba -- porque runtime-config.js se
    regenera con ella -- y el backend seguia publicando la del .env en el
    contacto del participante. Uno de los cuatro sitios a los que este correo
    tiene que llegar quedaba con el valor de ejemplo.
    """
    return load_site_overrides().get("adminEmail") or REQUESTS_MASTER_EMAIL


def organisation_id():
    return load_site_overrides().get("orgId") or os.getenv("ODS_ORG_ID", "").strip()


def setup_state():
    """Lo que el asistente necesita saber para pintarse.

    Devuelve los valores que ya vienen del .env, para que quien haya pasado
    por install.sh se encuentre las casillas rellenas y solo tenga que
    confirmar. La contrasena nunca sale de aqui.
    """
    overrides = load_site_overrides()
    return {
        "configured": is_configured(),
        "orgName": overrides.get("orgName") or os.getenv("ODS_ORG_NAME", "").strip(),
        "orgId": overrides.get("orgId") or os.getenv("ODS_ORG_ID", "").strip(),
        "adminEmail": overrides.get("adminEmail") or REQUESTS_MASTER_EMAIL,
        "lang": overrides.get("lang") or DEFAULT_LANG,
        "brandColor": overrides.get("brandColor") or os.getenv("ODS_BRAND_COLOR", "").strip() or "#1f5fd0",
        "logoPath": overrides.get("logoPath") or os.getenv("ODS_LOGO_PATH", "").strip(),
        "legalNotice": overrides.get("legalNotice") or os.getenv("ODS_LEGAL_NOTICE", "").strip(),
        "publicUrl": default_public_base_url(),
        "connectorId": CONNECTOR_ID,
        # Keycloak tarda mas en subir que este servicio, y el asistente es lo
        # primero que alguien abre en una instalacion nueva: sin esto, quien
        # llegue rapido pulsa Finalizar y recibe un «Connection refused» en
        # crudo, que no le dice ni que ha pasado ni que basta con esperar.
        "identityReady": identity_is_ready(),
    }


def identity_is_ready():
    """Si Keycloak ya contesta. No lanza: es una pregunta, no una operacion."""
    if EVALUATION_MODE:
        # No hay identidad que esperar, y decir que no esta lista dejaria el
        # asistente sin poder terminar nunca.
        return True
    try:
        with request.urlopen(
            f"{KEYCLOAK_URL}/realms/{REALM_NAME}/.well-known/openid-configuration",
            timeout=5,
        ) as response:
            return response.status == 200
    except Exception:  # noqa: BLE001 - cualquier fallo significa «todavia no»
        return False


def ensure_admin_user(email, password):
    """Crea el administrador del nodo en Keycloak y lo mete en su grupo.

    Idempotente: si la cuenta ya existe se le fija la contrasena y se le
    aseguran los grupos, en vez de fallar. Reconfigurar un nodo con la misma
    direccion no puede quedarse a medias por eso.
    """
    user_id, created = ensure_keycloak_user(email, password, first_name="Admin")
    if not user_id:
        raise RuntimeError("no se pudo crear el administrador en Keycloak")
    token = get_admin_token()
    if not created:
        # La cuenta ya existía -- un nodo que se reconfigura, o una dirección
        # que ya pasó por el alta. Aquí sí se le fija la contraseña: quien
        # ejecuta el asistente es el dueño del nodo y acaba de escribirla, y
        # devolverle un «listo» dejándole una contraseña que no es la que puso
        # es peor que fallar.
        kc_request(
            "PUT",
            f"/admin/realms/{REALM_NAME}/users/{user_id}/reset-password",
            token=token,
            payload={"type": "password", "value": password, "temporary": False},
        )
    for group in ("dataspace-users", "dataspace-negotiators", "dataspace-admins", "connector-users"):
        try:
            ensure_user_in_group(user_id, group, token)
        except Exception as exc:  # noqa: BLE001 - se dice, no se traga
            print(f"[setup] WARN no se pudo anadir {email} a {group}: {exc}")
    return user_id


def apply_setup(payload):
    """Aplica el asistente. Devuelve a donde hay que ir despues.

    El orden importa: primero lo que puede fallar y es reversible sin dejar
    rastro -- validar --, despues la identidad, y el marcador al final. Marcar
    el nodo como configurado antes de tener administrador dejaria un nodo sin
    forma de entrar y sin forma de volver al asistente.
    """
    org_name = str(payload.get("orgName", "")).strip()
    org_id = str(payload.get("orgId", "")).strip().lower() or slugify_fragment(org_name)
    email = normalize_user_identity(payload.get("adminEmail", ""))
    password = str(payload.get("adminPassword", ""))
    lang = "en" if str(payload.get("lang", "")).lower().startswith("en") else "es"

    if not org_name:
        raise ValueError("missing_org_name")
    if not EMAIL_RE.match(email):
        raise ValueError("invalid_email")
    if not PASSWORD_RE.match(password):
        raise ValueError("weak_password")
    if not NODE_ID_RE.match(org_id):
        raise ValueError("invalid_org_id")
    if not identity_is_ready():
        # Se comprueba antes de escribir nada. Fallar a mitad dejaria ajustes
        # guardados sin administrador que los use.
        raise ValueError("identity_not_ready")

    if not EVALUATION_MODE:
        ensure_admin_user(email, password)

    overrides = {
        "orgName": org_name,
        "orgId": org_id,
        "adminEmail": email,
        "lang": lang,
        "brandColor": str(payload.get("brandColor", "")).strip() or "#1f5fd0",
        "logoPath": str(payload.get("logoPath", "")).strip(),
        "legalNotice": str(payload.get("legalNotice", "")).strip(),
        "configuredAt": utc_now(),
    }
    save_site_overrides(overrides)

    # El participante de este nodo, con la direccion que acaba de darse.
    try:
        upsert_participant_for_connector(
            CONNECTOR_ID, email, CONNECTOR_CLIENT_ID, role_mode="both", status="active"
        )
    except Exception as exc:  # noqa: BLE001 - se dice, no se traga
        print(f"[setup] WARN no se pudo registrar el participante: {exc}")

    # La consola se regenera con la marca y el dueno nuevos.
    try:
        write_connector_pages(CONNECTOR_ID, email, role_mode="both")
    except Exception as exc:  # noqa: BLE001
        print(f"[setup] WARN no se pudo regenerar la consola: {exc}")

    render_site_config()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SETUP_MARKER_FILE.write_text(
        json.dumps({"configuredAt": overrides["configuredAt"], "adminEmail": email},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # El ejemplo, si se ha pedido, en su propio hilo: el conector puede tardar
    # y el asistente tiene que devolver ya.
    if os.getenv("ODS_SEED_DEMO", "true").strip().lower() not in ("false", "0", "no"):
        threading.Thread(target=seed_demo_when_ready, name="seed-demo", daemon=True).start()

    return console_page_name(lang)


def render_site_config():
    """Reescribe runtime-config.js con lo que el asistente ha decidido."""
    entorno = dict(os.environ)
    overrides = load_site_overrides()
    for clave, variable in (
        ("orgName", "ODS_ORG_NAME"),
        ("orgId", "ODS_ORG_ID"),
        ("adminEmail", "ODS_ADMIN_EMAIL"),
        ("lang", "ODS_LANG"),
        ("brandColor", "ODS_BRAND_COLOR"),
        ("logoPath", "ODS_LOGO_PATH"),
        ("legalNotice", "ODS_LEGAL_NOTICE"),
    ):
        if overrides.get(clave):
            entorno[variable] = str(overrides[clave])
    try:
        completed = subprocess.run(
            [sys.executable, str(ROOT / "app" / "tools" / "render_ui_runtime_config.py"),
             "--env-file", str(ROOT / ".env")],
            capture_output=True, text=True, timeout=60, cwd=str(ROOT), env=entorno,
        )
        if completed.returncode != 0:
            print(f"[setup] WARN no se pudo renderizar la interfaz: {(completed.stderr or '').strip()}")
    except Exception as exc:  # noqa: BLE001
        print(f"[setup] WARN no se pudo renderizar la interfaz: {exc}")


def normalize_user_identity(value):
    return str(value or "").strip().lower()


def decode_bearer_payload(handler):
    global _keycloak_jwks_client
    auth_header = str(handler.headers.get("Authorization", "") or "").strip()
    if not auth_header.startswith("Bearer "):
        raise PermissionError("missing_bearer_token")
    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        raise PermissionError("missing_bearer_token")
    try:
        if _keycloak_jwks_client is None:
            _keycloak_jwks_client = jwt.PyJWKClient(f"{KEYCLOAK_URL}/realms/{REALM_NAME}/protocol/openid-connect/certs")
        signing_key = _keycloak_jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "PS256", "ES256"],
            options={"verify_aud": False},
        )
        if str(payload.get("iss", "")).strip() not in keycloak_expected_issuers():
            raise PermissionError("unexpected_token_issuer")
        return payload
    except Exception as exc:
        raise PermissionError("invalid_bearer_token") from exc


def keycloak_user_group_names(subject, claim=None):
    """Los grupos de quien firma la petición, del token o de Keycloak.

    Se prefiere la reclamación del token cuando el cliente la emite -- está
    firmada y es de este mismo acceso -- y si no, se le pregunta a Keycloak por
    el `sub`. Lo que no se hace es deducirlos de una tabla de este fichero.
    """
    names = {
        str(entry or "").strip().lstrip("/")
        for entry in (claim or [])
        if str(entry or "").strip()
    }
    if names:
        return names
    subject = str(subject or "").strip()
    if not subject:
        return set()
    try:
        token = get_admin_token()
        groups = kc_request(
            "GET", f"/admin/realms/{REALM_NAME}/users/{subject}/groups", token=token
        ) or []
    except Exception:
        return set()
    return {str(group.get("name", "") or "").strip() for group in groups}


def assert_request_reviewer(handler):
    """Quién puede aprobar un alta: quien está en un grupo que lo permite.

    Se comparaba con una sola dirección literal, REQUESTS_MASTER_EMAIL, así que
    REQUEST_REVIEWER_GROUPS -- declarado justo arriba para decir exactamente
    esto -- no lo leía nadie, y ningún operador de `dataspace-admins` podía
    aprobar nada aunque su consola le ofreciera el botón. Es el mismo patrón
    que dejaba la resolución de consolas atada a una tabla de tres nombres
    mientras Keycloak ya sabía la respuesta.
    """
    payload = decode_bearer_payload(handler)
    email = normalize_user_identity(payload.get("email") or payload.get("preferred_username") or payload.get("sub") or "")
    subject = str(payload.get("sub", "") or "").strip()
    if email == REQUESTS_MASTER_EMAIL:
        return {"email": email or REQUESTS_MASTER_EMAIL, "subject": subject}
    if keycloak_user_group_names(subject, payload.get("groups")) & REQUEST_REVIEWER_GROUPS:
        return {"email": email, "subject": subject}
    raise PermissionError("forbidden_request_reviewer")


def send_email_message(to_email, subject, text_body):
    if not REQUESTS_SMTP_HOST or not REQUESTS_SMTP_USER or not REQUESTS_SMTP_PASSWORD:
        raise RuntimeError("smtp_not_configured")
    msg = EmailMessage()
    msg["From"] = REQUESTS_FROM_EMAIL
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(text_body)
    with smtplib.SMTP(REQUESTS_SMTP_HOST, REQUESTS_SMTP_PORT, timeout=30) as smtp:
        if REQUESTS_SMTP_STARTTLS:
            smtp.starttls()
        smtp.login(REQUESTS_SMTP_USER, REQUESTS_SMTP_PASSWORD)
        smtp.send_message(msg)


def request_email_body(doc, site_label, lang="es"):
    role_label = mode_label(doc.get("requestedRoleMode", "consumer"), lang)
    connector_id = str(doc.get("connectorId", "") or "").strip()
    if str(lang or "es").lower().startswith("en"):
        return (
            f"New connector registration request in {site_label}\n\n"
            f"Request ID: {doc['requestId']}\n"
            f"Connector ID: {connector_id}\n"
            f"Email: {doc['email']}\n"
            f"First name: {doc.get('firstName', '')}\n"
            f"Last name: {doc.get('lastName', '')}\n"
            f"Requested profile: {role_label}\n"
            f"Created at: {doc['createdAt']}\n\n"
            "Review it and approve or deny it from the console."
        )
    return (
        f"Nueva solicitud de registro de conector en {site_label}\n\n"
        f"Solicitud: {doc['requestId']}\n"
        f"Conector: {connector_id}\n"
        f"Correo: {doc['email']}\n"
        f"Nombre: {doc.get('firstName', '')}\n"
        f"Apellidos: {doc.get('lastName', '')}\n"
        f"Perfil solicitado: {role_label}\n"
        f"Creada: {doc['createdAt']}\n\n"
        "Revísala y apruébala o deniégala desde la consola."
    )


def decision_email_body(doc, approved: bool, lang="es"):
    role_label = mode_label(doc.get("approvedRoleMode") or doc.get("requestedRoleMode", "consumer"), lang)
    if str(lang or "es").lower().startswith("en"):
        if approved:
            if doc.get("passwordApplied", True):
                credential_line = (
                    "You can now sign in with the email address and password used in your request."
                )
            else:
                # La dirección ya tenía cuenta en el realm, así que
                # ensure_keycloak_user dejó su contraseña intacta a propósito.
                # Mandarle usar la que escribió en la solicitud es mandarle a
                # un acceso que la rechaza: es lo que pasó el 23 de agosto.
                credential_line = (
                    "This address already had an account, so its existing password was kept "
                    "and the one in your request was not applied. Sign in with the password "
                    "you already had, or use Forgot Password on the login page to reset it."
                )
            return (
                f"Your connector request has been approved.\n\n"
                f"Connector ID: {doc.get('connectorId', '')}\n"
                f"Assigned profile: {role_label}\n"
                f"{credential_line}"
            )
        return (
            f"Your connector request has been denied.\n\n"
            f"Request ID: {doc.get('requestId', '')}\n"
            f"Reason: {doc.get('reviewReason', '') or 'Not specified'}"
        )
    if approved:
        if doc.get("passwordApplied", True):
            linea_credencial = (
                "Ya puedes iniciar sesión con el correo y la contraseña indicados en la solicitud."
            )
        else:
            linea_credencial = (
                "Este correo ya tenía cuenta, así que se ha conservado su contraseña anterior "
                "y no se ha aplicado la indicada en la solicitud. Inicia sesión con la contraseña "
                "que ya tenías, o usa «¿Olvidaste tu contraseña?» en la pantalla de acceso."
            )
        return (
            f"Tu solicitud de conector ha sido aprobada.\n\n"
            f"Conector: {doc.get('connectorId', '')}\n"
            f"Perfil asignado: {role_label}\n"
            f"{linea_credencial}"
        )
    return (
        f"Tu solicitud de conector ha sido denegada.\n\n"
        f"Solicitud: {doc.get('requestId', '')}\n"
        f"Motivo: {doc.get('reviewReason', '') or 'No especificado'}"
    )


def render_connector_page(connector_id, email, lang, role_mode="consumer"):
    is_en = lang == "en"
    home_href = "./home-en.html" if is_en else "./home.html"
    login_href = "./login-en.html" if is_en else "./login.html"
    lang_active_es = "" if is_en else " is-active"
    lang_active_en = " is-active" if is_en else ""

    title = f"{connector_id} Console"
    heading = f"Connector {connector_id}" if is_en else f"Conector {connector_id}"
    endpoint_label = "Endpoint (proxy):" if is_en else "Endpoint (proxy):"
    nav_home = "Home" if is_en else "Inicio"
    nav_login = "Login"
    lang_aria = "Language selector" if is_en else "Selector de idioma"

    allowed_roles = requested_roles_for_mode(role_mode)
    can_consume = "consumer" in allowed_roles
    can_publish = "provider" in allowed_roles
    role_badge = mode_label(role_mode, "en" if is_en else "es")

    # Contra quien se puede negociar: este nodo y los que se hayan dado de
    # alta en la consola. Antes eran tres identificadores escritos aqui, que
    # es lo que hacia que la consola de una instalacion cualquiera ofreciera
    # negociar contra conectores que no existen en ella.
    negotiation_targets = [
        {
            "id": node["id"],
            "label": node["label"],
            # La direccion que el NAVEGADOR alcanza, no la de la red interna.
            # El nodo propio se opera por el paso de /api/connector; un nodo
            # remoto se mira por su catalogo publico.
            "baseUrl": CONNECTOR_PROXY_PREFIX if node.get("local") else node["baseUrl"],
            "local": node.get("local", False),
            "status": node.get("status", ""),
        }
        for node in list_known_nodes()
    ]

    nodes_intro = (
        "Add the address of another node and its offer joins this catalogue, "
        "next to your own. This is what makes several organisations that "
        "installed this separately into one data space."
        if is_en else
        "Añade la dirección de otro nodo y su oferta pasa a formar parte de "
        "este catálogo, junto a la tuya. Es lo que convierte a varias "
        "organizaciones que han instalado esto por separado en un espacio de "
        "datos de verdad."
    )
    nodes_note = (
        "A node that stops answering is marked unavailable and keeps its last "
        "known offer, with the date of its last successful sync. A node being "
        "down never empties the view of the others."
        if is_en else
        "Un nodo que deja de contestar se marca como no disponible y conserva "
        "su última oferta conocida, con la fecha de su última sincronización "
        "correcta. Un nodo caído nunca vacía la vista de los demás."
    )

    return f"""<!doctype html>
<html lang=\"{'en' if is_en else 'es'}\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{title}</title>
  <link rel=\"stylesheet\" href=\"./styles.css\" />
  <script src=\"./runtime-config.js?v=20260419-9\"></script>
  <script src=\"./site-config.js?v=20260419-9\"></script>
  <script>
    window.DATASPACE_SITE.applyPage({{
      path: \"./{console_page_name('en' if is_en else 'es')}\",
      title: {json.dumps(title)},
      robots: \"noindex, follow\"
    }});
  </script>
</head>
<body>
<div class=\"container\">
  <nav class=\"top-nav\">
    <a class=\"pill-link\" href=\"{home_href}\">{nav_home}</a>
    <a class=\"pill-link\" href=\"{login_href}\">{nav_login}</a>
    <span class=\"lang-switch\" aria-label=\"{lang_aria}\">
      <a class=\"pill-link{lang_active_es}\" href=\"./{CONSOLE_PAGES['es']}\">ES</a>
      <a class=\"pill-link{lang_active_en}\" href=\"./{CONSOLE_PAGES['en']}\">EN</a>
    </span>
  </nav>

  <h1>{heading}</h1>
  <p class=\"muted\">{endpoint_label} <strong>{CONNECTOR_PROXY_PREFIX}</strong></p>
  <p class=\"muted\">Owner: <strong>{email}</strong></p>
  <p class=\"muted\">{'Assigned profile' if is_en else 'Perfil asignado'}: <strong>{role_badge}</strong></p>

  <div id=\"operationTabNav\" class=\"tab-nav\" role=\"tablist\" aria-label=\"{'Connector operation areas' if is_en else 'Áreas operativas del conector'}\">
    <button id=\"operationProviderBtn\" class=\"tab-btn is-active\" type=\"button\" role=\"tab\" aria-controls=\"operationProviderPanel\" aria-selected=\"true\">{'Data provider' if is_en else 'Proveedor de datos'}</button>
    <button id=\"operationConsumerBtn\" class=\"tab-btn\" type=\"button\" role=\"tab\" aria-controls=\"operationConsumerPanel\" aria-selected=\"false\">{'Consumption and catalog' if is_en else 'Consumo y catálogo'}</button>
    <button id=\"operationNodesBtn\" class=\"tab-btn\" type=\"button\" role=\"tab\" aria-controls=\"operationNodesPanel\" aria-selected=\"false\">{'Known nodes' if is_en else 'Nodos conocidos'}</button>
  </div>

  <div id=\"operationNodesPanel\" class=\"tab-panel\" role=\"tabpanel\" aria-labelledby=\"operationNodesBtn\" hidden>
    <div class=\"card\">
      <h2>{'Known nodes' if is_en else 'Nodos conocidos'}</h2>
      <p class=\"muted\">{nodes_intro}</p>

      <div class=\"form-row\">
        <div><label for=\"nodeLabel\">{'Name' if is_en else 'Nombre'}</label><input id=\"nodeLabel\" placeholder=\"{'Neighbouring consortium' if is_en else 'Consorcio vecino'}\" /></div>
        <div><label for=\"nodeBaseUrl\">{'Address' if is_en else 'Dirección'}</label><input id=\"nodeBaseUrl\" placeholder=\"https://nodo.ejemplo.org\" /></div>
      </div>
      <button id=\"addNodeBtn\" class=\"btn\" type=\"button\">{'Add node' if is_en else 'Añadir nodo'}</button>
      <button id=\"syncNodesBtn\" class=\"secondary\" type=\"button\">{'Refresh now' if is_en else 'Actualizar ahora'}</button>
      <div id=\"nodesStatus\" class=\"status muted\"></div>
      <table id=\"nodesTable\"></table>
      <p class=\"muted\">{nodes_note}</p>
    </div>
  </div>

  <div id=\"operationProviderPanel\" class=\"tab-panel is-active\" role=\"tabpanel\" aria-labelledby=\"operationProviderBtn\">

  <div class=\"card\">
    <h2>{'Guided flow' if is_en else 'Flujo guiado'}</h2>
    <div class=\"asset-stage-row flow-stage-row\">
      <div id=\"flowStageDocument\" class=\"asset-stage is-active\"><span>1</span><strong>{'Document analyzed' if is_en else 'Documento analizado'}</strong></div>
      <div id=\"flowStageMetadata\" class=\"asset-stage\"><span>2</span><strong>{'Metadata proposed' if is_en else 'Metadatos propuestos'}</strong></div>
      <div id=\"flowStagePolicy\" class=\"asset-stage\"><span>3</span><strong>{'Policy proposed' if is_en else 'Política propuesta'}</strong></div>
      <div id=\"flowStageReady\" class=\"asset-stage\"><span>4</span><strong>{'Ready to create' if is_en else 'Listo para crear'}</strong></div>
    </div>
    <p id=\"flowStageStatus\" class=\"muted\">{'Start by pasting a valid resource URL to trigger the full chained analysis.' if is_en else 'Empieza pegando una URL válida del recurso para encadenar el análisis completo.'}</p>
  </div>

  <div class=\"card\">
    <h2>{'Create data asset' if is_en else 'Crear data asset'}</h2>
    <div class=\"asset-stage-row\">
      <div id=\"assetStageUrl\" class=\"asset-stage is-active\"><span>1</span><strong>{'Paste URL' if is_en else 'Pegar URL'}</strong></div>
      <div id=\"assetStageReview\" class=\"asset-stage\"><span>2</span><strong>{'Analyze and review' if is_en else 'Analizar y revisar'}</strong></div>
      <div id=\"assetStageCreate\" class=\"asset-stage\"><span>3</span><strong>{'Create asset' if is_en else 'Crear asset'}</strong></div>
    </div>
    <p class=\"muted\">{'Recommended formats for analysis: ' if is_en else 'Formatos recomendados para análisis: '}`.pdf`, `.txt`, `.md`, `.csv`, `.xls`, `.xlsx`, `.doc`, `.docx`.</p>
    <form id=\"assetForm\" class=\"grid\">
      <div style=\"grid-column: 1 / -1;\"><label>{'Resource base URL' if is_en else 'Base URL del recurso'}</label><input id=\"assetBaseUrl\" required placeholder=\"https://your-domain/objects/assets/document.pdf\"/></div>
      <div style=\"grid-column: 1 / -1; display:flex; gap:0.75rem; align-items:center; flex-wrap:wrap;\">
        <button id=\"analyzeAssetDocumentBtn\" type=\"button\" class=\"secondary\">{'Analyze URL' if is_en else 'Analizar URL'}</button>
        <span class=\"muted\">{'Analyze the URL first, review the proposed fields and create the asset when everything looks right.' if is_en else 'Primero analiza la URL, revisa los campos y crea el asset cuando todo esté correcto.'}</span>
        <span id=\"assetDocumentStatus\" class=\"muted\">{'Waiting for a URL to analyze.' if is_en else 'Esperando una URL para analizar.'}</span>
      </div>
      <div><label>{'Name' if is_en else 'Nombre'}</label><input id=\"assetName\" value=\"\"/></div>
      <div><label>{'Description' if is_en else 'Descripción'}</label><input id=\"assetDescription\" value=\"\"/></div>
      <div><label>{'DCAT-AP identifier' if is_en else 'Identificador DCAT-AP'}</label><input id=\"assetIdentifier\" data-site-identifier-prefix value=\"urn:ods:dataset:\"/></div>
      <div><label>{'DCAT-AP keywords (comma)' if is_en else 'Keywords DCAT-AP (coma)'}</label><input id=\"assetKeywords\" value=\"\"/></div>
      <div><label>{'DCAT-AP theme' if is_en else 'Tema DCAT-AP'}</label><input id=\"assetTheme\" value=\"\"/></div>
      <div><label>{'Language' if is_en else 'Idioma'}</label><input id=\"assetLanguage\" value=\"es\"/></div>
      <div><label>{'License' if is_en else 'Licencia'}</label><input id=\"assetLicense\" value=\"https://creativecommons.org/licenses/by-nc/4.0/\"/></div>
      <div><label>{'Publisher' if is_en else 'Publisher'}</label><input id=\"assetPublisher\" data-site-publisher value=\"My Open Dataspace\"/></div>
      <div><label>{'Spatial coverage' if is_en else 'Cobertura espacial'}</label><input id=\"assetSpatial\" value=\"ES\"/></div>
      <div><label>{'Period start (ISO8601)' if is_en else 'Periodo (inicio ISO8601)'}</label><input id=\"assetTemporalStart\" value=\"2026-01-01\"/></div>
      <div><label>{'Period end (ISO8601)' if is_en else 'Periodo (fin ISO8601)'}</label><input id=\"assetTemporalEnd\" value=\"2026-12-31\"/></div>
      <div><label>{'Distribution format' if is_en else 'Formato distribución'}</label><input id=\"assetFormat\" value=\"application/pdf\"/></div>
      <div><label>{'Media type' if is_en else 'Media type'}</label><input id=\"assetMediaType\" value=\"application/pdf\"/></div>
      <div><label>{'Access rights' if is_en else 'Derechos de acceso'}</label><input id=\"assetAccessRights\" value=\"public\"/></div>
      <div><button type=\"submit\">{'Create asset' if is_en else 'Crear Asset'}</button></div>
    </form>
    <div id=\"assetAuditPanel\" class=\"card\" style=\"margin-top:1rem;\">
      <h3>{'Document audit report' if is_en else 'Informe de auditoría del documento'}</h3>
      <p id=\"assetAuditSummary\" class=\"muted\">{'Paste a valid URL to automatically generate the analysis and metadata suggestions.' if is_en else 'Pega una URL válida para generar automáticamente el análisis y las sugerencias de metadatos.'}</p>
      <div id=\"assetAuditMeta\" class=\"muted\"></div>
      <div id=\"assetAuditReasoning\"></div>
      <div id=\"assetAuditRecommendations\"></div>
    </div>
  </div>

  <div class=\"card\">
    <h2>{'Create policy' if is_en else 'Crear Política'}</h2>
    <div class=\"asset-stage-row\">
      <div id=\"policyStageUrl\" class=\"asset-stage is-active\"><span>1</span><strong>{'URL or resource' if is_en else 'URL o recurso'}</strong></div>
      <div id=\"policyStageReview\" class=\"asset-stage\"><span>2</span><strong>{'Analyze and review' if is_en else 'Analizar y revisar'}</strong></div>
      <div id=\"policyStageCreate\" class=\"asset-stage\"><span>3</span><strong>{'Create policy' if is_en else 'Crear política'}</strong></div>
    </div>
    <form id=\"policyForm\" class=\"grid\">
      <div style=\"grid-column: 1 / -1;\"><label>{'Data asset reused URL' if is_en else 'URL reutilizada del data asset'}</label><input id=\"policySourceUrl\" required readonly placeholder=\"{'Filled automatically from the data asset' if is_en else 'Se rellena automáticamente desde el data asset'}\"/></div>
      <div style=\"grid-column: 1 / -1; display:flex; gap:0.75rem; align-items:center; flex-wrap:wrap;\">
        <button id=\"analyzePolicyBtn\" type=\"button\" class=\"secondary\">{'Regenerate policy' if is_en else 'Regenerar política'}</button>
        <span class=\"muted\">{'The policy reuses the document analysis and is automatically proposed from the same resource.' if is_en else 'La política reutiliza el análisis del documento y se propone automáticamente a partir del mismo recurso.'}</span>
        <span id=\"policyDocumentStatus\" class=\"muted\">{'The policy will be generated from the data asset analysis.' if is_en else 'La política se generará a partir del análisis del data asset.'}</span>
      </div>
      <div><label>{'Name' if is_en else 'Nombre'}</label><input id=\"policyName\" required value=\"{'Policy C1' if is_en else 'Política C1'}\"/></div>
      <div><label>{'License URL' if is_en else 'URL de Licencia'}</label><input id=\"policyLicenseUrl\" value=\"\"/></div>
      <div><label>{'Purpose' if is_en else 'Propósito de uso'}</label><input id=\"policyPurpose\" value=\"\"/></div>
      <div><label>{'Geographic scope' if is_en else 'Ámbito geográfico'}</label><input id=\"policyGeographicScope\" value=\"EU\"/></div>
      <div><label>{'Retention (days, 0 = n/a)' if is_en else 'Retención (días, 0 = no aplica)'}</label><input id=\"policyRetentionDays\" type=\"number\" min=\"0\" value=\"0\"/></div>
      <div><label>{'Internal use' if is_en else 'Uso interno'}</label><input id=\"policyInternalUse\" value=\"allowed-with-traceability\"/></div>
      <div><label>{'AI usage' if is_en else 'Uso para IA'}</label><input id=\"policyAiUsage\" value=\"review-required\"/></div>
      <div><label>{'Redistribution / forwarding' if is_en else 'Redistribución / reenvío'}</label><input id=\"policyRedistributionMode\" value=\"contract-only\"/></div>
      <div><label>{'Onward transfer' if is_en else 'Reenvío a terceros'}</label><input id=\"policyOnwardTransfer\" value=\"contract-only\"/></div>
      <div><label>{'Commercial use' if is_en else 'Uso comercial'}</label><input id=\"policyCommercialUse\" value=\"review-required\"/></div>
      <div><label>{'Anonymization required' if is_en else 'Anonimización requerida'}</label><input id=\"policyAnonymization\" value=\"not-required\"/></div>
      <div><label>{'Attribution mode' if is_en else 'Modo de atribución'}</label><input id=\"policyAttributionMode\" value=\"source-link-and-publisher\"/></div>
      <div><label>{'Notice of changes' if is_en else 'Notificación de cambios'}</label><input id=\"policyNoticeOfChanges\" value=\"required-for-derived-material\"/></div>
      <div><label>{'Rate limit compliance' if is_en else 'Cumplimiento de rate limit'}</label><input id=\"policyRateLimitCompliance\" value=\"not-applicable\"/></div>
      <div><label>{'Refresh expectation' if is_en else 'Expectativa de actualización'}</label><input id=\"policyDataRefreshExpectation\" value=\"snapshot-or-versioned-release\"/></div>
      <div style=\"grid-column: 1 / -1;\"><label>{'Permitted actions (comma)' if is_en else 'Acciones permitidas (coma)'}</label><input id=\"policyPermittedActions\" value=\"use, read, reproduce\"/></div>
      <div style=\"grid-column: 1 / -1;\"><label>{'Prohibited actions (comma)' if is_en else 'Prohibiciones (coma)'}</label><input id=\"policyProhibitedActions\" value=\"sell\"/></div>
      <div style=\"grid-column: 1 / -1;\"><label>{'Duties / mandatory clauses (comma)' if is_en else 'Deberes / cláusulas obligatorias (coma)'}</label><input id=\"policyDuties\" value=\"attribution, keep-source-link\"/></div>
      <div style=\"grid-column: 1 / -1;\"><label>{'Security measures' if is_en else 'Medidas de seguridad'}</label><input id=\"policySecurityMeasures\" value=\"signed-traceability, access-logging\"/></div>
      <div style=\"grid-column: 1 / -1;\"><label>{'Regulatory summary / clauses' if is_en else 'Resumen normativo / cláusulas'}</label><textarea id=\"policyClausesSummary\" rows=\"4\"></textarea></div>
      <div><button type=\"submit\">{'Create policy' if is_en else 'Crear Política'}</button></div>
    </form>
    <div id=\"policyAuditPanel\" class=\"card\" style=\"margin-top:1rem;\">
      <h3>{'Suggested policy report' if is_en else 'Informe de política sugerida'}</h3>
      <p id=\"policyAuditSummary\" class=\"muted\">{'Analyze a URL to propose a policy fitted to the content of the resource.' if is_en else 'Analiza una URL para proponer una política ajustada al contenido del recurso.'}</p>
      <div id=\"policyAuditMeta\" class=\"muted\"></div>
      <div id=\"policyAuditReasoning\"></div>
      <div id=\"policyAuditRecommendations\"></div>
    </div>
  </div>

  <div class=\"card\">
    <h2>{'Create contract' if is_en else 'Crear Contrato'}</h2>
    <form id=\"contractForm\" class=\"grid\">
      <div><label>{'Data asset' if is_en else 'Data asset'}</label><select id=\"contractAssetIdSelect\" required></select></div>
      <div><label>{'Policy' if is_en else 'Política'}</label><select id=\"contractPolicyIdSelect\" required></select></div>
      <div><button type=\"submit\">{'Create contract' if is_en else 'Crear Contrato'}</button></div>
    </form>
  </div>

  <div class=\"card\">
    <h2>{'View my assets' if is_en else 'Ver mis activos'}</h2>
    <button id=\"reloadBtn\">{'Reload' if is_en else 'Recargar'}</button>
    <h3>Assets</h3><table id=\"assetsTable\"></table>
    <h3>{'Policies' if is_en else 'Políticas'}</h3><table id=\"policiesTable\"></table>
    <h3>{'Contracts' if is_en else 'Contratos'}</h3><table id=\"contractsTable\"></table>
    <h3>{'Negotiations' if is_en else 'Negociaciones'}</h3><table id=\"negotiationsTable\"></table>
  </div>

  </div>

  <div id=\"operationConsumerPanel\" class=\"tab-panel\" role=\"tabpanel\" aria-labelledby=\"operationConsumerBtn\" hidden>

  <div class=\"card\">
    <h2>{'Federated catalog' if is_en else 'Catálogo federado'}</h2>
    <p class=\"muted\">{'From this connector you can accept policies and download resources after a completed negotiation.' if is_en else 'Desde este conector puedes aceptar políticas y descargar recursos con negociación completada.'}</p>
    <button id=\"reloadFederatedBtn\">{'Reload federated' if is_en else 'Recargar federado'}</button>
    <table id=\"federatedTable\"></table>
  </div>

  </div>

  <div id=\"status\" class=\"status\"></div>
</div>

<script>
  window.CONNECTOR_CONFIG = {{
    id: {json.dumps(connector_id)},
    lang: {json.dumps('en' if is_en else 'es')},
    label: {json.dumps(heading)},
    baseUrl: {json.dumps(f'/api/{connector_id}')},
    features: {{
      create: {str(can_publish).lower()},
      myAssets: {str(can_publish).lower()},
      federated: {str(can_consume).lower()},
      allowNegotiate: {str(can_consume).lower()},
      allowDownload: {str(can_consume).lower()}
    }},
    auth: {{
      enabled: true,
      url: window.DATASPACE_SITE.config.authBaseUrl,
      realm: \"dataspace\",
      clientId: \"dataspace-ui\",
      refreshSeconds: 30
    }},
    fusekiQueryUrl: \"/fuseki/dataspace/query\",
    fusekiUser: \"admin\",
    fusekiPassword: \"\",
    negotiationTargets: {json.dumps(negotiation_targets, ensure_ascii=False)}
  }};
</script>
<script src=\"./app.js?v=20260731-2\"></script>
</body>
</html>
"""


# La consola vive en una sola direccion, no en una por conector.
#
# El origen escribia <connector-id>.html, que con tres conectores daba tres
# consolas y tres direcciones que memorizar. Aqui hay un conector, asi que
# hay una consola: /console.html y /console-en.html. Que el identificador del
# conector sea configurable es justamente lo que hace que no pueda estar en
# la direccion.
CONSOLE_PAGES = {"es": "console.html", "en": "console-en.html"}


def console_page_name(lang):
    return CONSOLE_PAGES["en" if str(lang or "").lower().startswith("en") else "es"]


def write_connector_pages(connector_id, email, role_mode="consumer"):
    UI_DIR.mkdir(parents=True, exist_ok=True)
    for lang, page in CONSOLE_PAGES.items():
        (UI_DIR / page).write_text(
            render_connector_page(connector_id, email, lang, role_mode=role_mode),
            encoding="utf-8",
        )


def refresh_existing_connector_pages():
    """Reescribe la consola en cada arranque.

    La consola se genera, no se sirve estatica: lleva dentro la lista de nodos
    conocidos, el identificador del conector y el perfil de quien la usa, y
    los tres cambian sin que nadie toque un fichero. Las console*.html que
    viajan en el repositorio son lo que se ve antes del primer arranque; a
    partir de ahi las escribe esto.

    El conector de este nodo es proveedor y consumidor a la vez: es el unico
    que hay y tiene que poder publicar y consumir.
    """
    try:
        write_connector_pages(CONNECTOR_ID, REQUESTS_MASTER_EMAIL, role_mode="both")
    except Exception as exc:  # noqa: BLE001 - se dice, no se traga
        print(f"[onboarding-api] WARN no se pudo generar la consola: {exc}")


def find_connector_id_for_user(user_value):
    user = normalize_user_identity(user_value)
    if not user:
        return None

    candidate_emails = set()
    candidate_usernames = set()
    if EMAIL_RE.match(user):
        candidate_emails.add(user)
        candidate_usernames.add(user.split("@")[0])
    else:
        candidate_usernames.add(user)

    if CONNECTORS_DIR.exists():
        for path in sorted(CONNECTORS_DIR.glob("connector-*.json")):
            try:
                doc = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            connector_id = str(doc.get("connector_id", "")).strip()
            email = normalize_user_identity(doc.get("email", ""))
            if not connector_id or not email:
                continue
            username = email.split("@")[0]
            if email in candidate_emails or username in candidate_usernames:
                return connector_id, email

    for connector_id, doc in STATIC_CONNECTOR_DIRECTORY.items():
        email = normalize_user_identity(doc.get("email", ""))
        if not connector_id or not email:
            continue
        # A connector has one owner and may have further sign-ins - today the
        # release probe. The owner is what this returns either way.
        known = [email] + [
            normalize_user_identity(extra) for extra in doc.get("additionalEmails", [])
        ]
        usernames = [value.split("@")[0] for value in known if value]
        if any(value in candidate_emails for value in known if value) or any(
            value in candidate_usernames for value in usernames
        ):
            return connector_id, email

    return None


def get_user_profile_by_email(email, token=None):
    safe_email = normalize_user_identity(email)
    if not safe_email:
        return {"name": "", "lastName": "", "email": ""}

    own_token = token
    if not own_token:
        own_token = get_admin_token()

    users = kc_request(
        "GET",
        f"/admin/realms/{REALM_NAME}/users",
        token=own_token,
        query={"email": safe_email, "exact": "true"},
    )
    if not users:
        return {"name": "", "lastName": "", "email": safe_email}

    user = users[0]
    return {
        "name": str(user.get("firstName", "") or "").strip(),
        "lastName": str(user.get("lastName", "") or "").strip(),
        "email": str(user.get("email", safe_email) or safe_email).strip().lower(),
    }


def list_registered_connectors():
    """El directorio de conectores, leído del registro de participantes.

    Leer CONNECTORS_DIR daría sólo los conectores generados por un alta, y
    entonces esta función contestaría una lista vacía en un nodo cuyo conector
    viene declarado, mientras su consola, sus rutas y sus grupos existen y
    funcionan. El conector del nodo se siembra en el registro
    (seed_predefined_participants) y esta función se limita a leerlo, de modo
    que el catálogo, la registración y el panel contestan por la misma lista.
    """
    items = []
    token = None
    for doc in list_participants():
        attributes = doc.get("attributes", {}) if isinstance(doc.get("attributes"), dict) else {}
        connector_id = str(attributes.get("connectorId", "") or "").strip()
        if not connector_id:
            continue
        email = normalize_user_identity(attributes.get("email", ""))
        roles = doc.get("roles", []) if isinstance(doc.get("roles"), list) else []

        profile = {"name": "", "lastName": "", "email": email}
        if email:
            try:
                if token is None:
                    token = get_admin_token()
                profile = get_user_profile_by_email(email, token=token)
            except Exception:
                profile = {"name": "", "lastName": "", "email": email}

        items.append(
            {
                "connectorId": connector_id,
                "name": profile.get("name", ""),
                "lastName": profile.get("lastName", ""),
                "email": profile.get("email", email),
                "status": str(doc.get("status", "") or ""),
                "type": connector_type_for_mode(role_mode_for_roles(roles)),
                "roles": roles,
                "createdAt": connector_created_at(connector_id),
                "keycloakClientId": str(attributes.get("keycloakClientId", "") or "").strip(),
                "source": "predefined" if connector_id in STATIC_CONNECTOR_IDS else "registered",
            }
        )

    return sorted(items, key=lambda item: item.get("connectorId", ""))


def role_mode_for_roles(roles):
    roles = roles if isinstance(roles, list) else []
    if "provider" in roles and "consumer" in roles:
        return "both"
    if "provider" in roles:
        return "provider"
    return "consumer"


def connector_created_at(connector_id):
    path = CONNECTORS_DIR / f"{connector_id}.json"
    if not path.exists():
        return 0
    try:
        return int(json.loads(path.read_text(encoding="utf-8")).get("created_at", 0) or 0)
    except Exception:
        return 0








def connector_is_complete(connector_id):
    """El conector existe de verdad: registro en disco y entrada de participante.

    Es la comprobación que separa un alta terminada de un alta que sólo dejó
    rastro en Keycloak. El registro de participantes es el que consulta
    gobernanza para federar, así que un conector que no está ahí no existe
    para el espacio de datos por mucho grupo que tenga.
    """
    connector_id = str(connector_id or "").strip()
    if not connector_id:
        return False
    if not (CONNECTORS_DIR / f"{connector_id}.json").exists():
        return False
    return bool(load_participant(participant_id_for_connector(connector_id)))


def rollback_connector_artifacts(connector_id):
    """Deshace lo que create_connector_for_owner alcanzó a escribir.

    No toca el usuario de Keycloak -- puede ser una cuenta anterior a esta
    solicitud -- ni ningún grupo, porque en la ruta nueva el grupo no se ha
    creado todavía cuando esto corre.
    """
    connector_id = str(connector_id or "").strip()
    if not connector_id:
        return
    for path in (
        CONNECTORS_DIR / f"{connector_id}.json",
        WALLET_DIR / f"{connector_id}.json",
        # Por participant_path, no componiendo el nombre: el fichero se llama
        # sha1("participant:<dominio>:<conector>"), no como el identificador.
        # Componerlo a mano apunta a un fichero que no existe, y entonces la
        # entrada de participante sobrevive a cada retirada y a cada rollback,
        # dejando conectores registrados que ya no tienen ni grupo ni consola.
        participant_path(participant_id_for_connector(connector_id)),
        # La consola no se borra: es una sola y la comparte todo el nodo.
    ):
        try:
            path.unlink()
        except FileNotFoundError:
            continue
        except Exception:
            continue


def create_connector_for_owner(connector_id, email, role_mode="consumer"):
    """Crea el conector entero o no deja nada. Devuelve su client_id.

    Todo lo que un alta tiene que producir está aquí y en este orden, para que
    el fallo de cualquier pieza se pueda deshacer sin dejar medio conector
    suelto. Quien llama sólo concede grupos cuando esto ha devuelto.
    """
    email = normalize_user_identity(email)
    role_mode = normalize_role_mode(role_mode)
    try:
        client_id, client_secret = ensure_keycloak_client(connector_id, role_mode=role_mode)
        write_connector_registration(connector_id, email, client_id, role_mode=role_mode)
        write_wallet(connector_id, email, client_id, client_secret, role_mode=role_mode)
        write_connector_pages(connector_id, email, role_mode=role_mode)
        participant = upsert_participant_for_connector(
            connector_id, email, client_id, role_mode=role_mode, status="active"
        )
        if not connector_is_complete(connector_id):
            raise RuntimeError(f"connector_incomplete:{connector_id}")
    except Exception:
        rollback_connector_artifacts(connector_id)
        raise

    return client_id


def ensure_connector_artifacts_for_existing_user(email):
    safe_email = normalize_user_identity(email)
    if not EMAIL_RE.match(safe_email):
        return None

    connector_id = make_connector_id(safe_email)
    if connector_already_exists(connector_id):
        write_connector_pages(connector_id, safe_email)
        return connector_id

    token = get_admin_token()
    users = kc_request(
        "GET",
        f"/admin/realms/{REALM_NAME}/users",
        token=token,
        query={"email": safe_email, "exact": "true"},
    )
    if not users:
        return None

    user_id = users[0]["id"]
    # Mismo orden que en la aprobación: el conector primero, el acceso después.
    create_connector_for_owner(connector_id, safe_email, role_mode="consumer")
    ensure_consumer_access(user_id)
    return connector_id


CONNECTOR_GROUP_PATTERN = re.compile(r"^/?(connector-[A-Za-z0-9-]+)-users$")


def connector_id_from_groups(groups):
    """The connector a signed-in user belongs to, from their own token.

    Resolution used to come from a directory written in this file and a table
    of legacy redirects, so a new participant landed on /home.html until
    somebody added them here. Their membership of connector-N-users was already
    the fact that decided it, and Keycloak already knew it.

    A user in two connector groups is not resolved by guessing: the lowest name
    wins so that the same person lands in the same place on every request, and
    the ambiguity is left for the directory or a human to settle rather than
    depending on the order Keycloak happened to return.
    """
    candidates = set()
    for entry in groups or []:
        match = CONNECTOR_GROUP_PATTERN.match(str(entry or "").strip())
        if match:
            candidates.add(match.group(1))
    if not candidates:
        return ""
    return sorted(candidates)[0]


def keycloak_connector_groups():
    """Los grupos connector-*-users que existen hoy, con cuántos miembros tienen."""
    token = get_admin_token()
    groups = kc_request(
        "GET", f"/admin/realms/{REALM_NAME}/groups", token=token, query={"max": "1000"}
    ) or []
    found = {}
    for group in groups:
        name = str(group.get("name", "") or "").strip()
        match = CONNECTOR_GROUP_PATTERN.match(name)
        if not match:
            continue
        members = kc_request(
            "GET",
            f"/admin/realms/{REALM_NAME}/groups/{group.get('id')}/members",
            token=token,
            query={"max": "200"},
        ) or []
        owners = [
            normalize_user_identity(member.get("email") or member.get("username", ""))
            for member in members
        ]
        found[match.group(1)] = {
            "group": name,
            "groupId": str(group.get("id", "") or ""),
            "members": len(members),
            "owners": [owner for owner in owners if owner],
        }
    return found


def reconcile_connector_groups():
    """Un grupo sin conector detrás se completa; nunca se borra a ciegas.

    Ocho grupos `connector-*-users` nombraban un conector que no existía, y
    ninguno estaba vacío: cinco eran de personas reales, en organizaciones
    reales, y para ellas ese grupo era el único rastro de que se habían dado de
    alta. Borrarlo no es limpieza, es borrar la prueba. Lo que faltaba era el
    conector, así que es el conector lo que se crea.

    Sólo actúa cuando el grupo tiene exactamente un miembro y su dirección
    genera ese mismo identificador de conector: si no, se dice y se deja
    quieto. Retirar un grupo que sobra sigue siendo cosa de
    tools/remove_orphaned_connector_group.sh, que exige nombrar a quién cree
    uno que lo tiene y acertar.
    """
    groups = keycloak_connector_groups()
    registry = {
        str(item.get("connectorId", "") or "").strip()
        for item in list_registered_connectors()
    }
    completed, left = [], []
    for connector_id, entry in sorted(groups.items()):
        if connector_id in registry:
            continue
        owners = entry.get("owners", [])
        if len(owners) != 1:
            left.append(f"{connector_id}(miembros={entry.get('members', 0)})")
            continue
        if make_connector_id(owners[0]) != connector_id:
            # No se nombra la dirección: basta con decir que la que hay dentro
            # no genera este identificador, que es lo que impide actuar.
            left.append(f"{connector_id}(su miembro genera {make_connector_id(owners[0])})")
            continue
        try:
            create_connector_for_owner(connector_id, owners[0], role_mode="consumer")
            completed.append(connector_id)
        except Exception as exc:  # noqa: BLE001 - se dice cuál y por qué
            left.append(f"{connector_id}({type(exc).__name__}: {exc})")
    # Y al revés: una entrada de registro sin grupo es un participante que no
    # puede entrar en su propia consola. Si su cuenta sigue existiendo se le da
    # el acceso que le falta; si la cuenta ya no está, no hay participante que
    # sostener y la entrada se retira -- que no es borrar el rastro de nadie,
    # porque la persona ya no existe en el realm. Los predefinidos nunca se
    # retiran: no dependen de una cuenta.
    granted, dropped = [], []
    token = None
    for item in list_registered_connectors():
        connector_id = str(item.get("connectorId", "") or "").strip()
        if not connector_id or connector_id in groups:
            continue
        email = normalize_user_identity(item.get("email", ""))
        try:
            if token is None:
                token = get_admin_token()
            users = kc_request(
                "GET",
                f"/admin/realms/{REALM_NAME}/users",
                token=token,
                query={"username": email, "exact": "true"},
            ) if email else []
        except Exception as exc:  # noqa: BLE001 - no se decide a ciegas
            left.append(f"{connector_id}(no se pudo consultar su cuenta: {exc})")
            continue
        if users:
            try:
                ensure_request_access(
                    users[0]["id"], connector_id, role_mode_for_roles(item.get("roles", []))
                )
                granted.append(connector_id)
            except Exception as exc:  # noqa: BLE001
                left.append(f"{connector_id}(no se pudo dar el grupo: {exc})")
            continue
        if connector_id in STATIC_CONNECTOR_IDS:
            left.append(f"{connector_id}(predefinido sin grupo)")
            continue
        rollback_connector_artifacts(connector_id)
        dropped.append(connector_id)

    if completed:
        print(f"[onboarding-api] conectores completados desde su grupo: {', '.join(completed)}")
    if granted:
        print(f"[onboarding-api] grupos concedidos a participantes que no los tenían: {', '.join(granted)}")
    if dropped:
        print(f"[onboarding-api] entradas de registro retiradas por no tener cuenta detrás: {', '.join(dropped)}")
    if left:
        print(f"[onboarding-api] WARN grupos sin conector que no se pueden completar solos: {', '.join(left)}")
    return {"completed": completed, "granted": granted, "dropped": dropped, "left": left}


# En qué punto están las reparaciones de arranque, para que quien pregunte no
# tenga que adivinarlo. Lo lee /api/onboarding/health.
STARTUP_REPAIRS = {"status": "pending", "detail": ""}


def wait_for_keycloak(timeout_seconds=180):
    """Esperar a que el proveedor de identidad conteste antes de repararlo.

    Una composición levanta Keycloak y este servicio a la vez, y este arranca
    antes. Sin esta espera, las reparaciones que necesitan el realm -- la
    recuperación de contraseña y las dos mitades de la reconciliación de
    grupos -- fallan en cada arranque con "connection refused", se anotan como
    aviso y no vuelven a intentarse: los grupos huérfanos se quedan ahí sin
    que nada diga por qué.

    Devuelve True si contestó. No lanza: quien llama decide, y una identidad
    que no sube no puede impedir que este servicio sirva.
    """
    deadline = time.time() + max(1, int(timeout_seconds))
    attempt = 0
    while True:
        try:
            get_admin_token()
            if attempt:
                print(f"[onboarding-api] el proveedor de identidad contestó al intento {attempt + 1}")
            return True
        except Exception as exc:  # noqa: BLE001 - se reintenta, y se dice al final
            if time.time() >= deadline:
                print(f"[onboarding-api] WARN el proveedor de identidad no contestó en {timeout_seconds}s: {exc}")
                return False
            attempt += 1
            time.sleep(3)


def ensure_realm_password_recovery():
    """La recuperación que el correo ofrece tiene que existir y poder enviar.

    El correo de aprobación de una cuenta preexistente le dice a la persona que
    use «¿Olvidaste tu contraseña?». Si `resetPasswordAllowed` está en false, o
    si el realm no tiene servidor de correo, ese enlace no existe o el mensaje
    no sale de Keycloak: se le está ofreciendo a alguien una salida que no
    funciona.

    Va aquí, en el arranque del servicio, y no a mano en cada nodo. La
    configuración que vive fuera del árbol instalado es exactamente la que se
    pierde en la siguiente actualización.

    Idempotente y no fatal: si Keycloak no contesta, el servicio sirve igual y
    lo dice.
    """
    token = get_admin_token()
    realm = kc_request("GET", f"/admin/realms/{REALM_NAME}", token=token) or {}
    changes = {}

    if not realm.get("resetPasswordAllowed"):
        changes["resetPasswordAllowed"] = True

    current = realm.get("smtpServer") if isinstance(realm.get("smtpServer"), dict) else {}
    if REQUESTS_SMTP_HOST and REQUESTS_SMTP_PASSWORD:
        desired = {
            "host": REQUESTS_SMTP_HOST,
            "port": str(REQUESTS_SMTP_PORT),
            "from": REQUESTS_FROM_EMAIL,
            "fromDisplayName": dataspace_label(),
            "replyTo": REQUESTS_MASTER_EMAIL,
            "auth": "true",
            "user": REQUESTS_SMTP_USER,
            "password": REQUESTS_SMTP_PASSWORD,
            "starttls": "true" if REQUESTS_SMTP_STARTTLS else "false",
            "ssl": "false",
        }
        # La contraseña vuelve enmascarada de Keycloak, así que no se puede
        # comparar: se compara lo demás y se reescribe entera cuando algo
        # cambia o cuando no hay nada puesto.
        comparable = {key: value for key, value in desired.items() if key != "password"}
        if any(str(current.get(key, "")) != value for key, value in comparable.items()):
            changes["smtpServer"] = desired

    if not changes:
        return False
    # Representación parcial, no la entera de vuelta.
    #
    # Devolver el objeto completo que contestó el GET es lo que hacía esta
    # llamada, y Keycloak la rechazaba: el 24 de agosto de 2026 los dos
    # participantes siguieron con `resetPasswordAllowed` en false después de
    # tres arranques, y el recorrido del alta lo cazó al pedir el formulario de
    # recuperación y recibir un 400. updateRealm sólo aplica los campos que
    # vienen, así que mandar los que cambian es suficiente y no arrastra los
    # derivados que la representación completa trae.
    payload = dict(changes)
    payload["realm"] = str(realm.get("realm", "") or REALM_NAME)
    try:
        kc_request("PUT", f"/admin/realms/{REALM_NAME}", token=token, payload=payload)
    except urllib_error.HTTPError as exc:  # el cuerpo dice qué campo no le gusta
        detail = ""
        try:
            detail = exc.read().decode("utf-8", "replace")[:300]
        except Exception:  # noqa: BLE001
            detail = ""
        raise RuntimeError(f"realm_update_failed:{exc.code}:{detail}") from exc
    print(f"[onboarding-api] realm actualizado: {sorted(changes)}")
    return True


def run_startup_repairs():
    """Reparar el realm y los grupos, sin hacer esperar a quien pregunta.

    Corría antes de abrir el puerto, y con la espera al proveedor de identidad
    eso llegó a ser medio minuto largo: el 24 de agosto de 2026 el recorrido
    del login del propio despliegue pidió /api/onboarding/connector-page
    mientras esto esperaba, recibió cuerpo vacío y tumbó la release en los dos
    participantes. El servicio abre primero y repara después, y dice en qué
    punto está para que una comprobación pueda esperar a que termine en vez de
    medir a medias.
    """
    if not wait_for_keycloak():
        STARTUP_REPAIRS["status"] = "unavailable"
        STARTUP_REPAIRS["detail"] = "el proveedor de identidad no contestó"
        print("[onboarding-api] WARN sin identidad no se reparan ni el realm ni los grupos")
        return
    problems = []
    try:
        ensure_realm_password_recovery()
    except Exception as exc:  # noqa: BLE001 - reported, not swallowed
        problems.append(f"realm: {exc}")
        print(f"[onboarding-api] WARN no se pudo asegurar la recuperación de contraseña: {exc}")
    try:
        reconcile_connector_groups()
    except Exception as exc:  # noqa: BLE001 - reported, not swallowed
        problems.append(f"grupos: {exc}")
        print(f"[onboarding-api] WARN no se pudieron reconciliar los grupos: {exc}")
    STARTUP_REPAIRS["status"] = "done" if not problems else "partial"
    STARTUP_REPAIRS["detail"] = "; ".join(problems)
    print(f"[onboarding-api] reparaciones de arranque: {STARTUP_REPAIRS['status']}")


def connector_consistency_report():
    """Las dos fuentes que este servicio gobierna, puestas una al lado de otra.

    El registro manda. Un grupo sin entrada de registro es un alta que dejó
    acceso sin conector -- el caso C -- y una entrada de registro sin grupo es
    un participante que no puede entrar. La tercera fuente, el catálogo, la
    mide audit/consistencia-conectores.sh contra el federador en marcha,
    porque quien puede decir qué ha federado de verdad es el federador.
    """
    registry = {}
    for item in list_registered_connectors():
        connector_id = str(item.get("connectorId", "") or "").strip()
        if connector_id:
            registry[connector_id] = item

    groups = keycloak_connector_groups()
    registry_ids = set(registry)
    group_ids = set(groups)
    orphan_groups = sorted(group_ids - registry_ids)
    missing_groups = sorted(registry_ids - group_ids)
    return {
        "generatedAt": utc_now(),
        "registry": sorted(registry_ids),
        "keycloakGroups": sorted(group_ids),
        "orphanGroups": [
            {
                "connectorId": cid,
                "group": groups[cid]["group"],
                "members": groups[cid]["members"],
            }
            for cid in orphan_groups
        ],
        "missingGroups": missing_groups,
        "consistent": not orphan_groups and not missing_groups,
    }


def resolve_connector_redirect(user_value, lang, groups=None):
    found = find_connector_id_for_user(user_value)
    from_groups = connector_id_from_groups(groups)
    if from_groups:
        # El token manda. Va firmado, es actual y no necesita entrada en
        # ninguna tabla de aqui: quien esta en el grupo del conector aterriza
        # en su consola sin que haya que desplegar nada.
        found = (from_groups, user_value)
    is_en = str(lang or "es").lower().startswith("en")
    if not found:
        return "/home-en.html" if is_en else "/home.html"

    connector_id, email = found
    page_name = console_page_name(lang)
    if not (UI_DIR / page_name).exists():
        write_connector_pages(connector_id, email)
    return f"/{page_name}"


def existing_connector_message(lang):
    if str(lang or "es").lower().startswith("en"):
        return (
            "Your connector already existed. "
            "The access credentials have been updated. "
            "Go to the Login page and sign in using the same email address and the password you just entered."
        )
    return (
        "Tu conector ya existia. "
        "Las credenciales de acceso se han actualizado. "
        "Ve a la pantalla de Login e inicia sesion con el mismo correo y la contrasena que acabas de indicar."
    )


def created_connector_message(lang):
    if str(lang or "es").lower().startswith("en"):
        return (
            "Your connector has been created successfully. "
            "Go to the Login page and sign in using the same email address and the password you set during registration."
        )
    return (
        "Tu conector se ha creado correctamente. "
        "Dirigete a la pantalla de Login e inicia sesion con el mismo correo y la contrasena que definiste en el registro."
    )


def connector_already_exists(connector_id):
    return (
        (CONNECTORS_DIR / f"{connector_id}.json").exists()
        or (WALLET_DIR / f"{connector_id}.json").exists()
    )


def find_request_by_id(request_id):
    for item in load_requests():
        if str(item.get("requestId", "")).strip() == str(request_id or "").strip():
            return item
    return None


def list_connector_requests(status_filter="all"):
    items = load_requests()
    if status_filter and status_filter != "all":
        expected = str(status_filter).strip().lower()
        items = [item for item in items if str(item.get("status", "")).strip().lower() == expected]
    return sorted(items, key=lambda item: (str(item.get("createdAt", "")), str(item.get("requestId", ""))), reverse=True)


def create_connector_request(email, password, first_name, last_name, requested_role_mode, lang):
    safe_email = normalize_user_identity(email)
    connector_id = make_connector_id(safe_email)
    if connector_already_exists(connector_id):
        raise ValueError("connector_exists")

    items = load_requests()
    for item in items:
        if normalize_user_identity(item.get("email", "")) != safe_email:
            continue
        status = str(item.get("status", "")).strip().lower()
        if status in {"pending", "approved"}:
            raise ValueError("request_already_exists")

    doc = {
        "requestId": f"req-{hashlib.sha1(f'{safe_email}:{time.time()}'.encode('utf-8')).hexdigest()[:12]}",
        "connectorId": connector_id,
        "email": safe_email,
        "firstName": str(first_name or "").strip(),
        "lastName": str(last_name or "").strip(),
        "requestedRoleMode": normalize_role_mode(requested_role_mode),
        "requestedRoles": requested_roles_for_mode(requested_role_mode),
        "lang": "en" if str(lang or "es").lower().startswith("en") else "es",
        "status": "pending",
        "createdAt": utc_now(),
        "encryptedPassword": encrypt_pending_password(password),
    }
    items.append(doc)
    save_requests(items)
    return doc


def review_connector_request(request_id, approved, reviewer_email, review_reason=""):
    items = load_requests()
    target = None
    for item in items:
        if str(item.get("requestId", "")).strip() == str(request_id or "").strip():
            target = item
            break
    if not target:
        raise ValueError("request_not_found")
    if str(target.get("status", "")).strip().lower() != "pending":
        raise ValueError("request_already_reviewed")

    review_reason = str(review_reason or "").strip()
    target["reviewedAt"] = utc_now()
    target["reviewedBy"] = normalize_user_identity(reviewer_email)
    target["reviewReason"] = review_reason

    if not approved:
        target["status"] = "denied"
        target["encryptedPassword"] = ""
        save_requests(items)
        return target

    connector_id = str(target.get("connectorId", "")).strip()
    role_mode = normalize_role_mode(target.get("requestedRoleMode", "consumer"))
    password = decrypt_pending_password(str(target.get("encryptedPassword", "")).strip())
    email = normalize_user_identity(target.get("email", ""))
    first_name = str(target.get("firstName", "")).strip()
    last_name = str(target.get("lastName", "")).strip()

    user_id, user_created = ensure_keycloak_user(
        email, password, first_name=first_name, last_name=last_name
    )

    # El conector primero, el grupo después.
    #
    # Al revés -- que es como estaba -- una aprobación que no llegaba a crear
    # conector dejaba igualmente `connector-<id>-users` en Keycloak, y la
    # persona entraba a una consola de un conector que no existe en ninguna
    # fuente. Ocho grupos así se midieron el 22 de agosto de 2026 en los dos
    # participantes. Si algo de aquí abajo falla se deshace lo escrito y la
    # solicitud queda `failed` con el motivo: nunca un grupo huérfano.
    try:
        client_id = create_connector_for_owner(connector_id, email, role_mode=role_mode)
    except Exception as exc:  # noqa: BLE001 - se registra en la solicitud
        target["status"] = "failed"
        target["failureReason"] = str(exc)
        target["failedAt"] = utc_now()
        target["encryptedPassword"] = ""
        save_requests(items)
        raise

    ensure_request_access(user_id, connector_id, role_mode)

    target["status"] = "approved"
    target["approvedRoleMode"] = role_mode
    target["approvedRoles"] = requested_roles_for_mode(role_mode)
    target["approvedAt"] = utc_now()
    target["keycloakClientId"] = client_id
    # Lo que hay que contarle a quien solicitó, y la razón de anotarlo en vez
    # de suponerlo: si la cuenta ya estaba, su contraseña es la que ya tenía y
    # no la que traía esta solicitud.
    target["passwordApplied"] = bool(user_created)
    target["encryptedPassword"] = ""
    save_requests(items)
    return target


def create_captcha():
    a = random.randint(2, 9)
    b = random.randint(2, 9)
    challenge_id = "".join(random.choices(string.ascii_lowercase + string.digits, k=16))
    with captcha_lock:
        captcha_store[challenge_id] = {"answer": str(a + b), "exp": time.time() + 600}
    return challenge_id, f"{a} + {b} = ?"


def consume_captcha(challenge_id, answer):
    now = time.time()
    with captcha_lock:
        data = captcha_store.pop(challenge_id, None)
    if not data:
        return False
    if data["exp"] < now:
        return False
    return str(answer).strip() == data["answer"]


def slugify_fragment(value):
    normalized = re.sub(r"[^a-zA-Z0-9._-]+", "-", str(value or "").strip().lower())
    normalized = normalized.strip("-._")
    return normalized or "document"


def default_public_base_url():
    return os.getenv("ODS_PUBLIC_URL", "").strip().rstrip("/")


def dataspace_label():
    """El nombre de la organizacion, con lo que el asistente haya decidido."""
    return (
        load_site_overrides().get("orgName")
        or os.getenv("ODS_ORG_NAME", "").strip()
        or "My Open Dataspace"
    )


def keycloak_expected_issuers():
    issuers = {f"{KEYCLOAK_URL.rstrip('/')}/realms/{REALM_NAME}"}
    # El emisor que el navegador ve es el publico, y el que este servicio usa
    # por dentro es el de la red de la composicion: los dos son validos y hay
    # que aceptar ambos, o la consola inicia sesion y el servicio le rechaza
    # su propio token.
    for base in (
        os.getenv("ODS_AUTH_URL", "").strip().rstrip("/"),
        f"{os.getenv('ODS_PUBLIC_URL', '').strip().rstrip('/')}/auth" if os.getenv("ODS_PUBLIC_URL", "").strip() else "",
    ):
        if base:
            issuers.add(f"{base}/realms/{REALM_NAME}")
            try:
                parsed = urllib.parse.urlparse(base)
                host = parsed.hostname or ""
                if host:
                    issuers.add(f"http://{host}:8080/realms/{REALM_NAME}")
            except Exception:
                pass
    return sorted(issuers)
























SAFE_FILE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def safe_file_name(file_name):
    """Un nombre de fichero que no puede salirse de la carpeta de ficheros."""
    base = Path(str(file_name or "")).name
    cleaned = SAFE_FILE_NAME_RE.sub("-", base).strip("-._") or "documento"
    return cleaned[:120]


def build_object_key(connector_id, file_name):
    connector = SAFE_FILE_NAME_RE.sub("-", str(connector_id or "connector")).strip("-") or "connector"
    stamp = hashlib.sha256(f"{connector}:{file_name}:{time.time_ns()}".encode("utf-8")).hexdigest()[:12]
    return f"{connector}/{stamp}-{safe_file_name(file_name)}"


def object_path(object_key):
    """Resuelve una clave a una ruta dentro de FILES_DIR, o falla.

    Se comprueba contra la carpeta resuelta, no concatenando cadenas: es lo
    que impide que una clave con `..` lea cualquier fichero del contenedor.
    """
    root = FILES_DIR.resolve()
    candidate = (root / str(object_key or "").lstrip("/")).resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError("object_key_fuera_de_rango")
    return candidate


def store_document(connector_id, file_name, content_type, document_bytes):
    if not document_bytes:
        raise RuntimeError("documento_vacio")
    object_key = build_object_key(connector_id, file_name)
    destination = object_path(object_key)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(document_bytes)
    destination.with_suffix(destination.suffix + ".meta.json").write_text(
        json.dumps(
            {
                "fileName": safe_file_name(file_name),
                "contentType": content_type or "application/octet-stream",
                "size": len(document_bytes),
                "connectorId": connector_id,
                "storedAt": utc_now(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return {
        "objectKey": object_key,
        "objectUrl": f"{default_public_base_url().rstrip('/')}/api/onboarding/assets/{object_key}",
        "size": len(document_bytes),
    }


def load_vocabulary_manifest():
    manifest_path = PROFILES_DIR / "manifest.json"
    if not manifest_path.exists():
        return {"vocabularies": []}
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return {"vocabularies": []}
    return payload if isinstance(payload, dict) else {"vocabularies": []}


def find_vocabulary(vocabulary_id):
    manifest = load_vocabulary_manifest()
    for item in manifest.get("vocabularies", []) if isinstance(manifest.get("vocabularies"), list) else []:
        if str(item.get("id", "")).strip() == str(vocabulary_id or "").strip():
            return item
    return None


# One profile object for the service, built from the shapes the release ships.
SHAPES_RELATIVE_PATH = "profiles/dcat-ap/1.0.0/shapes.ttl"
CATALOGUE_PROFILE = CatalogueProfile(
    ROOT / SHAPES_RELATIVE_PATH,
    shapes_id=SHAPES_RELATIVE_PATH,
    descriptor={
        "id": "ods-dcat-ap-1.0.0",
        **METADATA_PROFILE_DESCRIPTIONS["ods-dcat-ap-1.0.0"],
    },
)


def shape_expectations():
    """What the shapes require. Kept as a name of its own because the profile
    endpoint and the drift guard both ask for it."""
    return CATALOGUE_PROFILE.expectations()


def shacl_conformance(metadata):
    return CATALOGUE_PROFILE.conformance(metadata)


def validate_catalog_metadata(metadata):
    """Delegated to the packaged profile. The response is unchanged: callers,
    the interface and the bundle validation all read the same shape."""
    return CATALOGUE_PROFILE.validate(metadata)


def validate_policy_metadata(policy):
    policy = policy if isinstance(policy, dict) else {}
    inner = policy.get("policy", policy) if isinstance(policy.get("policy", policy), dict) else {}
    missing = []
    for key in ("permission", "prohibition", "duty"):
        if not isinstance(inner.get(key), list) or not inner.get(key):
            missing.append(key)
    if not str(inner.get("purpose", "")).strip():
        missing.append("purpose")
    return {
        "ok": not missing,
        "profile": "ods-odrl-1.0.0",
        "checkedAt": utc_now(),
        "missing": missing,
        "warnings": [],
        "vocabularies": ["odrl"],
    }


def validate_metadata_policy_contract_bundle(payload):
    payload = payload if isinstance(payload, dict) else {}
    metadata = payload.get("metadata", {}) if isinstance(payload.get("metadata"), dict) else {}
    policy = payload.get("policy", {}) if isinstance(payload.get("policy"), dict) else {}
    contract = payload.get("contract", {}) if isinstance(payload.get("contract"), dict) else {}
    metadata_result = validate_catalog_metadata(metadata)
    policy_result = validate_policy_metadata(policy) if policy else {"ok": True, "missing": [], "warnings": []}
    consistency_errors = []
    consistency_warnings = []

    metadata_policy_id = str(metadata.get("policyId", "") or metadata.get("ods:policyId", "") or "").strip()
    contract_policy_id = str(contract.get("policyId", "") or "").strip()
    if metadata_policy_id and contract_policy_id and metadata_policy_id != contract_policy_id:
        consistency_errors.append("metadata_policy_id_does_not_match_contract")

    metadata_asset_id = str(metadata.get("assetId", "") or metadata.get("dct:identifier", "") or metadata.get("identifier", "") or "").strip()
    contract_asset_id = str(contract.get("assetId", "") or "").strip()
    if metadata_asset_id and contract_asset_id and metadata_asset_id != contract_asset_id:
        consistency_warnings.append("metadata_identifier_differs_from_contract_asset_id")

    access_rights = access_rights_from_metadata(metadata)
    if access_rights in {"contractual-dashboard", "controlled-governed-reuse", "restricted"} and not contract:
        consistency_errors.append("contract_required_for_controlled_access")

    delivery_mode = str(metadata_value(metadata, "ods:deliveryMode") or "").strip()
    if delivery_mode == "download" and access_rights == "public":
        consistency_warnings.append("public_download_should_still_emit_consumption_evidence")

    if contract:
        status = str(contract.get("status", "") or "").strip()
        if status and status not in {"draft", "review", "active", "completed", "suspended", "revoked", "expired", "denied"}:
            consistency_errors.append("invalid_contract_status")

    score = min(
        metadata_result.get("score", 0),
        100 if policy_result.get("ok", True) else 60,
        100 if not consistency_errors else 50,
    )
    return {
        "ok": metadata_result.get("ok") and policy_result.get("ok") and not consistency_errors,
        "profile": "ods-metadata-policy-contract-bundle-1.0.0",
        "checkedAt": utc_now(),
        "score": score,
        "metadata": metadata_result,
        "policy": policy_result,
        "consistency": {
            "ok": not consistency_errors,
            "errors": consistency_errors,
            "warnings": consistency_warnings,
        },
    }


def edc_asset_selector(asset_id):
    return [
        {
            "@type": "CriterionDto",
            "operandLeft": "https://w3id.org/edc/v0.0.1/ns/id",
            "leftOperand": "id",
            "operator": "=",
            "operandRight": asset_id,
            "rightOperand": asset_id,
        }
    ]


def edc_data_address_from_metadata(metadata, data_address=None):
    metadata = metadata if isinstance(metadata, dict) else {}
    data_address = data_address if isinstance(data_address, dict) else {}
    if data_address:
        return data_address
    object_url = str(metadata.get("objectUrl") or metadata.get("url") or metadata.get("downloadUrl") or "").strip()
    delivery_mode = str(metadata_value(metadata, "ods:deliveryMode") or "").strip()
    return {
        "type": "HttpData",
        "baseUrl": object_url or str(metadata.get("viewerUrl") or "").strip() or "http://localhost",
        "proxyPath": "true",
        "proxyQueryParams": "true",
    }


def edc_policy_from_policy(policy):
    policy = policy if isinstance(policy, dict) else {}
    inner = policy.get("policy", policy) if isinstance(policy.get("policy", policy), dict) else policy
    permissions = inner.get("permission", [])
    prohibitions = inner.get("prohibition", [])
    duties = inner.get("duty", inner.get("obligation", []))
    return {
        "@context": "http://www.w3.org/ns/odrl.jsonld",
        "@type": "Set",
        "permission": permissions if isinstance(permissions, list) else normalize_list(permissions),
        "prohibition": prohibitions if isinstance(prohibitions, list) else normalize_list(prohibitions),
        "obligation": duties if isinstance(duties, list) else normalize_list(duties),
        "purpose": str(inner.get("purpose", "") or "").strip(),
        "profile": str(inner.get("profile", "") or "").strip() or policy_profile_for_context({}, policy),
    }










class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.end_headers()

    def do_GET(self):
        parsed = parse.urlparse(self.path)
        if parsed.path == "/api/onboarding/health":
            return json_response(
                self,
                200,
                {
                    "ok": True,
                    "repairs": STARTUP_REPAIRS["status"],
                    "repairsDetail": STARTUP_REPAIRS["detail"],
                    # Que el nodo diga en que modo esta no es un detalle: un
                    # nodo sin autenticacion y uno con ella se ven igual desde
                    # fuera hasta que alguien intenta algo. Lo dice aqui para
                    # que se pueda comprobar sin adivinar.
                    "evaluationMode": EVALUATION_MODE,
                },
            )
        if parsed.path == "/api/v1/participants":
            return json_response(self, 200, {"ok": True, "items": list_participants()})
        if parsed.path == "/api/v1/connectors/consistency":
            try:
                report = connector_consistency_report()
            except Exception as exc:  # noqa: BLE001 - se contesta el motivo
                return json_response(self, 502, {"ok": False, "error": str(exc)})
            return json_response(self, 200, dict(report, ok=True))
        if parsed.path == "/api/v1/role-profiles":
            params = parse.parse_qs(parsed.query)
            connector_id = str((params.get("connectorId") or ["{connectorId}"])[0]).strip() or "{connectorId}"
            return json_response(
                self,
                200,
                {
                    "ok": True,
                    "source": "roles del participante",
                    "items": list_role_profiles(connector_id),
                },
            )
        if parsed.path == "/api/v1/identity-attributes":
            params = parse.parse_qs(parsed.query)
            assignable_only = str((params.get("assignable") or [""])[0]).strip().lower() in {"1", "true", "yes"}
            return json_response(
                self,
                200,
                {
                    "ok": True,
                    "source": "atributos de identidad del participante",
                    "items": list_identity_attributes(assignable_only=assignable_only),
                },
            )
        if parsed.path.startswith("/api/v1/identity-attributes/"):
            attribute_id = parse.unquote(parsed.path[len("/api/v1/identity-attributes/"):]).strip("/")
            item = identity_attribute_doc(attribute_id)
            if not item and identity_attribute_path(attribute_id).exists():
                try:
                    item = json.loads(identity_attribute_path(attribute_id).read_text(encoding="utf-8"))
                except Exception:
                    item = None
            if not item:
                return json_response(self, 404, {"error": "identity_attribute_not_found"})
            return json_response(self, 200, {"ok": True, "item": item})
        if parsed.path.startswith("/api/v1/role-profiles/"):
            mode = parse.unquote(parsed.path[len("/api/v1/role-profiles/"):]).strip("/")
            if mode not in ROLE_PROFILE_DESCRIPTIONS:
                return json_response(self, 404, {"error": "role_profile_not_found"})
            params = parse.parse_qs(parsed.query)
            connector_id = str((params.get("connectorId") or ["{connectorId}"])[0]).strip() or "{connectorId}"
            return json_response(
                self,
                200,
                {
                    "ok": True,
                    "source": "roles del participante",
                    "item": role_profile_doc(mode, connector_id),
                },
            )
        if parsed.path == "/api/v1/policy-profiles":
            return json_response(
                self,
                200,
                {
                    "ok": True,
                    "source": "perfil de politica ODRL",
                    "items": list_policy_profiles(),
                },
            )
        if parsed.path.startswith("/api/v1/policy-profiles/"):
            profile_id = parse.unquote(parsed.path[len("/api/v1/policy-profiles/"):]).strip("/")
            if profile_id not in POLICY_PROFILE_DESCRIPTIONS:
                return json_response(self, 404, {"error": "policy_profile_not_found"})
            return json_response(
                self,
                200,
                {
                    "ok": True,
                    "source": "perfil de politica ODRL",
                    "item": policy_profile_doc(profile_id),
                },
            )
        if parsed.path == "/api/v1/contracts":
            params = parse.parse_qs(parsed.query)
            return json_response(
                self,
                200,
                {
                    "ok": True,
                    "items": list_contracts(
                        status_filter=str((params.get("status") or ["all"])[0]).strip() or "all",
                        participant_id=str((params.get("participantId") or [""])[0]).strip(),
                        asset_id=str((params.get("assetId") or [""])[0]).strip(),
                        policy_id=str((params.get("policyId") or [""])[0]).strip(),
                        limit=str((params.get("limit") or ["100"])[0]).strip(),
                    ),
                },
            )
        if parsed.path.startswith("/api/v1/contracts/"):
            suffix = parse.unquote(parsed.path[len("/api/v1/contracts/"):]).strip("/")
            if suffix.endswith("/history"):
                contract_id = suffix[: -len("/history")].strip("/")
                contract = load_contract(contract_id)
                if not contract:
                    return json_response(self, 404, {"error": "contract_not_found"})
                return json_response(self, 200, {"ok": True, "contractId": contract_id, "items": contract.get("history", [])})
            contract = load_contract(suffix)
            if not contract:
                return json_response(self, 404, {"error": "contract_not_found"})
            return json_response(self, 200, {"ok": True, "item": contract})
        if parsed.path.startswith("/api/v1/participants/"):
            suffix = parse.unquote(parsed.path[len("/api/v1/participants/"):]).strip("/")
            if suffix.endswith("/history"):
                participant_id = suffix[: -len("/history")].strip("/")
                participant = load_participant(participant_id)
                if not participant:
                    return json_response(self, 404, {"error": "participant_not_found"})
                return json_response(self, 200, {"ok": True, "participantId": participant_id, "items": participant.get("history", [])})
            participant = load_participant(suffix)
            if not participant:
                return json_response(self, 404, {"error": "participant_not_found"})
            return json_response(self, 200, {"ok": True, "item": participant})
        if parsed.path == "/api/v1/vocabularies":
            return json_response(self, 200, {"ok": True, **load_vocabulary_manifest()})
        if parsed.path == "/api/v1/metadata/profiles":
            return json_response(
                self,
                200,
                {
                    "ok": True,
                    "source": "perfil de metadatos DCAT-AP",
                    "items": list_metadata_profiles(),
                },
            )
        if parsed.path.startswith("/api/v1/metadata/profiles/"):
            profile_id = parse.unquote(parsed.path[len("/api/v1/metadata/profiles/"):]).strip("/")
            if profile_id not in METADATA_PROFILE_DESCRIPTIONS:
                return json_response(self, 404, {"error": "metadata_profile_not_found"})
            return json_response(
                self,
                200,
                {
                    "ok": True,
                    "source": "perfil de metadatos DCAT-AP",
                    "item": metadata_profile_doc(profile_id),
                },
            )
        if parsed.path.startswith("/api/v1/vocabularies/"):
            vocabulary_id = parse.unquote(parsed.path[len("/api/v1/vocabularies/"):]).strip("/")
            if vocabulary_id.endswith("/download"):
                vocabulary_id = vocabulary_id[: -len("/download")].strip("/")
            vocabulary = find_vocabulary(vocabulary_id)
            if not vocabulary:
                return json_response(self, 404, {"error": "vocabulary_not_found"})
            return json_response(self, 200, {"ok": True, "item": vocabulary})
        if parsed.path.startswith("/api/onboarding/assets/"):
            # Sirve un fichero publicado. Es la direccion que el conector usa
            # como baseUrl del activo, de modo que la descarga sigue pasando
            # por la negociacion: quien llegue aqui sin contrato tiene el
            # fichero, pero para llegar aqui hace falta que el conector le
            # haya dado la direccion, y eso solo pasa con la transferencia.
            object_key = parse.unquote(parsed.path[len("/api/onboarding/assets/"):])
            try:
                target = object_path(object_key)
            except ValueError:
                return json_response(self, 400, {"error": "invalid_object_key"})
            if not target.is_file() or target.name.endswith(".meta.json"):
                return json_response(self, 404, {"error": "not_found"})
            meta_path = target.with_suffix(target.suffix + ".meta.json")
            content_type = "application/octet-stream"
            if meta_path.is_file():
                try:
                    content_type = json.loads(meta_path.read_text(encoding="utf-8")).get("contentType") or content_type
                except ValueError:
                    pass
            payload = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Content-Disposition", f'attachment; filename="{target.name}"')
            self.end_headers()
            self.wfile.write(payload)
            return None
        if parsed.path.startswith(CONNECTOR_PROXY_PREFIX + "/"):
            return proxy_to_connector(self, "GET", parsed.path + (f"?{parsed.query}" if parsed.query else ""))
        if parsed.path == "/api/v1/setup":
            if is_configured():
                # Ya configurado: el asistente deja de existir. Reconfigurar
                # exige una orden explícita en la línea de comandos.
                return json_response(self, 404, {"error": "not_found"})
            return json_response(self, 200, setup_state())

        if parsed.path == "/sparql":
            if not SPARQL_PUBLIC:
                # 404 y no 403: un punto que no esta abierto no tiene por que
                # anunciar que existe.
                return json_response(self, 404, {"error": "not_found"})
            query = parse.parse_qs(parsed.query or "").get("query", [""])[0]
            if not query.strip():
                return json_response(self, 400, {"error": "missing_query"})
            if not sparql_query_is_read_only(query):
                return json_response(self, 403, {"error": "read_only_endpoint"})
            try:
                payload, content_type = sparql_select(query)
            except Exception as exc:  # noqa: BLE001 - se dice, no se traga
                return json_response(self, 502, {"error": "sparql_failed", "detail": str(exc)[:200]})
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return None

        if parsed.path == "/api/v1/catalog":
            # Publica y de solo lectura: es la puerta por la que otro nodo
            # federa a este. Un fallo aqui no puede tumbar el portal, asi que
            # se contesta 503 y se dice, en vez de reventar.
            try:
                return json_response(self, 200, {"ok": True, **local_catalog()})
            except Exception as exc:  # noqa: BLE001 - se dice, no se traga
                return json_response(
                    self, 503,
                    {"ok": False, "error": "catalog_unavailable", "detail": str(exc)[:200]},
                )
        if parsed.path == "/api/v1/nodes":
            # Publica a proposito. Es la lista de quien forma este espacio de
            # datos; lo que exige identidad es anadir o quitar, no mirar.
            return json_response(self, 200, {"ok": True, "items": list_known_nodes()})
        if parsed.path == "/api/onboarding/captcha":
            cid, question = create_captcha()
            return json_response(self, 200, {"captchaId": cid, "question": question})
        if parsed.path == "/api/onboarding/requests":
            try:
                reviewer = assert_request_reviewer(self)
            except PermissionError as exc:
                return json_response(self, 403, {"error": str(exc)})
            params = parse.parse_qs(parsed.query)
            status_filter = str((params.get("status") or ["all"])[0]).strip().lower() or "all"
            items = list_connector_requests(status_filter=status_filter)
            redacted = []
            for item in items:
                clean = {key: value for key, value in item.items() if key != "encryptedPassword"}
                redacted.append(clean)
            return json_response(self, 200, {"ok": True, "reviewer": reviewer["email"], "items": redacted})
        if parsed.path == "/api/onboarding/connectors":
            connectors = list_registered_connectors()
            return json_response(self, 200, {"ok": True, "items": connectors})
        if parsed.path == "/api/onboarding/connector-page":
            params = parse.parse_qs(parsed.query)
            user = normalize_user_identity((params.get("user") or [""])[0])
            lang = str((params.get("lang") or ["es"])[0]).lower()
            if not user:
                return json_response(self, 400, {"error": "missing_user"})
            # The token is optional. Without one this answers exactly as it
            # did before, because the login page has to ask before it has one
            # and an anonymous caller is not owed an error for that.
            groups = []
            try:
                groups = decode_bearer_payload(self).get("groups", []) or []
            except PermissionError:
                pass
            redirect = resolve_connector_redirect(user, lang, groups)
            return json_response(self, 200, {"ok": True, "redirect": redirect})
        if parsed.path == "/api/audit/health":
            signing_ready = Path(AUDIT_PRIVATE_KEY_FILE).exists()
            connector_key_count = len(list(connector_key_dir().glob("connector-*-audit-signing-key.pem"))) if connector_key_dir().exists() else 0
            return json_response(
                self,
                200,
                {
                    "ok": True,
                    "signingReady": signing_ready,
                    "auditIssuer": AUDIT_ISSUER,
                    "connectorSigningKeys": connector_key_count,
                },
            )
        if parsed.path == "/api/v1/audit/evidence":
            # The same door as /api/v1/audit/traces below, which was shut on
            # 21 August with a comment warning that the hole was "the same
            # shape and one nginx location away". This is that location. The
            # summary needed a token and the ledger it summarises did not,
            # and the ledger is the one carrying subjects, resources, actors
            # and the hash chain over them.
            #
            # Nothing routes either of them publicly today. That is still
            # luck, and it is why this is shut before somebody adds the
            # route - which almost happened while chasing incidencia 5.
            try:
                decode_bearer_payload(self)
            except PermissionError as exc:
                return json_response(self, 401, {"error": str(exc)})
            params = parse.parse_qs(parsed.query)
            return json_response(
                self,
                200,
                {
                    "ok": True,
                    "items": list_evidence_records(
                        trace_id=str((params.get("traceId") or [""])[0]).strip(),
                        event_type=str((params.get("type") or [""])[0]).strip(),
                        participant_id=str((params.get("participantId") or [""])[0]).strip(),
                        event_id=str((params.get("eventId") or [""])[0]).strip(),
                        limit=str((params.get("limit") or ["100"])[0]).strip(),
                    ),
                },
            )
        if parsed.path == "/api/v1/audit/evidence/verify":
            # Verification returns the chain's state, which tells an
            # unauthenticated caller how many records there are and whether
            # the ledger has been tampered with. Same door.
            try:
                decode_bearer_payload(self)
            except PermissionError as exc:
                return json_response(self, 401, {"error": str(exc)})
            result = verify_evidence_ledger()
            return json_response(self, 200 if result.get("ok") else 409, result)
        if parsed.path == "/api/v1/audit/traces":
            # Signed in, any user of this data space. The sibling deployment
            # served this route to the open internet with real trace
            # identifiers, connectors and decisions on it until 21 August 2026.
            # Nothing routes it here today, which is luck rather than design:
            # the hole was the same shape and one nginx location away.
            try:
                decode_bearer_payload(self)
            except PermissionError as exc:
                return json_response(self, 401, {"error": str(exc)})
            return json_response(self, 200, {"ok": True, "items": evidence_trace_summary()})

        # Cualquier otra cosa es el portal o la consola.
        #
        # En el despliegue del que sale este codigo esto lo servia un nginx
        # aparte, y por eso este manejador contestaba 404 a todo lo que no
        # empezara por /api. Aqui no hay ese nginx: la composicion tiene seis
        # contenedores y `app` es el que sirve la interfaz.
        return self.serve_ui(parsed.path)

    def serve_ui(self, path):
        # Un nodo que todavía no ha pasado por el asistente manda cualquier
        # ruta a /setup. Todas menos las que el propio asistente necesita para
        # pintarse: sin esta excepción, la hoja de estilo también acabaría
        # redirigida y la página saldría en blanco.
        if not is_configured() and path not in ("/setup", "/setup.html", "/styles.css"):
            self.send_response(302)
            self.send_header("Location", "/setup")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return None
        if path == "/setup":
            if is_configured():
                return json_response(self, 404, {"error": "not_found"})
            path = "/setup.html"
        if path == "/setup.html" and is_configured():
            # A partir de la configuración, /setup devuelve 404. Que la página
            # siga en el árbol no puede significar que siga sirviéndose.
            return json_response(self, 404, {"error": "not_found"})
        if path in ("", "/"):
            path = "/index-en.html" if DEFAULT_LANG == "en" else "/index.html"
        candidate = (UI_DIR / parse.unquote(path).lstrip("/")).resolve()
        root = UI_DIR.resolve()
        # Comprobado contra la carpeta resuelta, no concatenando cadenas: es lo
        # que impide que /../../etc/passwd salga de la interfaz.
        if candidate != root and root not in candidate.parents:
            return json_response(self, 404, {"error": "not_found"})
        if candidate.is_dir():
            candidate = candidate / "index.html"
        if not candidate.is_file():
            return json_response(self, 404, {"error": "not_found"})

        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type in (
            "application/javascript",
            "application/json",
        ):
            content_type = f"{content_type}; charset=utf-8"
        payload = candidate.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        # La consola y la configuracion de marca se generan en el arranque y
        # cambian con cada despliegue; que un navegador se quede con la de
        # ayer es lo que hace que una organizacion vea la marca de la
        # instalacion anterior despues de actualizar.
        if candidate.suffix in (".html", ".js"):
            self.send_header("Cache-Control", "no-cache")
        else:
            self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        self.wfile.write(payload)
        return None

    def do_DELETE(self):
        parsed = parse.urlparse(self.path)
        if parsed.path.startswith("/api/v1/nodes/"):
            try:
                assert_request_reviewer(self)
            except PermissionError as exc:
                return json_response(self, 403, {"error": str(exc)})
            node_id = parse.unquote(parsed.path[len("/api/v1/nodes/"):]).strip().lower()
            if node_id == CONNECTOR_ID:
                # Retirar el nodo propio dejaria el catalogo consolidado sin
                # la oferta de este nodo, que es la unica que este nodo puede
                # garantizar.
                return json_response(self, 400, {"error": "cannot_remove_local_node"})
            if not remove_known_node(node_id):
                return json_response(self, 404, {"error": "not_found"})
            # Un grafo con nombre por nodo es lo que permite retirar uno sin
            # tocar el resto del almacen.
            drop_node_graph(node_id)
            audit_event_or_local({"type": "node.removed", "subject": node_id})
            return json_response(self, 200, {"ok": True, "id": node_id})
        return json_response(self, 404, {"error": "not_found"})

    def do_POST(self):
        if self.path == "/api/audit/events":
            try:
                raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                body = json.loads(raw.decode("utf-8"))
            except Exception:
                return json_response(self, 400, {"error": "invalid_json"})
            try:
                signed_event = sign_audit_event(body)
            except Exception as exc:
                # Only signing lands here now. It used to catch the forward
                # too, so a 400 from governance came back as a 502 saying the
                # signature had failed - a wrong code and a wrong cause, and
                # the list of missing fields discarded on the way.
                return json_response(self, 502, {"error": "audit_signing_failed", "message": str(exc)})
            try:
                status, upstream_body = forward_audit_event(signed_event)
            except Exception as exc:
                # Genuinely upstream: unreachable, timed out, or an answer that
                # was not HTTP at all. 502 is right here and nowhere else.
                return json_response(self, 502, {"error": "audit_forward_failed", "message": str(exc)})
            return json_response(self, status, upstream_body)

        try:
            raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            body = json.loads(raw.decode("utf-8"))
        except Exception:
            return json_response(self, 400, {"error": "invalid_json"})




        if self.path.startswith("/api/v1/participants/") and self.path.endswith("/status"):
            participant_id = parse.unquote(self.path[len("/api/v1/participants/"): -len("/status")]).strip("/")
            participant = load_participant(participant_id)
            if not participant:
                return json_response(self, 404, {"error": "participant_not_found"})
            status = str(body.get("status", "")).strip()
            if status not in {"active", "suspended", "revoked", "retired"}:
                return json_response(self, 400, {"error": "invalid_status"})
            participant["status"] = status
            saved = save_participant(participant, "participant.status.changed", {"status": status, "reason": str(body.get("reason", "")).strip()})
            return json_response(self, 200, {"ok": True, "item": saved})

        if self.path == "/api/v1/identity-attributes":
            try:
                item = upsert_identity_attribute(body)
            except ValueError as exc:
                return json_response(self, 400, {"error": str(exc)})
            return json_response(self, 201, {"ok": True, "item": item})

        if self.path == "/api/v1/participants/sync":
            try:
                participant = sync_participant_from_bootstrap(body)
            except ValueError as exc:
                error = str(exc)
                return json_response(self, 400, {"error": error})
            return json_response(self, 200, {"ok": True, "item": participant})

        if self.path.startswith("/api/v1/participants/") and (
            self.path.endswith("/identity-attributes/assign") or self.path.endswith("/identity-attributes/unassign")
        ):
            assign_suffix = "/identity-attributes/assign"
            unassign_suffix = "/identity-attributes/unassign"
            action = "assign" if self.path.endswith(assign_suffix) else "unassign"
            suffix_len = len(assign_suffix if action == "assign" else unassign_suffix)
            participant_id = parse.unquote(self.path[len("/api/v1/participants/"): -suffix_len]).strip("/")
            attribute_ids = body.get("identityAttributes", body.get("attributeIds", body.get("ids", [])))
            try:
                participant = assign_identity_attributes_to_participant(participant_id, attribute_ids, action=action)
            except ValueError as exc:
                error = str(exc)
                status = 404 if error == "participant_not_found" else 400
                return json_response(self, status, {"error": error})
            return json_response(self, 200, {"ok": True, "item": participant})

        if self.path == "/api/v1/vocabularies/validate":
            target = body.get("metadata", body)
            validation_type = str(body.get("type", "catalog")).strip().lower()
            result = validate_policy_metadata(target) if validation_type == "policy" else validate_catalog_metadata(target)
            return json_response(self, 200 if result.get("ok") else 400, result)

        if self.path == "/api/v1/metadata/validate":
            target = body.get("metadata", body)
            result = validate_catalog_metadata(target)
            return json_response(self, 200 if result.get("ok") else 400, result)

        if self.path == "/api/v1/metadata/validate-bundle":
            result = validate_metadata_policy_contract_bundle(body)
            return json_response(self, 200 if result.get("ok") else 400, result)


        if self.path == "/api/v1/policies/validate":
            result = validate_policy_metadata(body)
            return json_response(self, 200 if result.get("ok") else 400, result)

        if self.path == "/api/v1/policies/evaluate":
            result = evaluate_policy_decision(body)
            status = 200
            if result.get("decision") == "deny":
                status = 403
            elif result.get("decision") == "review":
                status = 202
            return json_response(self, status, result)

        if self.path == "/api/v1/contracts":
            try:
                contract = create_contract(body)
            except ValueError as exc:
                return json_response(self, 400, {"error": str(exc)})
            status = 201
            decision = (contract.get("policyDecision", {}) or {}).get("decision", "")
            if decision == "deny":
                status = 403
            elif decision == "review":
                status = 202
            return json_response(self, status, {"ok": decision != "deny", "item": contract})

        if self.path.startswith("/api/v1/contracts/") and self.path.endswith("/status"):
            contract_id = parse.unquote(self.path[len("/api/v1/contracts/"): -len("/status")]).strip("/")
            try:
                contract = change_contract_status(contract_id, body.get("status", ""), reason=str(body.get("reason", "")).strip())
            except ValueError as exc:
                error = str(exc)
                return json_response(self, 404 if error == "contract_not_found" else 400, {"error": error})
            return json_response(self, 200, {"ok": True, "item": contract})

        if self.path.startswith("/api/onboarding/requests/"):
            suffix = self.path[len("/api/onboarding/requests/"):]
            if suffix.endswith("/approve"):
                action = "approve"
                request_id = suffix[: -len("/approve")]
            elif suffix.endswith("/deny"):
                action = "deny"
                request_id = suffix[: -len("/deny")]
            else:
                return json_response(self, 404, {"error": "not_found"})
            request_id = str(request_id).strip().strip("/")
            if not request_id:
                return json_response(self, 400, {"error": "missing_request_id"})
            try:
                reviewer = assert_request_reviewer(self)
            except PermissionError as exc:
                return json_response(self, 403, {"error": str(exc)})
            try:
                doc = review_connector_request(
                    request_id,
                    approved=action == "approve",
                    reviewer_email=reviewer["email"],
                    review_reason=str(body.get("reason", "")).strip(),
                )
                email_lang = str(doc.get("lang", "")).strip() or "es"
            except ValueError as exc:
                return json_response(self, 400, {"error": str(exc)})
            except Exception as exc:
                return json_response(self, 502, {"error": "request_review_failed", "message": str(exc)})
            notification_error = ""
            try:
                send_email_message(
                    doc["email"],
                    ("Connector request approved" if email_lang == "en" else "Solicitud de conector aprobada")
                    if action == "approve"
                    else ("Connector request denied" if email_lang == "en" else "Solicitud de conector denegada"),
                    decision_email_body(doc, approved=action == "approve", lang=email_lang),
                )
            except Exception as exc:
                notification_error = str(exc)
            clean = {key: value for key, value in doc.items() if key != "encryptedPassword"}
            return json_response(self, 200, {"ok": True, "item": clean, "notificationError": notification_error})

        if self.path == "/api/v1/setup":
            if is_configured():
                return json_response(self, 409, {"error": "already_configured"})
            try:
                destino = apply_setup(body)
            except ValueError as exc:
                return json_response(self, 400, {"error": str(exc)})
            except Exception as exc:  # noqa: BLE001 - se dice, no se traga
                return json_response(self, 502, {"error": "setup_failed", "detail": str(exc)[:300]})
            return json_response(self, 200, {"ok": True, "redirect": f"/{destino}"})

        if self.path.startswith(CONNECTOR_PROXY_PREFIX + "/"):
            return proxy_to_connector(
                self, "POST", self.path,
                body=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            )

        if self.path == "/api/v1/nodes":
            try:
                assert_request_reviewer(self)
            except PermissionError as exc:
                return json_response(self, 403, {"error": str(exc)})
            try:
                entry = add_known_node(
                    body.get("label", ""),
                    body.get("baseUrl", ""),
                    node_id=body.get("id", ""),
                )
            except ValueError as exc:
                return json_response(self, 400, {"error": str(exc)})
            audit_event_or_local({
                "type": "node.added",
                "subject": entry["id"],
                "resource": entry["baseUrl"],
            })
            return json_response(self, 201, {"ok": True, "item": entry})

        if self.path == "/api/v1/nodes/sync":
            # El boton de «actualizar ahora» de la consola. No espera al
            # intervalo: si alguien acaba de anadir un nodo, quiere ver su
            # oferta ahora y no dentro de cinco minutos.
            try:
                assert_request_reviewer(self)
            except PermissionError as exc:
                return json_response(self, 403, {"error": str(exc)})
            result = run_federation_now()
            return json_response(self, 200, {"ok": True, **result})

        if self.path == "/api/onboarding/assets/upload":
            connector_id = str(body.get("connectorId", "")).strip() or CONNECTOR_ID
            file_name = str(body.get("fileName", "")).strip() or "document.pdf"
            content_type = str(body.get("contentType", "")).strip() or mimetypes.guess_type(file_name)[0] or "application/octet-stream"
            file_base64 = str(body.get("fileBase64", "")).strip()
            if not file_base64:
                return json_response(self, 400, {"error": "missing_file"})
            try:
                document_bytes = base64.b64decode(file_base64, validate=True)
            except Exception:
                return json_response(self, 400, {"error": "invalid_file_base64"})
            try:
                uploaded = store_document(connector_id, file_name, content_type, document_bytes)
            except Exception as exc:
                return json_response(self, 502, {"error": "upload_failed", "message": str(exc)})
            return json_response(
                self,
                200,
                {
                    "ok": True,
                    "fileName": file_name,
                    "contentType": content_type,
                    **uploaded,
                },
            )



        if self.path != "/api/onboarding/register":
            return json_response(self, 404, {"error": "not_found"})

        email = str(body.get("email", "")).strip().lower()
        first_name = str(body.get("firstName", "")).strip()
        last_name = str(body.get("lastName", "")).strip()
        password = str(body.get("password", ""))
        captcha_id = str(body.get("captchaId", "")).strip()
        captcha_answer = str(body.get("captchaAnswer", "")).strip()
        lang = str(body.get("lang", "es")).lower()
        requested_role_mode = normalize_role_mode(body.get("requestedRoleMode", "consumer"))

        if not EMAIL_RE.match(email):
            return json_response(self, 400, {"error": "invalid_email"})
        if not PASSWORD_RE.match(password):
            return json_response(
                self,
                400,
                {
                    "error": "invalid_password",
                    "message": "La contraseña debe tener mínimo 9 caracteres, una mayúscula, un número y un carácter especial.",
                },
            )
        if not consume_captcha(captcha_id, captcha_answer):
            return json_response(self, 400, {"error": "invalid_captcha"})

        try:
            request_doc = create_connector_request(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                requested_role_mode=requested_role_mode,
                lang=lang,
            )
        except ValueError as exc:
            error_name = str(exc)
            status_code = 409 if error_name in {"connector_exists", "request_already_exists"} else 400
            return json_response(self, status_code, {"error": error_name})
        try:
            send_email_message(
                REQUESTS_MASTER_EMAIL,
                "New connector request" if lang.startswith("en") else "Nueva solicitud de conector",
                request_email_body(request_doc, dataspace_label(), lang=lang),
            )
        except Exception as exc:
            request_doc["notificationError"] = str(exc)
            items = load_requests()
            for item in items:
                if item.get("requestId") == request_doc["requestId"]:
                    item["notificationError"] = str(exc)
            save_requests(items)

        return json_response(
            self,
            200,
            {
                "ok": True,
                "requestId": request_doc["requestId"],
                "connectorId": request_doc["connectorId"],
                "status": "pending",
                "message": (
                    "Solicitud enviada. Recibirás un correo cuando el administrador apruebe o deniegue el alta."
                    if not lang.startswith("en")
                    else "Request submitted. You will receive an email when the administrator approves or denies it."
                ),
            },
        )


if __name__ == "__main__":
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    FILES_DIR.mkdir(parents=True, exist_ok=True)
    ensure_requests_storage()
    refresh_existing_connector_pages()
    migrate_connectors_to_participants()
    # Las reparaciones hablan con Keycloak, que en un despliegue se está
    # recreando a la vez que esto arranca, así que van en su propio hilo y no
    # retrasan la apertura del puerto.
    if EVALUATION_MODE:
        print("=" * 70)
        print("MODO DE EVALUACION: no hay proveedor de identidad y no se pide")
        print("contrasena a nadie. Cualquiera que alcance este nodo puede")
        print("publicar, negociar y descargar. Es para probar el producto y")
        print("para docencia. NO lo dejes donde llegue nadie mas.")
        print("=" * 70)
    else:
        threading.Thread(target=run_startup_repairs, name="startup-repairs", daemon=True).start()
    # El catálogo consolidado se sincroniza en su propio hilo, por la misma
    # razón: si Fuseki tarda en subir, o un nodo remoto no contesta, el portal
    # tiene que estar sirviendo igual. Publicar, negociar y descargar no
    # dependen de esta vista.
    threading.Thread(target=federation_loop, name="catalog-federation", daemon=True).start()
    # El producto de datos de ejemplo, si se ha pedido. Va en su propio hilo
    # porque necesita que el conector este arriba, y el conector arranca a la
    # vez que esto: bloquear el puerto esperandolo deja el portal caido.
    if os.getenv("ODS_SEED_DEMO", "true").strip().lower() not in ("false", "0", "no"):
        threading.Thread(target=seed_demo_when_ready, name="seed-demo", daemon=True).start()
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"[onboarding-api] listening on {HOST}:{PORT}")
    httpd.serve_forever()
