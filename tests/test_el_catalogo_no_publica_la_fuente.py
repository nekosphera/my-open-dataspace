# -*- coding: utf-8 -*-
"""El catálogo público dice cómo se obtiene un dato, nunca de dónde sale.

`GET /api/v1/catalog` es público y lo lee cualquier nodo. Publicaba el activo
tal cual lo devuelve la API de gestión del conector, con `dataAddress.baseUrl`
y `objectUrl` dentro, y el federador copiaba esa dirección como
`dcat:accessURL`. Con una fuente abierta, eso es una descarga sin contrato
para quien lea el catálogo; con un fichero subido al nodo, era además la
ruta que lo sirve, y Caddy la publicaba.

Aquí se sostienen las tres piezas: el catálogo quita la dirección y pone la
ruta mediada, el federador sólo usa esa ruta, y Caddy no publica los ficheros.
"""
import importlib.util
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
CADDYFILE = (RAIZ / "deploy" / "Caddyfile").read_text(encoding="utf-8")
FEDERADOR = (RAIZ / "federation" / "federator" / "federate-catalogues.sh").read_text(
    encoding="utf-8"
)

FUENTE = "https://datos.ejemplo.org/abierto/aforos.csv"


def cargar_api(monkeypatch, publico):
    monkeypatch.setenv("ODS_PUBLIC_URL", publico)
    spec = importlib.util.spec_from_file_location(
        "onboarding_api_catalogo", RAIZ / "app" / "onboarding_api.py"
    )
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def activo():
    return {
        "@id": "aforos-2024",
        "properties": {
            "dct:title": "Aforos 2024",
            "objectUrl": FUENTE,
            "url": FUENTE,
            "downloadUrl": FUENTE,
        },
        "dataAddress": {"type": "HttpData", "baseUrl": FUENTE},
        "privateProperties": {"clave": "no sale"},
    }


def test_la_oferta_publica_no_lleva_la_direccion_del_dato(monkeypatch):
    api = cargar_api(monkeypatch, "https://nodo.ejemplo.org")
    oferta = api.oferta_publica_del_activo(activo(), "connector-abc")
    assert FUENTE not in repr(oferta), "el catálogo público publica la fuente"
    assert "dataAddress" not in oferta
    assert "privateProperties" not in oferta
    assert oferta["properties"]["dct:title"] == "Aforos 2024"
    assert oferta["properties"]["ods:connectorId"] == "connector-abc"


def test_la_oferta_publica_lleva_la_ruta_mediada(monkeypatch):
    api = cargar_api(monkeypatch, "https://nodo.ejemplo.org/")
    ajeno = api.oferta_publica_del_activo(activo(), "connector-abc")
    assert ajeno["properties"]["ods:accessUrl"] == (
        "https://nodo.ejemplo.org/api/connector/connector-abc"
        "/management/v3/assets/aforos-2024/download"
    )
    propio = api.oferta_publica_del_activo(activo(), api.CONNECTOR_ID)
    assert propio["properties"]["ods:accessUrl"] == (
        "https://nodo.ejemplo.org/api/connector"
        "/management/v3/assets/aforos-2024/download"
    )


def test_sin_direccion_publica_no_se_inventa_una(monkeypatch):
    api = cargar_api(monkeypatch, "")
    oferta = api.oferta_publica_del_activo(activo(), "connector-abc")
    assert "ods:accessUrl" not in oferta["properties"]
    assert FUENTE not in repr(oferta)


def test_la_oferta_publica_no_toca_el_activo_original(monkeypatch):
    """La caché y la API de gestión siguen teniendo el activo entero."""
    api = cargar_api(monkeypatch, "https://nodo.ejemplo.org")
    original = activo()
    api.oferta_publica_del_activo(original, "connector-abc")
    assert original["dataAddress"]["baseUrl"] == FUENTE
    assert original["properties"]["objectUrl"] == FUENTE


@pytest.mark.parametrize("campo", ["objectUrl", "dataAddress.baseUrl"])
def test_el_federador_no_toma_la_direccion_del_dato(campo):
    assert f".properties.{campo}" not in FEDERADOR and f".{campo}" not in FEDERADOR, (
        f"el federador vuelve a leer {campo}: publicaría la fuente como "
        "dcat:accessURL"
    )
    assert '.properties["ods:accessUrl"]' in FEDERADOR


def test_caddy_no_publica_los_ficheros_subidos():
    assert "handle /api/onboarding/assets/*" in CADDYFILE
    bloque = CADDYFILE.split("handle /api/onboarding/assets/*", 1)[1].split("}", 1)[0]
    assert "respond 404" in bloque
    # Y va antes del `handle` general, que lo mandaría a la aplicación.
    assert CADDYFILE.index("handle /api/onboarding/assets/*") < CADDYFILE.index(
        "reverse_proxy app:8092"
    )
