# -*- coding: utf-8 -*-
"""La consola no puede pedir rutas que este producto no sirve.

Esto no es celo: la consola estuvo entera rota por esto y ninguna prueba lo
dijo. Pedia `/api/governance/...` -- un servicio que se quito al separar el
producto de su origen --, `/api/v1/edc/bridge/payloads`, `papers_manifest.json`
y `/api/connector/management/v3/...` contra un paso que solo aceptaba
`/api/connector/v3/...`. Todo daba 404, la consola cargaba con buena cara, y
no se podia leer ni publicar nada. Se veia abriendo un navegador y de ninguna
otra forma, porque las pruebas de API llamaban a las rutas correctas
directamente.

Asi que aqui se comprueba lo unico que se puede comprobar sin navegador: que
cada ruta de este nodo que la interfaz nombra existe en el servidor. El
recorrido de `tests/e2e/navegador_alta_y_acceso.py` comprueba lo demas.
"""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
API = (RAIZ / "app" / "onboarding_api.py").read_text(encoding="utf-8")
UI = RAIZ / "app" / "ui"

# Ficheros de la interfaz que hablan con este nodo.
FUENTES = sorted(
    [p for p in UI.glob("*.js") if p.name != "runtime-config.js"]
    + list(UI.glob("*.html"))
)

# Rutas que la interfaz compone en trozos y no se pueden leer de una pieza.
# Cada una lleva por que se da por buena.
COMPUESTAS = {
    # El paso al conector: la consola le anade `/management/v3/<recurso>` y el
    # propio paso decide que recursos deja pasar, con su lista blanca.
    "/api/connector",
}

# Nombres del proyecto de origen que ya estuvieron aqui y rompieron la consola.
PROHIBIDAS = {
    r"/api/governance": "el servicio de gobernanza externo se quito con el origen",
    r"/api/v1/edc/bridge": "el puente de EDC es del origen y aqui no existe",
    r"papers_manifest\.json": "el manifiesto de papers es del origen",
    r"connector-[123](-en)?\.html": "las paginas connector-N son del origen",
    # Tambien en prosa y en rutas: `Connector-1` aparecia en el texto de la
    # pagina de alta y `/api/connector-1/` en el registro de la publica.
    r"[Cc]onnector-[123]\b": "connector-1, -2 y -3 son del origen; este nodo tiene un conector",
    # Con final de palabra: `dataspace-admins` es un grupo de este producto y
    # empieza igual que `dataspace-a`.
    r"dataspace-[ab]\b": "identificadores de espacios de datos del origen",
}


def lineas_de_codigo(fuente):
    """Las lineas que se ejecutan, sin los comentarios.

    Varias de las rutas que se fueron estan escritas a proposito en el
    comentario que explica por que: borrar la explicacion para que una prueba
    calle seria perder el motivo, que es lo unico que impide que vuelvan.
    """
    for numero, linea in enumerate(fuente.read_text(encoding="utf-8").splitlines(), 1):
        desnuda = linea.strip()
        if desnuda.startswith(("//", "*", "<!--", "#")):
            continue
        yield numero, desnuda


def rutas_de_la_interfaz():
    """Las rutas de este nodo que la interfaz nombra literalmente."""
    encontradas = set()
    for fuente in FUENTES:
        for _, linea in lineas_de_codigo(fuente):
            for cruda in re.findall(r"""["'`](/api/[A-Za-z0-9_./-]*)""", linea):
                # Hasta el primer trozo variable: lo que sigue es un
                # identificador y no forma parte de la ruta.
                limpia = cruda.rstrip("/")
                if limpia:
                    encontradas.add(limpia)
    return encontradas


def rutas_del_servidor():
    """Las rutas que el servidor compara, empiece por donde empiece."""
    servidas = set(re.findall(r'''path\s*==\s*["'](/api/[^"']+)["']''', API))
    servidas |= set(re.findall(r'''path\.startswith\(["'](/api/[^"']+)["']''', API))
    # Tambien las que compara al reves -- `if path != "/api/..."`, el guardia
    # de una sola ruta -- porque servirla es lo que hace justo despues.
    servidas |= set(re.findall(r'''path\s*!=\s*["'](/api/[^"']+)["']''', API))
    servidas |= set(re.findall(r'''CONNECTOR_PROXY_PREFIX = "([^"]+)"''', API))
    return servidas


def test_toda_ruta_que_la_interfaz_pide_existe_en_el_servidor():
    servidas = rutas_del_servidor()
    huerfanas = []
    for ruta in sorted(rutas_de_la_interfaz()):
        if ruta in COMPUESTAS or ruta in servidas:
            continue
        # Vale que el servidor sirva un prefijo suyo: `/api/v1/nodes/<id>` lo
        # atiende `path.startswith("/api/v1/nodes/")`.
        if any(ruta.startswith(s) or s.startswith(ruta + "/") for s in servidas):
            continue
        huerfanas.append(ruta)
    assert not huerfanas, (
        "La interfaz pide rutas que este nodo no sirve: "
        + ", ".join(huerfanas)
        + ". Cada una es un 404 en el navegador de quien use la consola, y no "
        "sale en ninguna prueba de API porque estas llaman a la ruta buena "
        "directamente."
    )


def test_no_vuelven_las_rutas_del_proyecto_de_origen():
    culpables = []
    for fuente in FUENTES:
        for numero, linea in lineas_de_codigo(fuente):
            for aguja, motivo in PROHIBIDAS.items():
                if re.search(aguja, linea):
                    culpables.append(f"{fuente.name}:{numero}: {aguja} ({motivo})")
    assert not culpables, "\n".join(culpables)


def test_el_patron_de_los_nombres_prohibidos_encuentra_de_verdad():
    """Que los patrones sirvan, no solo que existan.

    Escribiendo esta prueba, `\\b` acabo en el fichero como un byte de
    retroceso en vez de como frontera de palabra: el patron no encontraba nada
    nunca, y la prueba pasaba en verde diciendo que no habia restos del
    proyecto de origen cuando los habia. Una prueba que no puede fallar no
    prueba nada, asi que aqui se comprueba que puede.
    """
    ejemplos = {
        r"/api/governance": "await fetch('/api/governance/audit/traces')",
        r"/api/v1/edc/bridge": "post('/api/v1/edc/bridge/payloads', {})",
        r"papers_manifest\.json": "fetch('./papers_manifest.json')",
        r"connector-[123](-en)?\.html": "return '/connector-2.html';",
        r"[Cc]onnector-[123]\b": "<p>Connector-1 revisara tu solicitud</p>",
        r"dataspace-[ab]\b": "const ids = ['dataspace-a', 'dataspace-b'];",
    }
    assert set(ejemplos) == set(PROHIBIDAS), (
        "cada nombre prohibido necesita su ejemplo, o nadie sabra si el patron "
        "encuentra algo"
    )
    for aguja, ejemplo in ejemplos.items():
        assert re.search(aguja, ejemplo), f"el patron {aguja!r} no encuentra {ejemplo!r}"
    # Y que no se lleve por delante lo que sí es de este producto.
    for inocente in ('includes("dataspace-admins")', "id: 'connector-4.html'"):
        for aguja in PROHIBIDAS:
            if aguja == r"connector-[123](-en)?\.html" and "connector-4" in inocente:
                continue
            if aguja == r"dataspace-[ab]\b" and "dataspace-admins" in inocente:
                assert not re.search(aguja, inocente), (
                    "el patron de espacios de datos del origen tacha "
                    "`dataspace-admins`, que es un grupo de este producto"
                )


def test_el_paso_acepta_la_ruta_que_la_consola_compone():
    """`<base>/management/v3/...`, que es la forma de la API de EDC.

    La consola usa la misma forma contra este nodo y contra uno remoto, donde
    `<base>` es la direccion del otro. Si el paso deja de aceptar el
    `management/` de delante, todas sus llamadas vuelven a dar 404.
    """
    inicio = API.index("def proxy_to_connector(")
    cuerpo = API[inicio: API.index("\n\n\n", inicio)]
    assert 'suffix.startswith("management/")' in cuerpo, (
        "el paso al conector ya no acepta `/management/v3/...`, que es lo que "
        "la consola compone: sus llamadas darian 404 otra vez"
    )
