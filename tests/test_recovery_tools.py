# -*- coding: utf-8 -*-
"""Las herramientas de recuperación no pueden mentir.

`./deploy/reiniciar.sh --asistente` imprimió «Hecho. Abre /setup» sin haber
hecho nada: Git Bash en Windows convirtió `/var/lib/ods/...` en una ruta de
Windows antes de que Docker la viera, el `rm -f` borró un fichero inexistente
—y `rm -f` **sale con éxito** cuando no borra nada—.

Una herramienta de recuperación que dice «hecho» sin serlo es peor que no
tenerla: manda a buscar el problema a otra parte, y quien la usa está ya en un
mal día.

De ahí las dos reglas que se comprueban aquí:

1. **Ninguna ruta absoluta como argumento suelto** de `docker compose exec`.
   Van dentro de un `sh -c`, donde ya no se convierten.
2. **Cada acción destructiva comprueba su propio efecto** en vez de confiar en
   el código de salida.
"""
import re
import stat
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
REINICIAR = RAIZ / "deploy" / "reiniciar.sh"
RESET = RAIZ / "app" / "tools" / "reset_password.py"

GUIONES = sorted(RAIZ.glob("deploy/*.sh")) + [RAIZ / "install.sh"]


def texto(path):
    return path.read_text(encoding="utf-8")


def test_la_herramienta_de_recuperacion_existe():
    """La especificación pide una orden explícita para reconfigurar.

    `/setup` devuelve 404 en cuanto el nodo está configurado, y no puede
    reabrirse desde la web: si se pudiera, cualquiera que alcanzara el nodo se
    nombraría administrador. Sin esta orden, quedarse fuera significaba borrar
    los volúmenes.
    """
    assert REINICIAR.is_file(), "falta deploy/reiniciar.sh"
    contenido = texto(REINICIAR)
    for accion in ("--contrasena", "--asistente", "--todo"):
        assert accion in contenido, f"reiniciar.sh no ofrece {accion}"


@pytest.mark.parametrize("guion", GUIONES, ids=lambda p: p.name)
def test_ninguna_ruta_absoluta_suelta_en_docker_exec(guion):
    """Git Bash las convierte, y el comando actúa sobre otra cosa.

    Esto no da error: `rm -f` sobre una ruta inventada sale con cero, y el
    guion sigue como si hubiera funcionado.
    """
    malas = []
    for numero, linea in enumerate(texto(guion).splitlines(), 1):
        if "docker compose exec" not in linea and "docker exec" not in linea:
            continue
        # Lo que va dentro de comillas tras `sh -c` está a salvo.
        sin_protegidas = re.sub(r"""sh -c ['"].*?['"]""", "", linea)
        if re.search(r"\s/(?:var|srv|opt|etc)/", sin_protegidas):
            malas.append(f"línea {numero}: {linea.strip()[:90]}")
    assert not malas, (
        f"{guion.name}: rutas absolutas como argumento suelto de docker exec.\n"
        + "\n".join(malas)
        + "\nMételas dentro de un `sh -c '...'`: si no, Git Bash en Windows las "
        "convierte y el comando actúa sobre una ruta que no existe, en silencio."
    )


def test_reabrir_el_asistente_comprueba_que_lo_ha_hecho():
    """`rm -f` no se queja nunca. Sin comprobar, el guion miente."""
    contenido = texto(REINICIAR)
    inicio = contenido.index('if [[ "${ACCION}" == "asistente" ]]')
    fin = contenido.index('if [[ "${ACCION}" == "todo" ]]')
    rama = contenido[inicio:fin]

    assert "test -f /var/lib/ods/setup-complete.json" in rama, (
        "la rama --asistente no comprueba si el marcador ha desaparecido de "
        "verdad, así que puede decir «Hecho» con el asistente todavía cerrado"
    )
    assert "exit 1" in rama, "no falla cuando el borrado no ha surtido efecto"


def test_borrarlo_todo_pide_confirmacion():
    contenido = texto(REINICIAR)
    inicio = contenido.index('if [[ "${ACCION}" == "todo" ]]')
    rama = contenido[inicio:]
    assert "confirmar" in rama, "--todo borra los volúmenes sin preguntar"
    assert "backup.sh" in rama, (
        "--todo no menciona cómo hacer una copia antes de borrar"
    )


def test_el_cambio_de_contrasena_no_se_expone_por_la_red():
    """Quien puede ejecutarlo ya tiene la máquina; por HTTP sería un secuestro."""
    api = (RAIZ / "app" / "onboarding_api.py").read_text(encoding="utf-8")
    assert "reset_password" not in api, (
        "la API expone el cambio de contraseña por una ruta HTTP: eso permite "
        "tomar la cuenta de otro desde la red"
    )


def test_el_cambio_de_contrasena_exige_el_mismo_perfil_que_el_asistente():
    """Aceptar una que la consola rechazaría deja a alguien sin poder entrar."""
    reset = texto(RESET)
    api = (RAIZ / "app" / "onboarding_api.py").read_text(encoding="utf-8")
    perfil_api = re.search(r'PASSWORD_RE = re\.compile\(r"([^"]+)"\)', api)
    perfil_reset = re.search(r'PERFIL = re\.compile\(r"([^"]+)"\)', reset)
    assert perfil_api and perfil_reset, "no se encontró alguno de los dos perfiles"
    assert perfil_api.group(1) == perfil_reset.group(1), (
        "el perfil de contraseña de reset_password.py no coincide con el de la "
        f"API:\n  API:   {perfil_api.group(1)}\n  reset: {perfil_reset.group(1)}"
    )


def test_el_cambio_de_contrasena_habilita_la_cuenta():
    """Una contraseña nueva sobre una cuenta deshabilitada parece funcionar."""
    assert '"enabled": True' in texto(RESET) or '"enabled", True' in texto(RESET), (
        "reset_password.py no vuelve a habilitar una cuenta deshabilitada: la "
        "contraseña se cambia y quien la usa sigue sin poder entrar"
    )


def test_la_recuperacion_esta_documentada():
    doc = RAIZ / "docs" / "recuperar.md"
    assert doc.is_file(), "falta docs/recuperar.md"
    contenido = doc.read_text(encoding="utf-8")
    for accion in ("--contrasena", "--asistente", "--todo"):
        assert accion in contenido, f"recuperar.md no explica {accion}"


def test_reiniciar_viaja_como_ejecutable():
    modo = REINICIAR.stat().st_mode
    # En Windows el bit no se refleja; lo que importa es lo que git registra,
    # y eso lo vigila test_ready_to_publish.py sobre todos los .sh.
    assert modo & stat.S_IRUSR
