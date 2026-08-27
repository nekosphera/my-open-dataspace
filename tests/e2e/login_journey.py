#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""El recorrido de alta y acceso, hecho como lo hace una persona.

Esto faltaba, y su ausencia es la razón de que el acceso se rompiera dos veces
sin que nada lo dijera: `golden_path.py` usa un token de la cuenta de servicio
del conector, así que **nunca ejerció el login**. Un adaptador de Keycloak
borrado y un cliente mal configurado pasan por delante de una prueba así sin
tocarla.

Lo que se recorre, entero:

  1. Pedir un captcha y resolverlo.
  2. Darse de alta con él.
  3. Que el administrador apruebe la solicitud.
  4. **Entrar**: flujo de código de autorización con PKCE contra Keycloak,
     rellenando el formulario de acceso igual que un navegador.
  5. Usar el token en la consola y comprobar que trae los grupos.
  6. Que la contraseña equivocada no entre.

    python tests/e2e/login_journey.py http://localhost:8080
"""
from __future__ import annotations

import base64
import hashlib
import html
import http.cookiejar
import json
import os
import re
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

FALLOS: list[str] = []
PASOS = 0


def comprobar(nombre, condicion, detalle=""):
    global PASOS
    PASOS += 1
    if condicion:
        print(f"  ok    {nombre}")
    else:
        print(f"  FALLA {nombre}" + (f" -- {detalle}" if detalle else ""))
        FALLOS.append(nombre)
    return bool(condicion)


def navegador():
    """Un cliente con galletas, que es lo que distingue esto de un curl.

    Keycloak reparte una cookie de sesión de autenticación entre el formulario
    y el envío; sin conservarla, el POST del formulario da «Your login attempt
    timed out» y parece un problema de credenciales.
    """
    tarro = http.cookiejar.CookieJar()
    return urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(tarro),
        urllib.request.HTTPRedirectHandler(),
    )


def pedir(opener, url, datos=None, cabeceras=None, seguir=True):
    cuerpo = urllib.parse.urlencode(datos).encode("utf-8") if datos else None
    req = urllib.request.Request(url, data=cuerpo, headers=cabeceras or {})
    if cuerpo:
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with opener.open(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace"), r.geturl()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace"), url


def json_api(base, ruta, payload=None, method="GET", token=""):
    datos = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(f"{base}{ruta}", data=datos, method=method)
    req.add_header("Accept", "application/json")
    if datos:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            crudo = r.read()
            return r.status, json.loads(crudo.decode("utf-8")) if crudo else {}
    except urllib.error.HTTPError as exc:
        crudo = exc.read()
        try:
            return exc.code, json.loads(crudo.decode("utf-8")) if crudo else {}
        except ValueError:
            return exc.code, {"raw": crudo.decode("utf-8", "replace")[:200]}
    except Exception as exc:  # noqa: BLE001
        return 0, {"error": str(exc)}


def resolver_captcha(pregunta):
    """Las preguntas son sumas: «5 + 6 = ?»."""
    numeros = re.findall(r"\d+", pregunta or "")
    if "+" in (pregunta or "") and len(numeros) >= 2:
        return str(int(numeros[0]) + int(numeros[1]))
    if "-" in (pregunta or "") and len(numeros) >= 2:
        return str(int(numeros[0]) - int(numeros[1]))
    return ""


def token_de_administracion(base):
    """Para aprobar la solicitud. Sin esto se salta ese paso."""
    admin = os.getenv("ODS_KEYCLOAK_ADMIN_PASSWORD", "").strip()
    if not admin:
        env = Path(__file__).resolve().parents[2] / ".env"
        if env.is_file():
            for linea in env.read_text(encoding="utf-8").splitlines():
                if linea.startswith("ODS_KEYCLOAK_ADMIN_PASSWORD="):
                    admin = linea.split("=", 1)[1].strip().strip('"\'')
    return admin


def crear_revisor(base, admin_token, correo, contrasena):
    """Una persona de `dataspace-admins`, creada por la vía de administración.

    Devuelve (ok, motivo). No usa la API del producto a propósito: lo que se
    quiere probar después es que esa persona pueda aprobar, no cómo llegó a
    existir.
    """
    auth = f"{base}/auth/admin/realms/dataspace"

    def admin(url, method="GET", payload=None):
        datos = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(url, data=datos, method=method)
        req.add_header("Authorization", f"Bearer {admin_token}")
        req.add_header("Accept", "application/json")
        if datos:
            req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=30) as r:
            crudo = r.read()
            return json.loads(crudo.decode("utf-8")) if crudo else {}

    try:
        admin(f"{auth}/users", method="POST", payload={
            "username": correo, "email": correo,
            "firstName": "Revisor", "lastName": "De Pruebas",
            "enabled": True, "emailVerified": True,
        })
        usuarios = admin(f"{auth}/users?username={urllib.parse.quote(correo)}&exact=true")
        if not usuarios:
            return False, "el usuario no apareció tras crearlo"
        uid = usuarios[0]["id"]
        admin(f"{auth}/users/{uid}/reset-password", method="PUT",
              payload={"type": "password", "value": contrasena, "temporary": False})
        grupos = admin(f"{auth}/groups")
        destino = next((g for g in grupos if g.get("name") == "dataspace-admins"), None)
        if not destino:
            return False, "no existe el grupo dataspace-admins"
        admin(f"{auth}/users/{uid}/groups/{destino['id']}", method="PUT")
        return True, ""
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)[:160]


def entrar(base, correo, contrasena):
    """El flujo de código de autorización con PKCE, como el navegador.

    Devuelve (token, motivo). Si no entra, `motivo` dice en qué punto se
    quedó, que es lo que una pantalla que sólo dice «No se pudo completar el
    login» nunca cuenta.
    """
    verificador = base64.urlsafe_b64encode(secrets.token_bytes(64)).decode().rstrip("=")
    reto = base64.urlsafe_b64encode(
        hashlib.sha256(verificador.encode()).digest()
    ).decode().rstrip("=")
    redirect = f"{base}/login.html"

    autorizar = f"{base}/auth/realms/dataspace/protocol/openid-connect/auth?" + urllib.parse.urlencode({
        "client_id": "dataspace-ui",
        "response_type": "code",
        "scope": "openid profile email",
        "redirect_uri": redirect,
        "code_challenge": reto,
        "code_challenge_method": "S256",
        "state": secrets.token_hex(8),
    })

    opener = navegador()
    estado, cuerpo, _ = pedir(opener, autorizar)
    if estado != 200:
        return "", f"la página de acceso contestó {estado}"
    if "Invalid parameter" in cuerpo:
        return "", "Keycloak rechazó la petición: " + (
            re.search(r"Invalid parameter[^<]*", cuerpo).group(0)
        )

    # El formulario de Keycloak: su `action` lleva el código de sesión.
    accion = re.search(r'<form[^>]+action="([^"]+)"', cuerpo)
    if not accion:
        return "", "la página de acceso no traía formulario"
    url_accion = html.unescape(accion.group(1))

    estado, cuerpo, destino = pedir(
        opener, url_accion, datos={"username": correo, "password": contrasena, "credentialId": ""}
    )

    # Por parámetro, no por subcadena: `session_code=…` contiene «code=», así
    # que buscarlo en la cadena daba positivo cuando el formulario había
    # fallado y seguía en la página de autenticación.
    parametros = urllib.parse.parse_qs(urllib.parse.urlparse(destino).query)
    if "code" not in parametros:
        motivo = re.search(r'id="input-error"[^>]*>([^<]+)', cuerpo) or re.search(
            r'kc-feedback-text[^>]*>([^<]+)', cuerpo
        )
        return "", (motivo.group(1).strip() if motivo else f"no volvió con código (estado {estado})")

    codigo = parametros["code"][0]

    estado, cuerpo, _ = pedir(
        opener,
        f"{base}/auth/realms/dataspace/protocol/openid-connect/token",
        datos={
            "grant_type": "authorization_code",
            "client_id": "dataspace-ui",
            "code": codigo,
            "redirect_uri": redirect,
            "code_verifier": verificador,
        },
    )
    if estado != 200:
        return "", (f"el canje del código falló con {estado}: {cuerpo[:160]} "
                    f"(volvió a {destino[:120]})")
    return json.loads(cuerpo).get("access_token", ""), ""


def claims(token):
    trozo = token.split(".")[1]
    trozo += "=" * (-len(trozo) % 4)
    return json.loads(base64.urlsafe_b64decode(trozo))


def main(base):
    base = base.rstrip("/")
    print(f"\nAlta y acceso contra {base}\n")

    estado, salud = json_api(base, "/api/onboarding/health")
    if estado != 200:
        comprobar("el nodo contesta", False, f"estado {estado}")
        return 1
    if salud.get("evaluationMode"):
        print("  ...   modo de evaluación: no hay identidad, no hay nada que probar aquí")
        return 0
    comprobar("el nodo contesta", True)

    sufijo = str(int(time.time()))
    correo = f"prueba.{sufijo}@ejemplo.invalid"
    contrasena = f"Prueba{sufijo}!x"

    # --- 1 y 2. Captcha y alta ---------------------------------------------
    estado, captcha = json_api(base, "/api/onboarding/captcha")
    comprobar("el captcha se sirve", estado == 200 and captcha.get("captchaId"))
    respuesta = resolver_captcha(captcha.get("question", ""))
    comprobar("el captcha es resoluble", bool(respuesta), captcha.get("question", ""))

    estado, _ = json_api(
        base, "/api/onboarding/register", method="POST",
        payload={"email": correo, "password": contrasena, "firstName": "Prueba",
                 "lastName": "Usuario", "lang": "es", "captchaId": captcha.get("captchaId", ""),
                 "captchaAnswer": "0000", "requestedRoleMode": "consumer"},
    )
    comprobar("un captcha equivocado no da de alta", estado == 400, f"contestó {estado}")

    estado, captcha = json_api(base, "/api/onboarding/captcha")
    respuesta = resolver_captcha(captcha.get("question", ""))
    estado, alta = json_api(
        base, "/api/onboarding/register", method="POST",
        payload={"email": correo, "password": contrasena, "firstName": "Prueba",
                 "lastName": "Usuario", "lang": "es", "captchaId": captcha.get("captchaId", ""),
                 "captchaAnswer": respuesta, "requestedRoleMode": "consumer"},
    )
    comprobar("el alta se registra", estado == 200 and alta.get("ok"), json.dumps(alta)[:160])
    solicitud = alta.get("requestId", "")

    # --- 3. Aprobación ------------------------------------------------------
    admin = token_de_administracion(base)
    if not admin or not solicitud:
        print("  ...   sin credenciales de administración; no se aprueba ni se prueba el acceso")
        return 1 if FALLOS else 0

    from urllib.request import Request, urlopen
    datos = urllib.parse.urlencode({
        "client_id": "admin-cli", "username": "admin",
        "password": admin, "grant_type": "password",
    }).encode()
    req = Request(f"{base}/auth/realms/master/protocol/openid-connect/token", data=datos)
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urlopen(req, timeout=30) as r:
        admin_token = json.loads(r.read())["access_token"]

    # Aprobar es una acción del producto, no de Keycloak: la hace alguien de
    # `dataspace-admins`, entrando por el mismo sitio que cualquiera. Así queda
    # probado ese camino y no sólo el de la API.
    revisor = f"revisor.{sufijo}@ejemplo.invalid"
    clave_revisor = f"Revisor{sufijo}!x"
    creado, motivo = crear_revisor(base, admin_token, revisor, clave_revisor)
    comprobar("se puede crear un revisor en dataspace-admins", creado, motivo)

    token_revisor, motivo = entrar(base, revisor, clave_revisor)
    comprobar("el revisor entra por el formulario de acceso", bool(token_revisor), motivo)

    estado, aprobacion = json_api(
        base, f"/api/onboarding/requests/{solicitud}/approve", method="POST",
        payload={}, token=token_revisor,
    )
    comprobar(
        "quien está en dataspace-admins puede aprobar", estado == 200,
        f"contestó {estado}: {json.dumps(aprobacion)[:200]}",
    )

    # --- 4. Entrar de verdad ------------------------------------------------
    token, motivo = entrar(base, correo, contrasena)
    comprobar("la persona recién dada de alta entra", bool(token), motivo)

    if token:
        c = claims(token)
        comprobar("el token trae sus grupos", bool(c.get("groups")), json.dumps(c.get("groups")))
        comprobar("y su correo", c.get("email") == correo or c.get("preferred_username") == correo)

        # --- 5. El token vale en la consola --------------------------------
        estado, _ = json_api(base, "/api/connector/v3/assets", token=token)
        comprobar("el token sirve para leer el catálogo del conector", estado == 200, f"contestó {estado}")

    # --- 6. La contraseña equivocada no entra -------------------------------
    malo, _ = entrar(base, correo, "EstaNoEsLaBuena9!")
    comprobar("una contraseña equivocada no entra", not malo)

    print()
    if FALLOS:
        print(f"FALLA: {len(FALLOS)} de {PASOS} -- " + "; ".join(FALLOS))
        return 1
    print(f"OK: {PASOS} comprobaciones")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"))
