# -*- coding: utf-8 -*-
"""El alta y el acceso, en un navegador de verdad.

Por que hace falta ademas de `login_journey.py`: aquella prueba conduce el
flujo OIDC desde Python. Nunca ejecuta el JavaScript de `login.html`, que es
lo que corre cuando una persona pulsa el boton, y por eso daba verde mientras
el acceso estaba roto por donde se usa. Lo que se rompio y no vio nadie:

- la consola pedia `/api/connector/management/v3/...` y el paso solo aceptaba
  `/api/connector/v3/...`, asi que **todas** sus llamadas daban 404;
- quien administra el nodo entraba bien y aterrizaba en la pagina publica, que
  sigue diciendo «Acceder»;
- la pantalla para aprobar un alta no existia en la consola generada, asi que
  quien se registraba esperaba para siempre.

Nada de eso se ve sin abrir un navegador. Esta prueba lo abre.

Necesita Chrome o Edge y `websocket-client`. Si no hay navegador se salta con
un aviso, no con un verde: una prueba que no se ejecuto no es una prueba que
paso.

    python tests/e2e/navegador_alta_y_acceso.py [--base http://localhost:8080]
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
FALLOS = 0

NAVEGADORES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
]


def comprobar(titulo, condicion, detalle=""):
    global FALLOS
    if condicion:
        print(f"  ok    {titulo}")
    else:
        FALLOS += 1
        print(f"  FALLO {titulo}" + (f" -- {detalle}" if detalle else ""))


def encontrar_navegador():
    for ruta in NAVEGADORES:
        if Path(ruta).exists():
            return ruta
    for nombre in ("google-chrome", "chromium", "chrome", "msedge"):
        hallado = shutil.which(nombre)
        if hallado:
            return hallado
    return ""


class Navegador:
    """Lo minimo del protocolo de DevTools para pulsar y mirar."""

    def __init__(self, ejecutable, puerto=9411):
        import websocket  # se importa aqui: sin navegador no hace falta

        self.perfil = tempfile.mkdtemp(prefix="ods-e2e-")
        self.proc = subprocess.Popen(
            [
                ejecutable, "--headless=new", "--disable-gpu", "--no-sandbox",
                "--no-first-run", "--disable-features=Translate",
                # Sin esto Chrome rechaza la conexion de depuracion con un 403
                # y el fallo no se parece en nada a su causa.
                "--remote-allow-origins=*",
                f"--remote-debugging-port={puerto}",
                f"--user-data-dir={self.perfil}", "about:blank",
            ],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        self.ws = None
        self.id = 0
        self.eventos = []
        for _ in range(80):
            try:
                paginas = json.loads(
                    urllib.request.urlopen(f"http://127.0.0.1:{puerto}/json", timeout=2).read()
                )
                objetivo = next(p for p in paginas if p["type"] == "page")
                self.ws = websocket.create_connection(
                    objetivo["webSocketDebuggerUrl"], timeout=30, suppress_origin=True
                )
                break
            except Exception:
                time.sleep(0.4)
        if not self.ws:
            raise RuntimeError("el navegador no abrio su puerto de depuracion")
        for metodo in ("Page.enable", "Runtime.enable", "Log.enable", "Network.enable"):
            self.enviar(metodo)

    def enviar(self, metodo, **params):
        self.id += 1
        self.ws.send(json.dumps({"id": self.id, "method": metodo, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self.id:
                if "error" in msg:
                    raise RuntimeError(f"{metodo}: {msg['error']}")
                return msg.get("result", {})
            if "method" in msg:
                self.eventos.append(msg)

    def bombear(self, segundos):
        fin = time.time() + segundos
        self.ws.settimeout(0.3)
        while time.time() < fin:
            try:
                self.eventos.append(json.loads(self.ws.recv()))
            except Exception:
                pass
        self.ws.settimeout(30)

    def ir(self, url, espera=5):
        self.enviar("Page.navigate", url=url)
        self.bombear(espera)

    def evaluar(self, expresion, esperar_promesa=True):
        r = self.enviar("Runtime.evaluate", expression=expresion,
                        returnByValue=True, awaitPromise=esperar_promesa)
        if r.get("exceptionDetails"):
            detalle = r["exceptionDetails"]
            texto = (detalle.get("exception") or {}).get("description") or detalle.get("text")
            return f"[EXCEPCION] {texto}"
        return r.get("result", {}).get("value")

    def fallos(self, desde=0):
        """Errores de consola y peticiones que no llegaron, sin repetir."""
        salida = []
        for e in self.eventos[desde:]:
            metodo = e.get("method")
            if metodo == "Log.entryAdded" and e["params"]["entry"].get("level") == "error":
                x = e["params"]["entry"]
                salida.append(f"{x.get('text','')[:110]} {x.get('url','')[:90]}")
            elif metodo == "Runtime.exceptionThrown":
                d = e["params"]["exceptionDetails"]
                salida.append(f"excepcion: {(d.get('exception') or {}).get('description','')[:140]}")
        vistos, unicos = set(), []
        for linea in salida:
            if linea not in vistos:
                vistos.add(linea)
                unicos.append(linea)
        return unicos

    def cerrar(self):
        try:
            self.ws.close()
        except Exception:
            pass
        self.proc.terminate()
        try:
            self.proc.wait(timeout=10)
        except Exception:
            self.proc.kill()
        time.sleep(0.5)
        shutil.rmtree(self.perfil, ignore_errors=True)


# --- Lo que hace falta de Keycloak para preparar al revisor --------------

def contrasena_de_administracion():
    valor = os.getenv("ODS_KEYCLOAK_ADMIN_PASSWORD", "").strip()
    if valor:
        return valor
    env = RAIZ / ".env"
    if env.is_file():
        for linea in env.read_text(encoding="utf-8").splitlines():
            if linea.startswith("ODS_KEYCLOAK_ADMIN_PASSWORD="):
                return linea.split("=", 1)[1].strip().strip("\"'")
    return ""


def token_de_administracion(base, clave):
    datos = urllib.parse.urlencode({
        "client_id": "admin-cli", "username": "admin",
        "password": clave, "grant_type": "password",
    }).encode()
    req = urllib.request.Request(f"{base}/auth/realms/master/protocol/openid-connect/token", data=datos)
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())["access_token"]


def kc(base, token, ruta, method="GET", payload=None):
    datos = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(f"{base}/auth/admin/realms/dataspace{ruta}", data=datos, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    if datos:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as r:
        crudo = r.read()
        return json.loads(crudo) if crudo else {}


def crear_revisor(base, token, correo, clave):
    """Alguien de `dataspace-admins`: quien gobierna el nodo."""
    hay = kc(base, token, f"/users?username={urllib.parse.quote(correo)}&exact=true")
    if not hay:
        kc(base, token, "/users", "POST", {
            "username": correo, "email": correo, "firstName": "Revisor",
            "lastName": "De Prueba", "enabled": True, "emailVerified": True,
        })
        hay = kc(base, token, f"/users?username={urllib.parse.quote(correo)}&exact=true")
    uid = hay[0]["id"]
    kc(base, token, f"/users/{uid}/reset-password", "PUT",
       {"type": "password", "value": clave, "temporary": False})
    grupos = {g["name"]: g["id"] for g in kc(base, token, "/groups")}
    for nombre in ("dataspace-users", "dataspace-negotiators", "dataspace-admins", "connector-users"):
        if nombre in grupos:
            kc(base, token, f"/users/{uid}/groups/{grupos[nombre]}", "PUT")
    return uid


def borrar_usuario(base, token, correo):
    try:
        hay = kc(base, token, f"/users?username={urllib.parse.quote(correo)}&exact=true")
        if hay:
            kc(base, token, f"/users/{hay[0]['id']}", "DELETE")
    except Exception:
        pass


# --- El recorrido --------------------------------------------------------

def rellenar(nav, valores):
    """Escribe en los campos y avisa: la consola escucha `input` y `change`."""
    js = ("const p=(id,v)=>{const e=document.getElementById(id); if(e){e.value=v;"
          "e.dispatchEvent(new Event('input',{bubbles:true}));"
          "e.dispatchEvent(new Event('change',{bubbles:true}));}};")
    for clave, valor in valores.items():
        js += f"p({json.dumps(clave)},{json.dumps(valor)});"
    nav.evaluar(js + "1", esperar_promesa=False)


def estados(nav):
    return nav.evaluar(
        "Array.from(document.querySelectorAll('.status'))"
        ".map(e => e.textContent.trim()).filter(Boolean)"
    ) or []


def ultimo_estado(nav):
    valores = estados(nav)
    return valores[-1] if valores else ""


def esperar_estado(nav, patron, segundos=12):
    """Espera a que aparezca un mensaje, en vez de leer el ultimo.

    Leer el ultimo no vale: despues de publicar, la consola recarga sus
    catalogos y escribe «Catalogos cargados» encima del «Asset creado». La
    comprobacion daba por fallado algo que habia salido bien -- y, al reves,
    daba por bueno cualquier mensaje que no dijera «error».
    """
    fin = time.time() + segundos
    visto = []
    while time.time() < fin:
        for texto in estados(nav):
            if texto not in visto:
                visto.append(texto)
            if re.search(patron, texto, re.I):
                return True, texto
        nav.bombear(0.6)
    return False, " | ".join(visto[-3:])


def acceder(nav, base, correo, clave):
    """Pulsa el boton de acceso y rellena el formulario, como una persona."""
    nav.ir(f"{base}/login.html", 5)
    if not nav.evaluar("!!document.getElementById('loginBtn')"):
        return False, "no hay boton de acceso en /login.html"
    nav.evaluar("document.getElementById('loginBtn').click();1", esperar_promesa=False)
    nav.bombear(8)
    if not nav.evaluar("!!document.getElementById('username')"):
        return False, f"no salio el formulario de usuario: {nav.evaluar('location.href')}"
    nav.evaluar(
        f"document.getElementById('username').value={json.dumps(correo)};"
        f"document.getElementById('password').value={json.dumps(clave)};"
        "document.getElementById('kc-form-login').submit();1",
        esperar_promesa=False,
    )
    nav.bombear(12)
    destino = nav.evaluar("location.href") or ""
    if "/auth/realms/" in destino:
        texto = (nav.evaluar("document.body.innerText") or "").replace("\n", " ")[:160]
        return False, f"se quedo en la pantalla de autenticacion: {texto}"
    return True, destino


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=os.getenv("ODS_BASE_URL", "http://localhost:8080"))
    args = parser.parse_args()
    base = args.base.rstrip("/")

    ejecutable = encontrar_navegador()
    if not ejecutable:
        print("SALTADA: no hay Chrome ni Edge en esta maquina.")
        print("Esta prueba es la unica que ejecuta el JavaScript del acceso.")
        return 2
    try:
        import websocket  # noqa: F401
    except ImportError:
        print("SALTADA: falta websocket-client (pip install websocket-client).")
        return 2

    clave_admin = contrasena_de_administracion()
    if not clave_admin:
        print("SALTADA: sin ODS_KEYCLOAK_ADMIN_PASSWORD no se puede preparar al revisor.")
        return 2

    sufijo = str(int(time.time()))[-6:]
    revisor, clave_revisor = f"revisor.{sufijo}@ejemplo.invalid", f"Revisor{sufijo}!x"
    aspirante, clave_aspirante = f"alta.{sufijo}@ejemplo.invalid", f"Alta{sufijo}!xY"

    token_admin = token_de_administracion(base, clave_admin)
    crear_revisor(base, token_admin, revisor, clave_revisor)

    print(f"Alta y acceso en un navegador de verdad contra {base}")
    nav = Navegador(ejecutable)
    try:
        # --- 1. Alguien se da de alta por el formulario ------------------
        nav.ir(f"{base}/registro.html", 6)
        pregunta = nav.evaluar("document.getElementById('captchaQuestion')?.textContent") or ""
        cuentas = re.search(r"(\d+)\s*([+\-x*])\s*(\d+)", pregunta)
        comprobar("la pagina de alta pinta su captcha", bool(cuentas), repr(pregunta))
        if not cuentas:
            return 1
        a, op, b = int(cuentas.group(1)), cuentas.group(2), int(cuentas.group(3))
        resultado = a + b if op == "+" else (a - b if op == "-" else a * b)

        marca = len(nav.eventos)
        nav.evaluar(
            "document.getElementById('registerFirstName').value='Alta';"
            "document.getElementById('registerLastName').value='De Prueba';"
            f"document.getElementById('registerEmail').value={json.dumps(aspirante)};"
            f"document.getElementById('registerPassword').value={json.dumps(clave_aspirante)};"
            "document.getElementById('registerRoleMode').value='provider';"
            f"document.getElementById('captchaAnswer').value={json.dumps(str(resultado))};"
            "document.getElementById('registerSubmit').click();1",
            esperar_promesa=False,
        )
        nav.bombear(10)
        respuesta = (nav.evaluar("document.getElementById('registerResult')?.textContent") or "")
        comprobar("la solicitud se envia desde el formulario",
                  "enviada" in respuesta.lower() or "submitted" in respuesta.lower(),
                  respuesta[:180])
        comprobar("el alta no deja errores en la consola del navegador",
                  not nav.fallos(marca), " | ".join(nav.fallos(marca))[:200])

        # --- 2. Quien administra entra y aterriza en la consola ----------
        entro, destino = acceder(nav, base, revisor, clave_revisor)
        comprobar("quien administra el nodo entra pulsando el boton", entro, destino)
        comprobar("y aterriza en la consola, no en la pagina publica",
                  entro and destino.endswith("/console.html"), destino)

        marca = len(nav.eventos)
        nav.bombear(6)
        comprobar("la consola carga sin errores de red ni excepciones",
                  not nav.fallos(marca), " | ".join(nav.fallos(marca))[:250])

        # --- 3. La pantalla de altas existe y aprueba -------------------
        # Lo que se dibuja, no el atributo: `b.hidden` daba verde con el boton
        # a la vista, porque la regla `button { display: inline-block }` gana al
        # `[hidden]` del navegador y el atributo no ocultaba nada.
        visible = nav.evaluar(
            "(() => { const b = document.getElementById('operationRequestsBtn');"
            " return !!b && b.getBoundingClientRect().width > 0; })()"
        )
        comprobar("la pestana de solicitudes esta a la vista de quien administra", visible is True)
        if visible is True:
            nav.evaluar("document.getElementById('operationRequestsBtn').click();1",
                        esperar_promesa=False)
            nav.bombear(6)
            filas = nav.evaluar(
                "document.getElementById('connectorRequestsTable')?.innerText || ''") or ""
            comprobar("la solicitud recien enviada aparece en la lista",
                      aspirante in filas, filas.replace("\n", " ")[:200])
            if aspirante in filas:
                nav.evaluar(
                    "(() => { const f = Array.from(document.querySelectorAll("
                    "'#connectorRequestsTable tbody tr')).find(r => r.innerText.includes("
                    f"{json.dumps(aspirante)}));"
                    " if (!f) return false;"
                    " const b = f.querySelector('[data-accion=\"approve\"]');"
                    " if (!b) return false; b.click(); return true; })()",
                    esperar_promesa=False,
                )
                nav.bombear(12)
                estado = nav.evaluar(
                    "document.getElementById('connectorRequestsStatus')?.textContent") or ""
                comprobar("aprobar contesta sin error",
                          "error" not in estado.lower() and "fail" not in estado.lower(), estado[:180])


        # --- 3 bis. Publicar un producto de datos, pulsando --------------
        #
        # Esta parte encontro tres cosas que ninguna prueba de API podia ver:
        # la consola enviaba `myds:deliveryMode` y el perfil exige
        # `ods:deliveryMode` -- no se podia publicar nada, pusiera lo que
        # pusiera quien lo intentara --; «actualizar ahora» mandaba un POST sin
        # cuerpo y el servidor lo llamaba «invalid_json»; y la consulta del
        # catalogo pedia la politica colgada del activo, donde no esta, asi que
        # ninguna fila traia con que negociar.
        etiqueta = f"Producto {sufijo}"
        nav.evaluar("document.getElementById('operationProviderBtn').click();1",
                    esperar_promesa=False)
        nav.bombear(3)
        rellenar(nav, {
            "assetBaseUrl": f"{base}/api/onboarding/assets/seed/calidad-aire.csv",
            "assetName": etiqueta,
            "assetDescription": "Publicado desde la consola en una prueba de extremo a extremo.",
            "assetTheme": "http://publications.europa.eu/resource/authority/data-theme/TECH",
            "assetKeywords": "prueba, extremo a extremo",
        })
        nav.evaluar("document.querySelector('#assetForm button[type=submit]').click();1",
                    esperar_promesa=False)
        ok, detalle = esperar_estado(nav, r"asset\s+creado|asset\s+created", 15)
        comprobar("se publica un data asset desde la consola", ok, detalle[:200])
        # El identificador que la consola acaba de generar, para pedir despues
        # su descarga por la misma ruta que usa el boton.
        encontrado = re.search(r"(asset-[A-Za-z0-9._:-]+)", detalle or "")
        id_publicado = encontrado.group(1) if encontrado else ""
        comprobar("y dice con que identificador", bool(id_publicado), detalle[:200])

        rellenar(nav, {
            "policyName": f"Politica {sufijo}",
            "policySourceUrl": f"{base}/files/politica.txt",
            "policyPurpose": "Prueba de extremo a extremo",
            "policyLicenseUrl": "https://creativecommons.org/licenses/by/4.0/",
        })
        nav.evaluar("document.querySelector('#policyForm button[type=submit]').click();1",
                    esperar_promesa=False)
        ok, detalle = esperar_estado(nav, r"pol[ií]tica\s+creada|policy\s+created", 15)
        comprobar("se crea la politica", ok, detalle[:200])

        nav.evaluar(
            "const a=document.getElementById('contractAssetIdSelect');"
            "const p=document.getElementById('contractPolicyIdSelect');"
            "if(a&&a.options.length)a.selectedIndex=a.options.length-1;"
            "if(p&&p.options.length)p.selectedIndex=p.options.length-1;1",
            esperar_promesa=False)
        nav.evaluar("document.querySelector('#contractForm button[type=submit]').click();1",
                    esperar_promesa=False)
        ok, detalle = esperar_estado(nav, r"contrato\s+creado|contract\s+created", 15)
        comprobar("se crea el contrato que ata el activo a la politica", ok, detalle[:200])

        # Federar ahora. Se pide por la misma ruta que pulsaba el boton, porque
        # la pestana de nodos conocidos no se ofrece en esta entrega: el panel y
        # su codigo siguen ahi, pero nadie llega a el desde la interfaz. Fingir
        # un clic que una persona no puede dar seria probar otra cosa.
        federacion = nav.evaluar("""(async () => {
            const t = await window.__DATASPACE_ENSURE_FRESH_TOKEN();
            const res = await fetch('/api/v1/nodes/sync',
              { method: 'POST', headers: { Authorization: 'Bearer ' + t } });
            return res.status + ' ' + (await res.text()).slice(0, 160);
        })()""") or ""
        nav.bombear(10)
        comprobar("la federacion se puede lanzar y no da error",
                  federacion.startswith("200"), federacion[:180])

        nav.evaluar("document.getElementById('operationConsumerBtn').click();1", esperar_promesa=False)
        nav.bombear(6)
        # Cambiar de pestana no vuelve a pedir el catalogo: ensena lo que ya
        # tenia. Lo que se acaba de federar aparece cuando se recarga.
        nav.evaluar("Array.from(document.querySelectorAll('#operationConsumerPanel button'))"
                    ".find(b=>/Recargar federado|Reload federated/i.test(b.textContent))?.click();1",
                    esperar_promesa=False)
        nav.bombear(12)
        catalogo = nav.evaluar("document.getElementById('operationConsumerPanel')?.innerText || ''") or ""
        comprobar("lo publicado aparece en el catalogo consolidado",
                  etiqueta in catalogo, " ".join(catalogo.split())[:180])

        # --- 3 ter. Negociar y descargar, en el mismo nodo -----------------
        #
        # Es el criterio 6 de la seccion 12: publicar un producto y, **desde la
        # vista de consumo**, negociar su contrato y descargar el dato. Aqui la
        # consola devolvia «Activo propio» desactivado para toda fila de este
        # nodo, asi que ese recorrido no se podia hacer -- ni por quien
        # publicaba, ni por nadie que se hubiera dado de alta despues.
        #
        # Y la descarga no llegaba a funcionar nunca: el activo lleva la URL
        # publica del nodo -- tiene que llevarla, es la que viaja en el catalogo
        # federado -- y desde el contenedor del conector esa direccion no lleva
        # al portal, sino al propio conector.
        fila = ("(() => { const f = Array.from(document.querySelectorAll("
                "'#operationConsumerPanel tbody tr')).find(r => r.innerText.includes("
                + json.dumps(etiqueta) + "));")
        comprobar("lo publicado se puede negociar desde la vista de consumo",
                  nav.evaluar(fila + " if (!f) return 'sin fila'; const b = f.querySelector('button');"
                              " return b ? b.textContent.trim() + (b.disabled ? ' (desactivado)' : '')"
                              " : 'sin boton'; })()") == "Aceptar")

        nav.evaluar(fila + " const b = f && f.querySelector('button');"
                    " if (b && !b.disabled) b.click(); return !!b; })()", esperar_promesa=False)
        ok, detalle = esperar_estado(nav, r"negociaci[oó]n\s+completada|negotiation\s+completed", 20)
        comprobar("la negociacion se cierra", ok, detalle[:200])
        comprobar("y el boton pasa a ofrecer la descarga",
                  nav.evaluar(fila + " if (!f) return '-'; const b = f.querySelector('button');"
                              " return b ? b.textContent.trim() : '-'; })()") in ("Descargar", "Download"))

        descarga = nav.evaluar("""(async () => {
            const t = await window.__DATASPACE_ENSURE_FRESH_TOKEN();
            const res = await fetch('/api/connector/management/v3/assets/'
              + encodeURIComponent(%s) + '/download',
              { headers: { Authorization: 'Bearer ' + t } });
            const cuerpo = await res.text();
            return res.status + '|' + cuerpo.length;
        })()""" % json.dumps(id_publicado))
        comprobar("y el dato se descarga de verdad",
                  str(descarga).startswith("200|") and int(str(descarga).split("|")[1]) > 0,
                  str(descarga))
        # --- 4. Y quien se dio de alta puede entrar ---------------------
        # Se borran las cookies del navegador en vez de pedirle a Keycloak que
        # cierre la sesion: su `/logout` sin `id_token_hint` no cierra nada,
        # ensena una pantalla de confirmacion, y la prueba se quedaba mirando
        # una pagina de autenticacion sin formulario. Lo que hay que probar es
        # que esta persona entra desde cero, y desde cero es sin cookies.
        nav.enviar("Network.clearBrowserCookies")
        nav.evaluar("window.localStorage.clear(); window.sessionStorage.clear(); 1",
                    esperar_promesa=False)
        entro, destino = acceder(nav, base, aspirante, clave_aspirante)
        comprobar("quien se dio de alta entra con sus datos del formulario", entro, destino)
        comprobar("y aterriza en la consola de este nodo",
                  entro and destino.endswith("/console.html"), destino)

        # Un proveedor publica, pero no administra el nodo.
        #
        # Eran el mismo grupo: dar de alta a alguien como proveedor lo hacia
        # `dataspace-admins`, y ese grupo daba permiso para aprobar y denegar
        # altas ajenas y leer sus datos. Publicar y administrar son dos cosas
        # distintas, asi que se comprueban las dos por separado.
        nav.bombear(5)
        oculta = nav.evaluar(
            "(() => { const b = document.getElementById('operationRequestsBtn');"
            " return !b || b.getBoundingClientRect().width === 0; })()"
        )
        comprobar("un proveedor no ve la pantalla de aprobar altas", oculta is True)

        # La pestana de nodos conocidos no se ofrece en esta entrega. Se
        # comprueba que no se dibuja -- su panel sigue en la pagina a proposito.
        comprobar("la pestana de nodos conocidos no se ofrece", nav.evaluar(
            "(() => { const b = document.getElementById('operationNodesBtn');"
            " return !b || b.getBoundingClientRect().width === 0; })()") is True)

        prohibido = nav.evaluar("""(async () => {
            const t = await window.__DATASPACE_ENSURE_FRESH_TOKEN();
            const res = await fetch('/api/onboarding/requests?status=pending',
              { headers: { Authorization: 'Bearer ' + t } });
            return res.status;
        })()""")
        comprobar("y el servidor tampoco se las ensena", prohibido == 403, str(prohibido))

        nav.evaluar("document.getElementById('operationProviderBtn').click();1",
                    esperar_promesa=False)
        nav.bombear(3)
        rellenar(nav, {
            "assetBaseUrl": f"{base}/api/onboarding/assets/seed/calidad-aire.csv",
            "assetName": f"Proveedor {sufijo}",
            "assetDescription": "Publicado por alguien que provee y no administra.",
            "assetTheme": "http://publications.europa.eu/resource/authority/data-theme/TECH",
            "assetKeywords": "prueba, proveedor",
        })
        nav.evaluar("document.querySelector('#assetForm button[type=submit]').click();1",
                    esperar_promesa=False)
        ok, detalle = esperar_estado(nav, r"asset\s+creado|asset\s+created", 15)
        comprobar("pero si puede publicar en el conector del nodo", ok, detalle[:200])
    finally:
        nav.cerrar()
        borrar_usuario(base, token_admin, revisor)
        borrar_usuario(base, token_admin, aspirante)

    print(f"\n{'TODO BIEN' if not FALLOS else str(FALLOS) + ' FALLO(S)'}")
    return 1 if FALLOS else 0


if __name__ == "__main__":
    sys.exit(main())
