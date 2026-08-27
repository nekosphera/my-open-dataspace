# -*- coding: utf-8 -*-
"""El punto SPARQL está cerrado por omisión, y abierto sólo deja leer.

Abrirlo publica el catálogo consolidado entero —incluida la oferta de los
demás nodos— a cualquiera que lo pida, así que la decisión de abrirlo es de
quien instala y la de qué se puede hacer con él, no.

La comprobación de «esto es sólo una lectura» es el sitio evidente donde
equivocarse en las dos direcciones: rechazar una consulta legítima porque
lleva la palabra «insert» dentro de un literal, o dejar pasar un DELETE
escondido detrás de un PREFIX o de un comentario.
"""
import importlib.util
import os
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]


def cargar_api(sparql_publico):
    """Carga el módulo con ODS_SPARQL_PUBLIC puesto: se lee al importar."""
    anterior = os.environ.get("ODS_SPARQL_PUBLIC")
    os.environ["ODS_SPARQL_PUBLIC"] = sparql_publico
    os.environ.setdefault("ODS_ADMIN_EMAIL", "admin@example.org")
    os.environ.setdefault("ONBOARDING_DATA_DIR", str(RAIZ / ".pytest_cache" / "ods"))
    try:
        spec = importlib.util.spec_from_file_location(
            "ods_api_sparql", RAIZ / "app" / "onboarding_api.py"
        )
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
        return modulo
    finally:
        if anterior is None:
            os.environ.pop("ODS_SPARQL_PUBLIC", None)
        else:
            os.environ["ODS_SPARQL_PUBLIC"] = anterior


API = cargar_api("false")


def test_cerrado_por_omision():
    assert API.SPARQL_PUBLIC is False


def test_se_abre_por_configuracion():
    assert cargar_api("true").SPARQL_PUBLIC is True


LECTURAS = [
    "SELECT ?s WHERE { ?s ?p ?o }",
    "  select * where { ?s ?p ?o }",
    "ASK { ?s ?p ?o }",
    "DESCRIBE <urn:ods:dataset:x>",
    "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }",
    # El caso que la primera versión rompía: la almohadilla del IRI no es un
    # comentario, y comérsela dejaba la consulta irreconocible.
    "PREFIX dcat: <http://www.w3.org/ns/dcat#> SELECT * WHERE { ?s a dcat:Dataset }",
    "PREFIX a: <urn:a#>\nPREFIX b: <urn:b#>\nSELECT * WHERE { ?s ?p ?o }",
    "BASE <urn:ods:> SELECT * WHERE { ?s ?p ?o }",
    "# una consulta comentada\nSELECT * WHERE { ?s ?p ?o }",
    # «insert» dentro de un literal no convierte una lectura en una escritura.
    'SELECT ?s WHERE { ?s ?p "insert data" }',
    'SELECT ?s WHERE { ?s ?p "drop graph <urn:x>" }',
]

ESCRITURAS = [
    "INSERT DATA { <a> <b> <c> }",
    "DELETE WHERE { ?s ?p ?o }",
    "DROP GRAPH <urn:ods:catalog/connector>",
    "CLEAR ALL",
    "LOAD <http://example.org/datos.ttl>",
    "CREATE GRAPH <urn:x>",
    # Detrás de un prefijo.
    "PREFIX x: <urn:x#> DROP GRAPH <urn:ods:catalog/connector>",
    # Detrás de un comentario que dice «select».
    "# select\nINSERT DATA { <a> <b> <c> }",
    "PREFIX d: <http://www.w3.org/ns/dcat#>\n# select\nDELETE WHERE { ?s ?p ?o }",
    "",
    "   ",
    None,
]


@pytest.mark.parametrize("consulta", LECTURAS)
def test_una_lectura_pasa(consulta):
    assert API.sparql_query_is_read_only(consulta), (
        f"rechazada una consulta de lectura legítima: {consulta!r} "
        f"(primera palabra detectada: {API.sparql_first_keyword(consulta)!r})"
    )


@pytest.mark.parametrize("consulta", ESCRITURAS, ids=lambda c: repr(c)[:40])
def test_una_escritura_no_pasa(consulta):
    assert not API.sparql_query_is_read_only(consulta), (
        f"ha pasado algo que no es una lectura: {consulta!r}"
    )
