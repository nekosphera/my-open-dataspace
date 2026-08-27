# -*- coding: utf-8 -*-
"""Un conector por participante, en un navegador de verdad.

Criterios 10 a 13 de la seccion 12, anadidos por la enmienda 16 del 28 de
agosto de 2026: dos personas se dan de alta en el mismo nodo, una publica y la
otra negocia y descarga lo que aquella publico.

Por que hace falta abrir un navegador: todo lo que esto comprueba vive entre el
token y la consola. El identificador del conector viaja como claim firmado; la
consola lo lee para saber quien mira; el catalogo atribuye cada oferta a su
participante. Una prueba de API llamaria con el token que ella misma se hace y
no ejercitaria ninguna de las tres cosas.

    python tests/e2e/navegador_conector_por_participante.py [--base URL]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from navegador_alta_y_acceso import (  # noqa: E402
    Navegador,
    contrasena_de_administracion,
    encontrar_navegador,
    kc,
    token_de_administracion,
)

FALLOS = 0


def comprobar(titulo, condicion, detalle=""):
    global FALLOS
    if condicion:
        print(f"  ok    {titulo}")
    else:
        FALLOS += 1
        print(f"  FALLO {titulo}" + (f" -- {detalle}" if detalle else ""))


def registrar(nav, base, correo, clave, perfil):
    """Rellena el formulario de alta, como una persona."""
    nav.ir(f"{base}/registro.html", 6)
    pregunta = nav.evaluar("document.getElementById('captchaQuestion')?.textContent") or ""
    cuentas = re.search(r"(\d+)\s*\+\s*(\d+)", pregunta)
    if not cuentas:
        raise RuntimeError(f"la pagina de alta no pinto su captcha: {pregunta!r}")
    suma = int(cuentas.group(1)) + int(cuentas.group(2))
    nav.evaluar(
        "document.getElementById('registerFirstName').value='Participante';"
        "document.getElementById('registerLastName').value='De Prueba';"
        f"document.getElementById('registerEmail').value={json.dumps(correo)};"
        f"document.getElementById('registerPassword').value={json.dumps(clave)};"
        f"document.getElementById('registerRoleMode').value={json.dumps(perfil)};"
        f"document.getElementById('captchaAnswer').value={json.dumps(str(suma))};"
        "document.getElementById('registerSubmit').click();1",
        esperar_promesa=False,
    )
    nav.bombear(10)
    return f"connector-{hashlib.sha1(correo.encode('utf-8')).hexdigest()[:10]}"


def aprobar(nav, correo):
    """Aprueba el alta de esa persona desde una sesion de administracion.

    Es lo que **levanta su conector**: su contenedor y su base de datos. Por eso
    la prueba pasa por aqui en vez de crear la cuenta a mano, que era como se
    hacia antes y dejaba a la persona con identificador y sin conector.
    """
    pendientes = json.loads(nav.evaluar("""(async () => {
      const t = await window.__DATASPACE_ENSURE_FRESH_TOKEN();
      const r = await fetch('/api/onboarding/requests?status=pending',
        { headers: { Authorization: 'Bearer ' + t } });
      const j = await r.json();
      return JSON.stringify((j.items || []).map(x => [x.requestId, x.email]));
    })()""") or "[]")
    fila = next((f for f in pendientes if f[1] == correo), None)
    if not fila:
        return False, "su solicitud no aparece entre las pendientes"
    respuesta = nav.evaluar("""(async () => {
      const t = await window.__DATASPACE_ENSURE_FRESH_TOKEN();
      const r = await fetch('/api/onboarding/requests/%s/approve', { method: 'POST',
        headers: { Authorization: 'Bearer ' + t, 'Content-Type': 'application/json' },
        body: '{}' });
      const j = await r.json().catch(() => ({}));
      return r.status + '|' + (j.message || j.error || '');
    })()""" % fila[0]) or ""
    return str(respuesta).startswith("200"), str(respuesta)[:200]


def crear_participante(base, token, correo, clave, grupos):
    """Una cuenta con su conector, como la deja una aprobacion."""
    hay = kc(base, token, f"/users?username={urllib.parse.quote(correo)}&exact=true")
    if not hay:
        kc(base, token, "/users", "POST", {
            "username": correo, "email": correo, "firstName": "Participante",
            "lastName": "De Prueba", "enabled": True, "emailVerified": True,
        })
        hay = kc(base, token, f"/users?username={urllib.parse.quote(correo)}&exact=true")
    uid = hay[0]["id"]
    kc(base, token, f"/users/{uid}/reset-password", "PUT",
       {"type": "password", "value": clave, "temporary": False})
    todos = {g["name"]: g["id"] for g in kc(base, token, "/groups")}
    for nombre in grupos:
        if nombre in todos:
            kc(base, token, f"/users/{uid}/groups/{todos[nombre]}", "PUT")
    connector_id = f"connector-{hashlib.sha1(correo.encode('utf-8')).hexdigest()[:10]}"
    actual = kc(base, token, f"/users/{uid}")
    atributos = dict(actual.get("attributes") or {})
    atributos["connector_id"] = [connector_id]
    kc(base, token, f"/users/{uid}", "PUT", {**actual, "attributes": atributos})
    guardado = (kc(base, token, f"/users/{uid}") or {}).get("attributes") or {}
    if guardado.get("connector_id") != [connector_id]:
        raise RuntimeError(
            "Keycloak no guardo connector_id: comprueba que esta declarado en el "
            "perfil de usuario del realm"
        )
    return uid, connector_id


def entrar(nav, base, correo, clave):
    nav.ir(f"{base}/login.html", 5)
    nav.evaluar("document.getElementById('loginBtn').click();1", esperar_promesa=False)
    nav.bombear(8)
    if not nav.evaluar("!!document.getElementById('username')"):
        return False, nav.evaluar("location.href")
    nav.evaluar(
        f"document.getElementById('username').value={json.dumps(correo)};"
        f"document.getElementById('password').value={json.dumps(clave)};"
        "document.getElementById('kc-form-login').submit();1",
        esperar_promesa=False,
    )
    nav.bombear(14)
    nav.bombear(5)
    return True, nav.evaluar("location.href")


def publicar(nav, asset_id, etiqueta, base):
    """Publica activo, politica y contrato por la API, con el token de quien mira."""
    fuente = f"{base}/api/onboarding/assets/seed/ocupacion-aparcamiento.csv"
    sufijo = asset_id.rsplit("-", 1)[-1]
    return nav.evaluar("""(async () => {
      const t = await window.__DATASPACE_ENSURE_FRESH_TOKEN();
      const h = { Authorization: 'Bearer ' + t, 'Content-Type': 'application/json' };
      const a = await fetch('/api/connector/management/v3/assets', { method: 'POST', headers: h,
        body: JSON.stringify({ '@id': %(asset)s, properties: {
          'dct:title': %(etiq)s, name: %(etiq)s, 'dct:description': 'Publicada por un participante',
          'dct:identifier': %(asset)s, 'dcat:theme': 'http://publications.europa.eu/resource/authority/data-theme/TECH',
          'dcat:keyword': 'prueba', 'dcat:mediaType': 'text/csv', 'dct:publisher': 'Participante',
          'dct:license': 'https://creativecommons.org/licenses/by/4.0/', 'dct:accessRights': 'public',
          'ods:deliveryMode': 'download', objectUrl: %(fuente)s },
          dataAddress: { type: 'HttpData', baseUrl: %(fuente)s } }) });
      const p = await fetch('/api/connector/management/v3/policydefinitions', { method: 'POST', headers: h,
        body: JSON.stringify({ '@id': 'policy-' + %(suf)s, policy: { name: 'Politica del participante' } }) });
      const c = await fetch('/api/connector/management/v3/contractdefinitions', { method: 'POST', headers: h,
        body: JSON.stringify({ '@id': 'contract-' + %(suf)s, accessPolicyId: 'policy-' + %(suf)s,
          contractPolicyId: 'policy-' + %(suf)s,
          assetsSelector: [{ leftOperand: 'id', operator: '=', rightOperand: %(asset)s }] }) });
      return [a.status, p.status, c.status].join('/');
    })()""" % {
        "asset": json.dumps(asset_id), "etiq": json.dumps(etiqueta),
        "fuente": json.dumps(fuente), "suf": json.dumps(sufijo),
    })


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=os.getenv("ODS_BASE_URL", "http://localhost:8080"))
    args = parser.parse_args()
    base = args.base.rstrip("/")

    ejecutable = encontrar_navegador()
    if not ejecutable:
        print("SALTADA: no hay Chrome ni Edge en esta maquina.")
        return 2
    try:
        import websocket  # noqa: F401
    except ImportError:
        print("SALTADA: falta websocket-client (pip install websocket-client).")
        return 2
    clave_admin = contrasena_de_administracion()
    if not clave_admin:
        print("SALTADA: sin ODS_KEYCLOAK_ADMIN_PASSWORD no se pueden crear los participantes.")
        return 2

    token = token_de_administracion(base, clave_admin)
    sufijo = str(int(time.time()))[-6:]
    proveedor = (f"prov.{sufijo}@ejemplo.invalid", f"Prov{sufijo}!xY")
    consumidor = (f"cons.{sufijo}@ejemplo.invalid", f"Cons{sufijo}!xY")
    revisor = (f"adm.{sufijo}@ejemplo.invalid", f"Adm{sufijo}!xY")
    asset_id, etiqueta = f"asset-vecino-{sufijo}", f"Oferta del vecino {sufijo}"

    print(f"Un conector por participante, en un navegador, contra {base}")

    # Quien aprueba: cuenta directa, con el conector del nodo. No necesita uno
    # propio porque administra, no publica.
    uid_a, _ = crear_participante(base, token, *revisor,
                                  ["connector-users", "dataspace-users", "dataspace-admins"])
    kc(base, token, f"/users/{uid_a}", "PUT", {
        **kc(base, token, f"/users/{uid_a}"),
        "attributes": {"connector_id": ["connector"]},
    })

    # Los dos participantes, por el camino de verdad: formulario y aprobación.
    # Es la aprobación la que **levanta su conector** —su contenedor y su base—,
    # así que crearlos a mano dejaría la prueba midiendo otra cosa.
    uid_p = uid_c = None
    nav = Navegador(ejecutable, puerto=9420)
    try:
        cid_p = registrar(nav, base, *proveedor, "provider")
        cid_c = registrar(nav, base, *consumidor, "consumer")
    finally:
        nav.cerrar()

    nav = Navegador(ejecutable, puerto=9419)
    try:
        entrar(nav, base, *revisor)
        ok_p, detalle_p = aprobar(nav, proveedor[0])
        comprobar("aprobar el alta levanta el conector del proveedor", ok_p, detalle_p)
        ok_c, detalle_c = aprobar(nav, consumidor[0])
        comprobar("y el del consumidor", ok_c, detalle_c)
    finally:
        nav.cerrar()

    # Token nuevo: registrar y aprobar por el navegador lleva minutos, y el de
    # administración de Keycloak caduca antes.
    token = token_de_administracion(base, clave_admin)
    uid_p = (kc(base, token, f"/users?username={urllib.parse.quote(proveedor[0])}&exact=true") or [{}])[0].get("id")
    uid_c = (kc(base, token, f"/users?username={urllib.parse.quote(consumidor[0])}&exact=true") or [{}])[0].get("id")
    comprobar("cada participante tiene su propio conector", cid_p != cid_c, f"{cid_p} / {cid_c}")

    try:
        # --- El proveedor -------------------------------------------------
        nav = Navegador(ejecutable, puerto=9421)
        try:
            entro, destino = entrar(nav, base, *proveedor)
            comprobar("el proveedor entra y llega a su consola",
                      entro and str(destino).endswith("/console.html"), str(destino))
            comprobar("y la consola lleva su conector, no el del nodo",
                      nav.evaluar("document.getElementById('consoleHeading')?.textContent") == f"Conector {cid_p}",
                      str(nav.evaluar("document.getElementById('consoleHeading')?.textContent")))
            comprobar("y su correo como dueno",
                      nav.evaluar("document.getElementById('consoleOwner')?.textContent") == proveedor[0],
                      str(nav.evaluar("document.getElementById('consoleOwner')?.textContent")))
            comprobar("publica activo, politica y contrato",
                      publicar(nav, asset_id, etiqueta, base) == "200/200/200",
                      str(publicar.__name__))
            suyos = nav.evaluar("""(async () => {
              const t = await window.__DATASPACE_ENSURE_FRESH_TOKEN();
              const r = await fetch('/api/connector/management/v3/assets',
                { headers: { Authorization: 'Bearer ' + t } });
              return (await r.json()).map(x => x.id || x['@id']).join(',');
            })()""") or ""
            comprobar("y en «sus activos» sale lo suyo", asset_id in suyos, suyos[:160])
        finally:
            nav.cerrar()

        # Aqui habia un paso en el que quien administra el nodo federaba a mano.
        # Se ha quitado a proposito: lo que hay que probar es que la oferta se
        # vea **sin que nadie haga nada**. Crear el contrato la federa, porque
        # es el momento en que existe para los demas; con el paso puesto, esta
        # prueba pasaba en verde mientras un participante real tenia que
        # esperar cinco minutos o pedirselo a quien administra.

        # --- El consumidor -------------------------------------------------
        nav = Navegador(ejecutable, puerto=9423)
        try:
            entrar(nav, base, *consumidor)
            suyos = nav.evaluar("""(async () => {
              const t = await window.__DATASPACE_ENSURE_FRESH_TOKEN();
              const r = await fetch('/api/connector/management/v3/assets',
                { headers: { Authorization: 'Bearer ' + t } });
              return (await r.json()).map(x => x.id || x['@id']).join(',');
            })()""") or ""
            comprobar("el consumidor no ve los activos del proveedor entre los suyos",
                      asset_id not in suyos, suyos[:160])

            nav.evaluar("document.getElementById('operationConsumerBtn')?.click();1",
                        esperar_promesa=False)
            nav.bombear(12)
            fila = ("(() => { const f = Array.from(document.querySelectorAll("
                    "'#operationConsumerPanel tbody tr')).find(r => r.innerText.includes("
                    + json.dumps(etiqueta) + "));")
            # Recargando hasta que aparezca, con tope. El nodo federa al nacer
            # el contrato, pero preguntarle a cada conector lleva su tiempo y
            # mirar una sola vez mide la suerte del momento, no el producto.
            fin = time.time() + 45
            while time.time() < fin and nav.evaluar(fila + " return !!f; })()") is not True:
                nav.evaluar("Array.from(document.querySelectorAll('#operationConsumerPanel button'))"
                            ".find(b=>/Recargar federado|Reload federated/i.test(b.textContent))?.click();1",
                            esperar_promesa=False)
                nav.bombear(8)
            comprobar("pero si la ve en el catalogo del espacio de datos",
                      nav.evaluar(fila + " return !!f; })()") is True)
            texto_fila = nav.evaluar(fila + " return f ? f.innerText : ''; })()") or ""
            comprobar("atribuida al conector del proveedor, no al nodo",
                      cid_p in texto_fila,
                      f"esperaba {cid_p} en: " + " ".join(texto_fila.split())[:200])

            # Y en la columna de proveedor, delante quien ofrece.
            #
            # Iba al reves: el nombre del nodo en grande y el identificador del
            # conector debajo, con lo que la oferta de una persona se leia como
            # «asignada» al nodo.
            celda = nav.evaluar(fila + " return f ? f.cells[0].innerText"
                                ".split(String.fromCharCode(10)).join(' | ') : ''; })()") or ""
            # El identificador del conector, no el correo: la columna la ve
            # cualquiera que entre en el nodo y la direccion de una persona no
            # se publica para eso.
            comprobar("y quien la ofrece va delante del nodo en la columna",
                      celda.startswith(cid_p), celda[:120])
            comprobar("sin publicar el correo de nadie",
                      proveedor[0] not in celda, celda[:120])
            comprobar("y se la ofrece negociar",
                      nav.evaluar(fila + " const b = f && f.querySelector('button');"
                                  " return b ? b.textContent.trim() : '-'; })()") in ("Aceptar", "Accept"))

            nav.evaluar(fila + " const b = f && f.querySelector('button');"
                        " if (b && !b.disabled) b.click(); return !!b; })()", esperar_promesa=False)
            nav.bombear(18)
            estado = nav.evaluar(
                "Array.from(document.querySelectorAll('.status'))"
                ".map(e => e.textContent.trim()).filter(Boolean).slice(-1)[0]") or ""
            comprobar("la negociacion se cierra", "error" not in estado.lower(), estado[:180])
            comprobar("y el boton pasa a la descarga",
                      nav.evaluar(fila + " const b = f && f.querySelector('button');"
                                  " return b ? b.textContent.trim() : '-'; })()") in ("Descargar", "Download"))

            # Al conector **del proveedor**, que es donde vive el dato: cada
            # participante tiene su instancia, y pedirselo al propio devuelve un
            # 404 con razon. Es la misma ruta que usa el boton de la consola.
            descarga = nav.evaluar("""(async () => {
              const t = await window.__DATASPACE_ENSURE_FRESH_TOKEN();
              const r = await fetch('/api/connector/%s/management/v3/assets/'
                + encodeURIComponent(%s) + '/download',
                { headers: { Authorization: 'Bearer ' + t } });
              return r.status + '|' + (await r.text()).length;
            })()""" % (cid_p, json.dumps(asset_id)))
            comprobar("y descarga el dato del vecino",
                      str(descarga).startswith("200|") and int(str(descarga).split("|")[1]) > 0,
                      str(descarga))

            comprobar("un consumidor no puede publicar", nav.evaluar("""(async () => {
              const t = await window.__DATASPACE_ENSURE_FRESH_TOKEN();
              const r = await fetch('/api/connector/management/v3/assets', { method: 'POST',
                headers: { Authorization: 'Bearer ' + t, 'Content-Type': 'application/json' },
                body: JSON.stringify({ properties: {}, dataAddress: {} }) });
              return String(r.status);
            })()""") == "403")
        finally:
            nav.cerrar()
    finally:
        for uid in (uid_p, uid_c, uid_a):
            try:
                kc(base, token, f"/users/{uid}", "DELETE")
            except Exception:
                pass

    print(f"\n{'TODO BIEN' if not FALLOS else str(FALLOS) + ' FALLO(S)'}")
    return 1 if FALLOS else 0


if __name__ == "__main__":
    sys.exit(main())
