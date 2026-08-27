# -*- coding: utf-8 -*-
"""Los datos de ejemplo tienen que llegar a quien clona el repositorio.

`seed/manifest.json` nombra un fichero por producto. Si esos ficheros no
viajan —porque una regla de `.gitignore` se los lleva por delante, o porque
alguien anade una entrada al manifiesto y olvida el CSV— un nodo recien
instalado publica dos activos cuya descarga da 404, que es peor que no
publicar ninguno: parece que funciona.

La regla que lo provoco fue `data/` sin anclar. Sin la barra de delante casa
con cualquier carpeta llamada asi a cualquier profundidad, y `seed/data/`
dejo de versionarse sin que nada lo dijera.
"""
import json
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
MANIFIESTO = RAIZ / "seed" / "manifest.json"


def manifiesto():
    return json.loads(MANIFIESTO.read_text(encoding="utf-8"))


def datasets():
    return manifiesto().get("datasets", [])


def test_hay_datos_de_ejemplo():
    assert datasets(), "seed/manifest.json no declara ningun producto de datos"


@pytest.mark.parametrize("dataset", datasets(), ids=lambda d: d["dct:identifier"])
def test_el_fichero_del_producto_existe(dataset):
    nombre = dataset.get("file", "")
    assert nombre, f"{dataset['dct:identifier']} no dice de que fichero sale"
    assert (RAIZ / "seed" / nombre).is_file(), (
        f"{dataset['dct:identifier']} apunta a seed/{nombre}, que no existe"
    )


@pytest.mark.parametrize("dataset", datasets(), ids=lambda d: d["dct:identifier"])
def test_el_fichero_del_producto_no_esta_ignorado(dataset):
    """Existir en disco no basta: tiene que estar versionado."""
    ruta = f"seed/{dataset['file']}"
    resultado = subprocess.run(
        ["git", "check-ignore", "-q", ruta], cwd=RAIZ, capture_output=True
    )
    # check-ignore devuelve 0 cuando el fichero SI esta ignorado.
    assert resultado.returncode != 0, (
        f"{ruta} esta en .gitignore: quien clone el repositorio no lo recibira "
        "y su descarga dara 404"
    )


@pytest.mark.parametrize("dataset", datasets(), ids=lambda d: d["dct:identifier"])
def test_cada_producto_declara_su_politica_y_su_contrato(dataset):
    """Un activo sin politica no se puede negociar, y sin negociar no se descarga."""
    policy_ids = {p.get("id") for p in manifiesto().get("policies", [])}
    assert dataset.get("ods:policyId") in policy_ids, (
        f"{dataset['dct:identifier']} referencia una politica que el manifiesto no declara"
    )
    assert dataset.get("ods:contractId"), (
        f"{dataset['dct:identifier']} no declara contrato: no se podra negociar"
    )
