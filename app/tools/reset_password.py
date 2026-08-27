#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Le pone una contraseña nueva a una cuenta del realm.

Se ejecuta dentro del contenedor `app`, que es quien tiene las credenciales de
administración de Keycloak. No se llama desde ninguna ruta HTTP a propósito:
si se pudiera pedir por la red, sería una forma de tomar la cuenta de otro.
Quien puede ejecutar esto ya tiene acceso a la máquina.

    ODS_RESET_EMAIL=... ODS_RESET_PASSWORD=... python app/tools/reset_password.py

Lo usa `./deploy/reiniciar.sh --contrasena <correo>`, que es la orden explícita
en la línea de comandos que la especificación pide para recuperar un nodo.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "").strip().rstrip("/") or "http://keycloak:8080/auth"
REALM = os.getenv("REALM_NAME", "").strip() or "dataspace"
ADMIN_USER = os.getenv("KEYCLOAK_ADMIN_USER", "").strip() or "admin"
ADMIN_PASSWORD = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "")

# El mismo perfil que exige el asistente. Aceptar aquí una contraseña que la
# consola rechazaría dejaría a alguien sin poder entrar con la que acaba de
# poner.
PERFIL = re.compile(r"^(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{9,}$")


def pedir(url, method="GET", token="", form=None, payload=None):
    data = None
    headers = {"Accept": "application/json"}
    if form is not None:
        data = urllib.parse.urlencode(form).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, method=method, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as respuesta:
        crudo = respuesta.read()
        return json.loads(crudo.decode("utf-8")) if crudo else {}


def main():
    correo = os.getenv("ODS_RESET_EMAIL", "").strip().lower()
    nueva = os.getenv("ODS_RESET_PASSWORD", "")

    if not correo or not nueva:
        print("Faltan ODS_RESET_EMAIL y ODS_RESET_PASSWORD.", file=sys.stderr)
        return 2
    if not PERFIL.match(nueva):
        print(
            "La contraseña no cumple el perfil del nodo: nueve caracteres o "
            "más, con una mayúscula, un número y un símbolo.",
            file=sys.stderr,
        )
        return 2
    if not ADMIN_PASSWORD:
        print(
            "Sin KEYCLOAK_ADMIN_PASSWORD no se puede hablar con Keycloak. "
            "¿Estás ejecutando esto dentro del contenedor app?",
            file=sys.stderr,
        )
        return 2

    try:
        token = pedir(
            f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token",
            method="POST",
            form={
                "client_id": "admin-cli",
                "username": ADMIN_USER,
                "password": ADMIN_PASSWORD,
                "grant_type": "password",
            },
        )["access_token"]
    except Exception as exc:  # noqa: BLE001
        print(f"Keycloak no contesta: {exc}", file=sys.stderr)
        return 1

    usuarios = pedir(
        f"{KEYCLOAK_URL}/admin/realms/{REALM}/users"
        f"?username={urllib.parse.quote(correo)}&exact=true",
        token=token,
    )
    if not usuarios:
        usuarios = pedir(
            f"{KEYCLOAK_URL}/admin/realms/{REALM}/users"
            f"?email={urllib.parse.quote(correo)}&exact=true",
            token=token,
        )
    if not usuarios:
        # Decir quién hay ahorra el viaje de adivinar el correo exacto.
        todos = pedir(f"{KEYCLOAK_URL}/admin/realms/{REALM}/users?max=20", token=token)
        conocidos = [u.get("username", "") for u in todos if not u.get("username", "").startswith("service-account-")]
        print(f"No hay ninguna cuenta «{correo}» en el realm {REALM}.", file=sys.stderr)
        if conocidos:
            print("Las que hay: " + ", ".join(sorted(conocidos)), file=sys.stderr)
        else:
            print(
                "No hay ninguna cuenta de persona. El nodo se configuró sin "
                "administrador, o el realm se recreó: usa "
                "./deploy/reiniciar.sh --asistente",
                file=sys.stderr,
            )
        return 1

    user_id = usuarios[0]["id"]
    pedir(
        f"{KEYCLOAK_URL}/admin/realms/{REALM}/users/{user_id}/reset-password",
        method="PUT",
        token=token,
        payload={"type": "password", "value": nueva, "temporary": False},
    )

    # Y que la cuenta esté habilitada: una deshabilitada acepta la contraseña
    # nueva y sigue sin poder entrar, que es el peor de los resultados.
    if not usuarios[0].get("enabled", True):
        pedir(
            f"{KEYCLOAK_URL}/admin/realms/{REALM}/users/{user_id}",
            method="PUT",
            token=token,
            payload={**usuarios[0], "enabled": True},
        )
        print(f"[reset] la cuenta estaba deshabilitada; se ha vuelto a habilitar")

    grupos = pedir(
        f"{KEYCLOAK_URL}/admin/realms/{REALM}/users/{user_id}/groups", token=token
    )
    print(f"[reset] contraseña cambiada para {correo}")
    print(f"[reset] grupos: {', '.join(g.get('name', '') for g in grupos) or '(ninguno)'}")
    if not any(g.get("name") == "dataspace-admins" for g in grupos):
        print(
            "[reset] AVISO esta cuenta no está en dataspace-admins, así que "
            "entrará pero no podrá administrar. Para un administrador nuevo: "
            "./deploy/reiniciar.sh --asistente"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
