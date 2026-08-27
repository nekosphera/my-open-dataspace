#!/usr/bin/env python3
"""Escribe app/ui/runtime-config.js a partir del .env del nodo.

La interfaz no lleva la marca dentro: la lee de un fichero que se genera en
cada arranque. Es lo que permite que dos organizaciones instalen esto y cada
una vea la suya sin tocar una sola linea de codigo.

El fichero generado no se versiona. Lo escribe el arranque del contenedor.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UI_DIR = ROOT / "app" / "ui"


def parse_env_file(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.exists():
        return data
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        data[key.strip()] = value
    return data


def resolve_env(env_file: Path | None) -> dict[str, str]:
    """El entorno del proceso manda sobre el fichero.

    La composicion pasa las variables por `environment:`, y el fichero es lo
    que hay cuando esto se ejecuta a mano. Si las dos fuentes discrepan, la
    que gana es la que el contenedor esta usando de verdad.
    """
    env = parse_env_file(env_file) if env_file else {}
    for key, value in os.environ.items():
        if key.startswith("ODS_") and value.strip():
            env[key] = value.strip()
    return env


def parse_enabled_identity_providers(value: str) -> dict[str, bool]:
    providers: dict[str, bool] = {}
    for raw_item in value.split(","):
        item = raw_item.strip().lower()
        if item:
            providers[item] = True
    return providers


def build_config(env: dict[str, str]) -> dict[str, object]:
    public_base_url = env.get("ODS_PUBLIC_URL", "").strip() or "http://localhost:8080"
    org_name = env.get("ODS_ORG_NAME", "").strip()

    return {
        # La marca es de quien instala. Sin nombre de organizacion se cae al
        # nombre del producto, que es lo que ve un nodo recien levantado
        # antes de pasar por el asistente.
        "brandName": org_name or "My Open Dataspace",
        "publicBaseUrl": public_base_url,
        "authBaseUrl": env.get("ODS_AUTH_URL", "").strip() or f"{public_base_url.rstrip('/')}/auth",
        "contactEmail": env.get("ODS_ADMIN_EMAIL", "").strip(),
        "dcatIdentifierPrefix": env.get("ODS_DCAT_IDENTIFIER_PREFIX", "").strip() or "urn:ods:dataset:",
        "defaultPublisher": org_name,
        "organisationId": env.get("ODS_ORG_ID", "").strip(),
        # Rutas relativas dentro del volumen de marca. Vacias mientras nadie
        # haya subido un logotipo: la interfaz se apana sin el.
        "iconPath": env.get("ODS_ICON_PATH", "").strip(),
        "brandMarkPath": env.get("ODS_BRAND_MARK_PATH", "").strip(),
        "logoPath": env.get("ODS_LOGO_PATH", "").strip(),
        "brandColor": env.get("ODS_BRAND_COLOR", "").strip() or "#1f5fd0",
        "legalNotice": env.get("ODS_LEGAL_NOTICE", "").strip(),
        "lang": env.get("ODS_LANG", "").strip() or "es",
        "realm": env.get("ODS_REALM", "").strip() or "dataspace",
        "connectorId": env.get("ODS_CONNECTOR_ID", "").strip() or "connector",
        "federatedIdentityProviders": parse_enabled_identity_providers(
            env.get("ODS_FEDERATED_IDENTITY_PROVIDERS", "")
        ),
    }


def write_runtime_config(config: dict[str, object], output_path: Path) -> None:
    payload = json.dumps(config, ensure_ascii=True, indent=2)
    content = (
        "// Generado por app/tools/render_ui_runtime_config.py. No se edita a mano.\n"
        "(function () {\n  window.DATASPACE_RUNTIME_CONFIG = Object.freeze("
        + payload.replace("\n", "\n  ")
        + ");\n})();\n"
    )
    output_path.write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render the UI runtime configuration from the node's .env."
    )
    parser.add_argument("--env-file", default=str(ROOT / ".env"))
    parser.add_argument("--output-dir", default=str(UI_DIR))
    args = parser.parse_args()

    env = resolve_env(Path(args.env_file))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_runtime_config(build_config(env), output_dir / "runtime-config.js")
    print(f"[render-ui-config] escrito {output_dir / 'runtime-config.js'}")


if __name__ == "__main__":
    main()
