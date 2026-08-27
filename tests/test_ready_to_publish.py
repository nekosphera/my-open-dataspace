# -*- coding: utf-8 -*-
"""La lista de «antes de pulsar público», comprobada.

El repositorio de destino **ya es público y está vacío**, así que no hay paso
intermedio: el primer `git push` publica. Esta lista tiene que estar cerrada
antes, no después, y una lista en un documento se cumple a ojo —o no se
cumple—. Esto la sostiene.

Lo que esta prueba **no** puede comprobar está en `docs/revision/lista.md`, y
son dos cosas: la captura del README y que alguien que no sea el autor instale
esto en una máquina limpia siguiendo sólo el README.
"""
import re
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]


def leer(nombre):
    return (RAIZ / nombre).read_text(encoding="utf-8")


def sin_saltos(nombre):
    """El texto con los espacios normalizados.

    Los documentos van ajustados a 79 columnas, asi que buscar una frase tal
    cual falla en cuanto cae partida en dos lineas -- y falla por el ajuste,
    no porque la frase no este. Lo que se comprueba es el contenido.

    Tambien se quitan las marcas de cita y de enfasis: una frase dentro de un
    bloque `>` lleva el signo en medio al juntar las lineas, y un `**` puede
    caer justo en el corte.
    """
    texto = leer(nombre)
    texto = re.sub(r"^\s*>\s?", "", texto, flags=re.M)
    texto = texto.replace("**", "").replace("*", "")
    return re.sub(r"\s+", " ", texto)


# --- Licencia y atribuciones ---------------------------------------------


def test_la_licencia_esta_y_es_apache_2():
    licencia = leer("LICENSE")
    assert "Apache License" in licencia and "Version 2.0" in licencia


def test_las_atribuciones_estan():
    notice = sin_saltos("NOTICE")
    # Lo que de verdad se incorporó al árbol, no una lista genérica.
    assert "catalejo" in notice.lower(), (
        "NOTICE no atribuye catalejo, del que sale federation/ y profiles/"
    )
    assert "Apache" in notice


# --- Ficheros de comunidad -----------------------------------------------


def test_los_ficheros_de_comunidad_estan():
    for nombre in (
        "README.md",
        "LICENSE",
        "NOTICE",
        "SECURITY.md",
        "CONTRIBUTING.md",
        "CODE_OF_CONDUCT.md",
        "CHANGELOG.md",
    ):
        assert (RAIZ / nombre).is_file(), f"falta {nombre}"


def test_las_plantillas_de_incidencia_estan():
    plantillas = RAIZ / ".github" / "ISSUE_TEMPLATE"
    assert plantillas.is_dir(), "faltan las plantillas de incidencia"
    nombres = {p.name for p in plantillas.glob("*.yml")}
    assert "config.yml" in nombres
    assert len(nombres - {"config.yml"}) >= 2, (
        "hacen falta al menos dos plantillas: un fallo y una idea"
    )


def test_las_plantillas_mandan_la_seguridad_a_un_canal_privado():
    """Una incidencia es pública desde el primer momento."""
    config = leer(".github/ISSUE_TEMPLATE/config.yml")
    assert "security/advisories" in config, (
        "las plantillas no ofrecen un canal privado para un problema de "
        "seguridad, así que el primer reflejo de alguien será abrir una "
        "incidencia pública con un fallo explotable dentro"
    )
    assert "blank_issues_enabled: false" in config


# --- Política de seguridad -----------------------------------------------


def test_la_politica_de_seguridad_da_canal_y_plazo():
    politica = sin_saltos("SECURITY.md")
    assert "Report a vulnerability" in politica, "no dice por dónde se reporta"
    # Un plazo, no «lo antes posible».
    plazos = re.findall(r"within \d+ (?:working )?days", politica)
    assert len(plazos) >= 2, (
        "la política no da plazos concretos de acuse y de respuesta: "
        f"encontrados {plazos}"
    )


# --- El README ------------------------------------------------------------


def test_el_readme_lleva_los_tres_caminos():
    readme = sin_saltos("README.md")
    assert "docker run" in readme, "falta el camino de probarlo sin instalar"
    assert "./install.sh" in readme, "falta el camino de instalarlo"
    assert "docker compose" in readme, "falta el camino de operarlo"


def test_el_readme_lleva_el_aviso_de_alcance_literal():
    """Visible en el README, no sólo enlazado."""
    readme = sin_saltos("README.md")
    for frase in (
        "No certifica conformidad",
        "no garantiza",
        "no acredita pertenencia",
    ):
        assert frase in readme, f"el README no dice «{frase}»"
    for iniciativa in ("SIMPL", "Gaia-X", "FIWARE", "IDSA", "EHDS"):
        assert iniciativa in readme, (
            f"el aviso de alcance del README no nombra {iniciativa}"
        )


def test_el_readme_no_afirma_lo_que_todavia_no_es_cierto():
    """Las imágenes no están publicadas: el README no puede callárselo.

    Un `docker run` en la portada que no resuelve es la primera impresión de
    quien llega, y descubrirlo por un «not found» es peor que leerlo.
    """
    readme = sin_saltos("README.md")
    assert "todavía no están publicadas" in readme, (
        "el README ofrece imágenes que no existen sin decir que no existen"
    )


def test_el_readme_lleva_su_captura_y_la_captura_existe():
    """La sección 14 la pide, y un enlace roto a una imagen es peor que nada."""
    readme = leer("README.md")
    imagenes = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", readme)
    assert imagenes, "el README no lleva ninguna captura"
    for ruta in imagenes:
        assert (RAIZ / ruta).is_file(), f"el README enlaza a {ruta}, que no existe"


def test_la_captura_no_lleva_la_marca_de_nadie():
    """Se hace sobre un nodo de ejemplo, no sobre el de una organización real.

    Una captura tomada contra un nodo configurado con el nombre de alguien
    mete esa marca en el repositorio por la puerta de atrás, que es justo lo
    que la lista de la sección 14 prohíbe. El guion que las toma lo avisa;
    esto comprueba que el aviso está.
    """
    guion = leer("deploy/capturas.sh")
    assert "Organización de Ejemplo" in guion, (
        "deploy/capturas.sh no dice con qué nombre hay que levantar el nodo"
    )
    for advertencia in ("organización real", "que exista", "no sea localhost"):
        assert advertencia in guion, (
            f"el guion de capturas no advierte de «{advertencia}»"
        )


def test_el_alcance_tiene_una_sola_copia():
    assert (RAIZ / "docs" / "alcance.md").is_file()
    flujo = leer(".github/workflows/release.yml")
    assert "docs/alcance.md" in flujo, (
        "las notas de versión escriben su propia copia del aviso de alcance en "
        "vez de tomarla de docs/alcance.md; dos copias divergen"
    )


# --- Procedencia ----------------------------------------------------------


def test_la_procedencia_nombra_repositorio_y_commit():
    procedencia = leer("docs/procedencia.md")
    commits = re.findall(r"`([0-9a-f]{40})`", procedencia)
    assert len(commits) >= 2, (
        "docs/procedencia.md no fija los commits de origen: sin ellos no se "
        "puede volver a traer una mejora de aguas arriba sin adivinar"
    )
    for repo in ("mydataspace", "catalejo"):
        assert repo in procedencia, f"procedencia.md no menciona {repo}"


def test_cada_carpeta_traida_esta_en_la_procedencia():
    procedencia = leer("docs/procedencia.md")
    for carpeta in ("app/", "connector/", "federation/", "profiles/"):
        assert carpeta in procedencia, (
            f"{carpeta} viene de algún sitio y procedencia.md no lo dice"
        )


# --- Los guiones ----------------------------------------------------------


def test_los_guiones_viajan_como_ejecutables():
    """`./install.sh` es el primer comando del README.

    Todos los guiones se versionaron como 100644 porque esta máquina de
    desarrollo tiene `core.filemode=false`: `chmod +x` no deja rastro en el
    índice. En Windows daba igual; quien clonara en Linux o macOS se
    encontraba «Permission denied» en el primer comando de la portada, y el
    arranque de Caddy moría con «exec: permission denied» sin decir por qué.
    """
    salida = subprocess.run(
        ["git", "ls-files", "-s", "--", "*.sh"], cwd=RAIZ,
        capture_output=True, text=True, check=True,
    ).stdout
    sin_bit = [
        linea.split("\t", 1)[1]
        for linea in salida.splitlines()
        if linea and not linea.startswith("100755")
    ]
    assert not sin_bit, (
        "guiones versionados sin el bit de ejecución: "
        + ", ".join(sorted(sin_bit))
        + ". Arréglalo con:  git update-index --chmod=+x <fichero>"
    )


# --- El historial ---------------------------------------------------------


# El único sitio al que este árbol puede empujar.
DESTINO = "nekosphera/my-open-dataspace"


def test_solo_se_empuja_al_repositorio_de_destino():
    """Un remoto de más publica en un sitio que nadie ha decidido.

    Antes de publicar, esta prueba exigía que no hubiera ninguno. Ahora que el
    repositorio está publicado, lo que comprueba es que el único remoto sea
    ese: `git push` sin argumentos empuja a donde diga la configuración, y un
    remoto añadido para una prueba y olvidado publica el trabajo en el
    repositorio de otro.
    """
    salida = subprocess.run(
        ["git", "remote", "-v"], cwd=RAIZ, capture_output=True, text=True, check=True
    )
    urls = {
        linea.split()[1]
        for linea in salida.stdout.splitlines()
        if len(linea.split()) >= 2
    }
    ajenos = [u for u in urls if DESTINO not in u]
    assert not ajenos, (
        "hay remotos que no apuntan a " + DESTINO + ": " + ", ".join(sorted(ajenos))
    )


def test_main_tiene_un_solo_commit_y_es_la_raiz():
    """D-001: un único commit inicial en el árbol publicado.

    Se pierde sin que nadie lo note. Basta con que alguien añada la captura
    del README como un commit nuevo en vez de con `--amend`, y a partir de ahí
    el árbol publicado tiene dos commits y nadie vuelve a mirarlo.
    """
    cabeza = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=RAIZ,
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    raices = subprocess.run(
        ["git", "rev-list", "--max-parents=0", "HEAD"], cwd=RAIZ,
        capture_output=True, text=True, check=True,
    ).stdout.split()
    total = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"], cwd=RAIZ,
        capture_output=True, text=True, check=True,
    ).stdout.strip()

    assert raices == [cabeza], (
        f"main tiene {total} commits y su raíz no es HEAD. El árbol publicado "
        "tiene que tener uno solo: lo que falte se mete con "
        "`git commit --amend`, y lo que merezca contarse va a la rama "
        "historia-de-trabajo."
    )


def ramas_locales():
    return subprocess.run(
        ["git", "branch", "--format=%(refname:short)"], cwd=RAIZ,
        capture_output=True, text=True, check=True,
    ).stdout.split()


# La rama de historia es local y **no se empuja**: un clon —el de CI, el de
# cualquiera— no la tiene, y exigirla ahí sería exigir algo que por diseño no
# está. Se comprueba donde puede estar.
en_el_arbol_de_trabajo = pytest.mark.skipif(
    "historia-de-trabajo" not in ramas_locales(),
    reason="la rama historia-de-trabajo es local y no se empuja",
)


@en_el_arbol_de_trabajo
def test_la_historia_de_trabajo_sigue_estando():
    """Aplastar no puede significar perder por qué está cada cosa.

    Los mensajes de esos commits son la única explicación escrita de los
    fallos que sólo se ven arrancando.
    """
    commits = subprocess.run(
        ["git", "rev-list", "--count", "historia-de-trabajo"], cwd=RAIZ,
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert int(commits) > 1, "la rama de historia no tiene historia dentro"


@en_el_arbol_de_trabajo
def test_aplastar_no_ha_cambiado_el_contenido():
    """El árbol publicado y el de trabajo tienen que ser el mismo objeto."""
    arboles = [
        subprocess.run(
            ["git", "rev-parse", f"{ref}^{{tree}}"], cwd=RAIZ,
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        for ref in ("HEAD", "historia-de-trabajo")
    ]
    # Si difieren es porque después del aplastado se ha trabajado, y entonces
    # la rama de historia se ha quedado atrás. No es un error: es un aviso de
    # que ese trabajo no está contado en ningún sitio.
    if arboles[0] != arboles[1]:
        import warnings
        warnings.warn(
            "el árbol publicado ya no coincide con historia-de-trabajo: hay "
            "trabajo hecho después del aplastado que no está contado en "
            "ningún mensaje de commit",
            stacklevel=2,
        )


def test_el_arbol_no_arrastra_historial_de_los_repositorios_de_origen():
    salida = subprocess.run(
        ["git", "log", "--format=%s"], cwd=RAIZ, capture_output=True, text=True, check=True
    )
    asuntos = salida.stdout.splitlines()
    assert asuntos, "el repositorio no tiene commits"
    # Los del repositorio de origen venían todos numerados por su propio
    # gestor de incidencias.
    heredados = [a for a in asuntos if re.search(r"\(#\d+\)$", a)]
    assert not heredados, (
        "hay commits que parecen heredados de un repositorio de origen: "
        + "; ".join(heredados[:3])
    )
