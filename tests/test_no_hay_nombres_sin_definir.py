# -*- coding: utf-8 -*-
"""Ninguna funcion puede nombrar algo que no existe.

Python no se queja hasta que la linea se ejecuta. Borrando codigo muerto se
fueron por delante dos constantes de nivel superior que estaban escritas entre
las funciones que se retiraban -- `CONNECTOR_GROUP_PATTERN` y
`STARTUP_REPAIRS` --, el fichero seguia compilando, y el fallo aparecio horas
despues: la primera al reconciliar grupos, la segunda tumbando `/health` con
un `NameError` en cada peticion.

Esto lo dice antes de arrancar nada. Recorre el arbol contando que nombres hay
en cada ambito -- parametros, asignaciones, importaciones, `global`, capturas
de `except`, comprensiones -- y avisa de los que no salen de ninguna parte.
"""
import ast
import builtins
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
FUENTES = sorted(
    list((RAIZ / "app").glob("*.py"))
    + list((RAIZ / "app" / "tools").glob("*.py"))
)
INCORPORADOS = set(dir(builtins)) | {"__file__", "__name__", "__doc__", "__spec__"}


def nombres_atados(nodo, incluir_hijos=True):
    """Los nombres que un trozo de arbol deja atados en su ambito."""
    atados = set()
    for hijo in ast.walk(nodo) if incluir_hijos else [nodo]:
        if isinstance(hijo, ast.Name) and isinstance(hijo.ctx, (ast.Store, ast.Del)):
            atados.add(hijo.id)
        elif isinstance(hijo, (ast.Import, ast.ImportFrom)):
            for alias in hijo.names:
                atados.add((alias.asname or alias.name).split(".")[0])
        elif isinstance(hijo, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            atados.add(hijo.name)
        elif isinstance(hijo, ast.ExceptHandler) and hijo.name:
            atados.add(hijo.name)
        elif isinstance(hijo, (ast.Global, ast.Nonlocal)):
            atados.update(hijo.names)
    return atados


def parametros(funcion):
    a = funcion.args
    nombres = {p.arg for p in a.posonlyargs + a.args + a.kwonlyargs}
    if a.vararg:
        nombres.add(a.vararg.arg)
    if a.kwarg:
        nombres.add(a.kwarg.arg)
    return nombres


def revisar(fuente):
    arbol = ast.parse(fuente.read_text(encoding="utf-8"), filename=str(fuente))
    globales = nombres_atados(arbol, incluir_hijos=True) | INCORPORADOS
    sueltos = []

    def mirar(funcion, visibles):
        propios = visibles | parametros(funcion) | nombres_atados(funcion)
        for hijo in ast.walk(funcion):
            if isinstance(hijo, ast.Name) and isinstance(hijo.ctx, ast.Load):
                if hijo.id not in propios:
                    sueltos.append((fuente.name, hijo.lineno, hijo.id))
            elif isinstance(hijo, (ast.FunctionDef, ast.AsyncFunctionDef)) and hijo is not funcion:
                mirar(hijo, propios)

    for nodo in arbol.body:
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
            mirar(nodo, globales)
        elif isinstance(nodo, ast.ClassDef):
            for miembro in nodo.body:
                if isinstance(miembro, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    mirar(miembro, globales | nombres_atados(nodo))
    return sueltos


@pytest.mark.parametrize("fuente", FUENTES, ids=lambda f: f.name)
def test_ninguna_funcion_nombra_algo_que_no_existe(fuente):
    sueltos = revisar(fuente)
    assert not sueltos, "\n".join(
        f"{nombre}:{linea}: «{quien}» no está definido en ningún sitio"
        for nombre, linea, quien in sueltos
    )


def test_la_revision_encuentra_de_verdad(tmp_path):
    """Que la comprobacion pueda fallar.

    Una que no puede fallar no prueba nada, y este fichero existe justamente
    porque una prueba en verde convivio con dos nombres rotos.
    """
    roto = tmp_path / "roto.py"
    roto.write_text(
        "SI_EXISTE = 1\n\n\ndef f(a):\n    b = a + SI_EXISTE\n    return b + NO_EXISTE\n",
        encoding="utf-8",
    )
    hallados = [nombre for _, _, nombre in revisar(roto)]
    assert hallados == ["NO_EXISTE"], hallados
