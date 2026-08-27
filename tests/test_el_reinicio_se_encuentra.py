# -*- coding: utf-8 -*-
"""El guion de recuperacion tiene que estar donde se le busca.

Quien instala escribe `./install.sh` en la raiz. Cuando algo va mal escribe
`./reiniciar.sh` en el mismo sitio, y lo que se encontraba era

    ./reiniciar.sh: No such file or directory

porque el guion vivia solo en `deploy/`. Y desde dentro de `deploy/` corria,
pero sin argumentos imprimia la ayuda y salia con exito, que se lee como «ha
corrido y no ha hecho nada».

Es el peor momento para un tropiezo de estos: se llega aqui cuando ya no se
puede entrar en el nodo.
"""
import os
import shutil
import subprocess

import pytest

from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
RAIZ_SH = RAIZ / "reiniciar.sh"
DEPLOY_SH = RAIZ / "deploy" / "reiniciar.sh"


def test_esta_en_la_raiz_y_lleva_al_de_verdad():
    assert RAIZ_SH.is_file(), (
        "no hay `reiniciar.sh` en la raiz: quien no puede entrar en su nodo lo "
        "busca donde escribio `./install.sh`"
    )
    texto = RAIZ_SH.read_text(encoding="utf-8")
    assert "deploy/reiniciar.sh" in texto, "el de la raiz no lleva al de deploy/"
    assert '"$@"' in texto, "el de la raiz no pasa los argumentos"


def test_los_dos_son_ejecutables_en_el_indice():
    """En el indice de git, no en el disco.

    En Windows `core.filemode=false` hace que `chmod +x` no llegue al indice, y
    quien clone en Linux se encuentra un «Permission denied». Ya paso con
    `install.sh`.
    """
    if not (RAIZ / ".git").exists():
        pytest.skip("sin repositorio git")
    salida = subprocess.run(
        ["git", "ls-files", "-s", "reiniciar.sh", "deploy/reiniciar.sh"],
        cwd=RAIZ, capture_output=True, text=True, check=True,
    ).stdout
    modos = {linea.split()[3]: linea.split()[0] for linea in salida.splitlines() if linea}
    assert modos, "git no conoce los guiones de reinicio"
    for ruta, modo in modos.items():
        assert modo == "100755", f"{ruta} esta como {modo}: no se puede ejecutar al clonar"


def test_la_ayuda_no_manda_a_un_camino_que_no_existe():
    """La ayuda dice el camino que se ha escrito, no uno fijo.

    Decia siempre `./deploy/reiniciar.sh`, que desde dentro de `deploy/` no
    existe: quien leia la ayuda ahi copiaba una orden que no funciona.
    """
    texto = DEPLOY_SH.read_text(encoding="utf-8")
    assert "${YO}" in texto, "la ayuda tiene el camino escrito a mano"
    inicio = texto.index("uso() {")
    fin = texto.index("AYUDA\n}", inicio)
    cuerpo = texto[inicio:fin]
    assert "./deploy/reiniciar.sh" not in cuerpo, (
        "la ayuda vuelve a nombrar un camino fijo"
    )


@pytest.mark.skipif(not shutil.which("bash"), reason="hace falta bash")
def test_sin_accion_no_parece_que_haya_funcionado():
    """Sin decirle que hacer, sale con error y dice por que.

    Salir con 0 despues de imprimir la ayuda se lee como «ha corrido»; y quien
    lo ejecuta esta buscando arreglar algo, no leer.
    """
    r = subprocess.run(
        # Ruta relativa con `cwd`: en Windows, el bash de Git no entiende una
        # ruta `C:\...` como argumento y contesta «No such file or directory».
        ["bash", "reiniciar.sh"], cwd=RAIZ, capture_output=True, text=True,
        env={**os.environ, "LC_ALL": "C.UTF-8"},
    )
    assert r.returncode != 0, "salir con 0 hace pensar que ha hecho algo"
    salida = r.stdout + r.stderr
    assert "--contrasena" in salida and "--todo" in salida, "no ensena las opciones"
    assert "No has dicho" in salida, "no dice por que no ha hecho nada"
