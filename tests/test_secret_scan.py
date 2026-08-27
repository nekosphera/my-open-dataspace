# -*- coding: utf-8 -*-
"""Ningún secreto nuevo entra en el árbol sin que alguien lo mire.

`.secrets.baseline` guarda los hallazgos ya revisados —los nueve, todos falsos
positivos, explicados uno a uno en `docs/revision/secretos.md`—. Esta prueba
vuelve a barrer y falla si aparece algo que no está ahí.

El fallo que esto evita no es «se cuela una contraseña»: es que la línea base
se convierta en una alfombra. Una lista de excepciones que crece sin que nadie
explique por qué acaba conteniendo el secreto de verdad, y para entonces nadie
la mira.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
BASELINE = RAIZ / ".secrets.baseline"
TRIAJE = RAIZ / "docs" / "revision" / "secretos.md"


def detect_secrets_disponible():
    try:
        subprocess.run(
            [sys.executable, "-m", "detect_secrets", "--version"],
            capture_output=True, check=True, timeout=60,
        )
        return True
    except Exception:  # noqa: BLE001
        return False


requiere_herramienta = pytest.mark.skipif(
    not detect_secrets_disponible(),
    reason="hace falta detect-secrets (python -m pip install detect-secrets)",
)


def test_la_linea_base_existe():
    assert BASELINE.is_file(), (
        "falta .secrets.baseline: el barrido de secretos de la sección 14 "
        "tiene que dejar su resultado guardado"
    )


def test_cada_hallazgo_esta_explicado():
    """Una línea base sin su triaje al lado no dice nada."""
    assert TRIAJE.is_file(), "falta docs/revision/secretos.md"
    triaje = TRIAJE.read_text(encoding="utf-8")
    base = json.loads(BASELINE.read_text(encoding="utf-8"))
    ficheros = {f.replace("\\", "/") for f in base.get("results", {})}
    sin_explicar = [f for f in ficheros if Path(f).name not in triaje]
    assert not sin_explicar, (
        "hay ficheros en la línea base que el triaje no menciona: "
        + ", ".join(sorted(sin_explicar))
    )


# Los dos ficheros que existen para hablar del barrido, y que barrerlos
# duplica cada hallazgo:
#
#   - la línea base guarda los hashes, así que encontrarlos ahí los declara
#     hallazgos nuevos y cada regeneración produce una línea base distinta de
#     la anterior, indefinidamente;
#   - el triaje cita el código que explica, así que cada cita cuenta otra vez.
#
# Excluirlos no esconde nada: lo que citan está barrido en su fichero de
# origen, que es donde importa.
FUERA_DEL_BARRIDO = {".secrets.baseline", "secretos.md"}


def ficheros_versionados():
    salida = subprocess.run(
        ["git", "ls-files"], cwd=RAIZ, capture_output=True, text=True, check=True
    )
    return [
        l for l in salida.stdout.splitlines()
        if l.strip() and Path(l).name not in FUERA_DEL_BARRIDO
    ]


@requiere_herramienta
def test_ningun_hallazgo_fuera_de_la_linea_base():
    salida = subprocess.run(
        [sys.executable, "-m", "detect_secrets", "scan", *ficheros_versionados()],
        cwd=RAIZ, capture_output=True, text=True, timeout=600,
    )
    assert salida.returncode == 0, f"el barrido falló: {salida.stderr[:300]}"

    def claves(informe):
        return {
            (fichero.replace("\\", "/"), h["type"], h["hashed_secret"])
            for fichero, hallazgos in informe.get("results", {}).items()
            for h in hallazgos
        }

    ahora = claves(json.loads(salida.stdout))
    conocidos = claves(json.loads(BASELINE.read_text(encoding="utf-8")))

    nuevos = ahora - conocidos
    assert not nuevos, (
        "Hallazgos que no están en la línea base:\n"
        + "\n".join(f"  {f}  ({tipo})" for f, tipo, _ in sorted(nuevos))
        + "\n\nMíralos uno a uno. Si son falsos positivos, explícalos en "
        "docs/revision/secretos.md y vuelve a generar la línea base con:\n"
        "  python -m detect_secrets scan $(git ls-files) > .secrets.baseline"
    )


@requiere_herramienta
def test_la_linea_base_no_arrastra_hallazgos_que_ya_no_existen():
    """Una excepción que ya no hace falta deja de decir nada y estorba."""
    salida = subprocess.run(
        [sys.executable, "-m", "detect_secrets", "scan", *ficheros_versionados()],
        cwd=RAIZ, capture_output=True, text=True, timeout=600,
    )

    def ficheros(informe):
        return {f.replace("\\", "/") for f in informe.get("results", {})}

    sobran = ficheros(json.loads(BASELINE.read_text(encoding="utf-8"))) - ficheros(
        json.loads(salida.stdout)
    )
    assert not sobran, (
        "la línea base menciona ficheros que ya no dan ningún hallazgo: "
        + ", ".join(sorted(sobran))
        + ". Vuelve a generarla."
    )
