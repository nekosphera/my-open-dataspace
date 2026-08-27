# -*- coding: utf-8 -*-
"""Nada de lo que el contenedor ejecuta puede llevar CRLF.

Un guion con finales de linea de Windows llega al contenedor con `set -euo
pipefail\r` y bash lo rechaza con «pipefail: invalid option name». El
federador se paso asi una tarde entera devolviendo ok=False sin decir por
que: el guion fallaba en su primera linea.

`.gitattributes` lo garantiza para lo que entra al repositorio, pero no
reescribe lo que ya esta en disco ni lo que alguien copie a mano. Esta prueba
mira el arbol de trabajo, que es lo que acaba dentro de la imagen.
"""
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]

DIRECTORIOS_IGNORADOS = {
    ".git", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache",
    "target", ".venv", "venv",
}

# Lo que se ejecuta, se interpreta o se monta dentro de un contenedor.
EJECUTABLES = {".sh", ".py", ".yml", ".yaml", ".json", ".jsonld", ".ttl", ".sql"}
POR_NOMBRE = {"Caddyfile", "Dockerfile", ".env.example", "entrypoint.sh"}


def ficheros_ejecutables():
    for path in sorted(RAIZ.rglob("*")):
        if not path.is_file():
            continue
        if any(parte in DIRECTORIOS_IGNORADOS for parte in path.parts):
            continue
        if path.suffix in EJECUTABLES or path.name in POR_NOMBRE:
            yield path


@pytest.mark.parametrize(
    "path", list(ficheros_ejecutables()), ids=lambda p: p.relative_to(RAIZ).as_posix()
)
def test_sin_finales_de_linea_de_windows(path):
    contenido = path.read_bytes()
    assert b"\r\n" not in contenido, (
        f"{path.relative_to(RAIZ).as_posix()} lleva CRLF. Dentro del contenedor "
        "esto falla en la primera linea y el mensaje no dice que el problema "
        "sea el final de linea."
    )


def test_los_guiones_declaran_su_interprete():
    """Un .sh sin shebang se ejecuta con el shell que toque, no con el suyo."""
    sin_shebang = []
    for path in RAIZ.rglob("*.sh"):
        if any(parte in DIRECTORIOS_IGNORADOS for parte in path.parts):
            continue
        primera = path.read_bytes().split(b"\n", 1)[0]
        if not primera.startswith(b"#!"):
            sin_shebang.append(path.relative_to(RAIZ).as_posix())
    assert not sin_shebang, "Guiones sin shebang: " + ", ".join(sin_shebang)
