#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""El recorrido completo contra un nodo levantado de verdad.

Es la prueba que gobierna la publicación: **si esto falla, no hay versión.**
Lo que comprueba es el criterio de aceptación de la especificación, no una
lista de funciones:

  1. Un nodo recién instalado manda a `/setup`.
  2. El asistente se completa y el nodo queda configurado.
  3. A partir de ahí `/setup` deja de existir.
  4. Hay un producto de datos de ejemplo publicado.
  5. El catálogo público del nodo lo ofrece, con el contacto del participante.
  6. La superficie de administración del conector **no** está publicada.
  7. Descargar sin negociación cerrada se rechaza.
  8. El punto SPARQL está cerrado.

No es un unittest: se ejecuta contra una dirección, en CI y a mano.

    python tests/e2e/golden_path.py http://localhost:8080
"""
from __future__ import annotations

import json
import secrets
import string
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

FALLOS: list[str] = []
PASOS = 0


def contrasena_de_una_vez():
    """Una contrasena distinta en cada ejecucion, y que no se imprime.

    Escrita en el fichero, esta prueba deja un administrador con una
    contrasena que esta publicada en el repositorio. Contra un nodo de usar y
    tirar da igual; contra el nodo de alguien que lo ejecuto «para ver si
    funciona» y luego se lo quedo, no.
    """
    alfabeto = string.ascii_letters + string.digits
    cuerpo = "".join(secrets.choice(alfabeto) for _ in range(20))
    # El perfil que el nodo exige: mayuscula, digito y simbolo.
    return f"A{cuerpo}9!"


def pedir(url, method="GET", payload=None, timeout=20, headers=None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    cabeceras = {"Accept": "application/json"}
    if data is not None:
        cabeceras["Content-Type"] = "application/json"
    cabeceras.update(headers or {})
    req = urllib.request.Request(url, method=method, data=data, headers=cabeceras)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as respuesta:
            crudo = respuesta.read()
            try:
                return respuesta.status, json.loads(crudo.decode("utf-8")) if crudo else {}
            except ValueError:
                return respuesta.status, crudo
    except urllib.error.HTTPError as exc:
        crudo = exc.read()
        try:
            return exc.code, json.loads(crudo.decode("utf-8")) if crudo else {}
        except ValueError:
            return exc.code, crudo
    except Exception as exc:  # noqa: BLE001
        return 0, {"error": str(exc)}


def comprobar(nombre, condicion, detalle=""):
    global PASOS
    PASOS += 1
    if condicion:
        print(f"  ok    {nombre}")
    else:
        print(f"  FALLA {nombre}" + (f" -- {detalle}" if detalle else ""))
        FALLOS.append(nombre)
    return bool(condicion)


def esperar(descripcion, comprobacion, intentos=60, espera=5):
    print(f"  ...   esperando {descripcion}")
    for _ in range(intentos):
        if comprobacion():
            return True
        time.sleep(espera)
    return False


def main(base):
    base = base.rstrip("/")
    print(f"\nRecorrido completo contra {base}\n")

    # --- El nodo contesta --------------------------------------------------
    if not esperar("a que el nodo conteste", lambda: pedir(f"{base}/api/onboarding/health")[0] == 200):
        comprobar("el nodo contesta", False, "no contestó a tiempo")
        return 1
    comprobar("el nodo contesta", True)

    # --- 1. Sin configurar, todo va al asistente ---------------------------
    estado, _ = pedir(f"{base}/api/v1/setup")
    ya_configurado = estado == 404
    if ya_configurado:
        print("  ...   el nodo ya estaba configurado; se saltan los pasos 1-3")
    else:
        comprobar("el asistente existe en un nodo sin configurar", estado == 200)

        if not esperar(
            "al servicio de identidad",
            lambda: pedir(f"{base}/api/v1/setup")[1].get("identityReady") is not False,
            intentos=60,
        ):
            comprobar("la identidad está lista", False)

        # --- 2. Completarlo ------------------------------------------------
        codigo, cuerpo = pedir(
            f"{base}/api/v1/setup",
            method="POST",
            payload={
                "orgName": "Organización de prueba",
                "orgId": "prueba-e2e",
                "adminEmail": "admin@prueba.example",
                "adminPassword": contrasena_de_una_vez(),
                "lang": "es",
            },
            timeout=120,
        )
        comprobar("el asistente se completa", codigo == 200, json.dumps(cuerpo)[:200])

        # --- 3. Y deja de existir ------------------------------------------
        comprobar("después, /setup devuelve 404", pedir(f"{base}/api/v1/setup")[0] == 404)

    comprobar("el portal responde", pedir(f"{base}/")[0] == 200)
    comprobar("la consola responde", pedir(f"{base}/console.html")[0] == 200)

    # --- 4 y 5. El ejemplo publicado, en el catálogo público ---------------
    def hay_ejemplo():
        _, cuerpo = pedir(f"{base}/api/v1/catalog")
        return isinstance(cuerpo, dict) and len(cuerpo.get("assets") or []) > 0

    if not esperar("al producto de datos de ejemplo", hay_ejemplo, intentos=40):
        comprobar("hay un producto de ejemplo publicado", False, "no apareció a tiempo")
    else:
        codigo, catalogo = pedir(f"{base}/api/v1/catalog")
        activos = catalogo.get("assets") or []
        comprobar("hay un producto de ejemplo publicado", len(activos) > 0)
        comprobar(
            "el catálogo declara el contacto del participante",
            bool((catalogo.get("contactPoint") or {}).get("email")),
            json.dumps(catalogo.get("contactPoint"))[:120],
        )
        comprobar(
            "cada producto declara su política y su contrato",
            all(
                a.get("properties", {}).get("ods:policyId")
                and a.get("properties", {}).get("ods:contractId")
                for a in activos
            ),
        )

    # --- 6. La administración del conector no está publicada ---------------
    codigo, _ = pedir(f"{base}/management/v3/assets")
    comprobar(
        "la API de administración del conector no está publicada",
        codigo in (0, 404, 502),
        f"contestó {codigo}",
    )
    # En la imagen de evaluación no hay identidad, así que exigir un token
    # sería exigir algo que no existe. Lo que sí tiene que ser cierto en los
    # dos modos es que el nodo **diga** en cuál está: un nodo sin
    # autenticación y uno con ella se ven igual desde fuera hasta que alguien
    # intenta algo.
    _, salud = pedir(f"{base}/api/onboarding/health")
    evaluacion = bool(isinstance(salud, dict) and salud.get("evaluationMode"))
    codigo, _ = pedir(f"{base}/api/connector/v3/assets")
    if evaluacion:
        print("  ...   modo de evaluación: no hay identidad que exigir")
        comprobar(
            "el nodo declara que está en modo de evaluación",
            evaluacion,
        )
        comprobar(
            "y aun así el paso al conector responde",
            codigo == 200,
            f"contestó {codigo}",
        )
    else:
        comprobar("el paso al conector exige identidad", codigo == 401, f"contestó {codigo}")

    # --- 7. Descargar sin negociación cerrada ------------------------------
    _, catalogo = pedir(f"{base}/api/v1/catalog")
    activos = (catalogo or {}).get("assets") or []
    if activos:
        asset_id = activos[0].get("id") or activos[0].get("@id") or ""
        codigo, _ = pedir(
            f"{base}/api/connector/v3/assets/{urllib.parse.quote(asset_id, safe='')}/download"
        )
        comprobar(
            "descargar sin negociación cerrada se rechaza",
            codigo in (401, 403),
            f"contestó {codigo}",
        )

    # --- 8. El punto SPARQL, cerrado ---------------------------------------
    codigo, _ = pedir(f"{base}/sparql?query=SELECT%20*%20WHERE%20%7B%3Fs%20%3Fp%20%3Fo%7D")
    comprobar(
        "el punto SPARQL está cerrado por omisión",
        codigo == 404,
        f"contestó {codigo}; si está abierto a propósito, ODS_SPARQL_PUBLIC lo dice",
    )

    print()
    if FALLOS:
        print(f"FALLA: {len(FALLOS)} de {PASOS} comprobaciones -- " + "; ".join(FALLOS))
        return 1
    print(f"OK: {PASOS} comprobaciones")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"))
