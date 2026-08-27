# -*- coding: utf-8 -*-
"""El portal habla de este producto, y todos sus enlaces llevan a algún sitio.

Esto lo escribo después de que una captura de pantalla enseñara lo que las
pruebas no vieron: el portal seguía siendo, entero, el del despliegue de
origen. «Espacio de datos de salud urbana», «indicadores sintéticos de calidad
ambiental, confort, afluencia, energía, incendios y radiación
electromagnética», y dos botones grandes que llevaban a páginas que la poda
había borrado.

La poda miró el código —imports, rutas, dependencias— y no miró la prosa. El
barrido de términos prohibidos buscaba `ehds`, `fhir`, `healthdcat`: ninguno
aparece en un párrafo escrito en castellano sobre salud urbana.

Dos comprobaciones, entonces:

1. **Ningún enlace muerto.** Un botón que lleva a un 404 es lo primero que ve
   quien entra, y no hay forma de que un despliegue lo revele antes que un
   usuario.
2. **Ninguna palabra de la vertical podada.** En la prosa, no sólo en los
   identificadores.
"""
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
UI = RAIZ / "app" / "ui"

# Las que se sirven tal cual. Las de la consola las genera la API en el
# arranque, y su plantilla se comprueba aparte.
PAGINAS = sorted(p for p in UI.glob("*.html"))

# Lo que no está en el árbol porque se escribe en el arranque. Enlazarlo no es
# un enlace muerto.
#
# Sin esta lista la prueba pasaba en mi máquina y fallaba en CI, y lo peor no
# era que fallara: es que en local pasaba **por la razón equivocada**, porque
# el fichero había quedado de una ejecución anterior. Una prueba que depende
# de la basura de una ejecución previa no comprueba nada.
GENERADOS_EN_EL_ARRANQUE = {
    # app/tools/render_ui_runtime_config.py, en cada arranque de `app`.
    "runtime-config.js",
}

# La vertical que la sección 9 poda, en las palabras con las que estaba
# escrita —no en los identificadores técnicos, que ya vigila
# test_no_hidden_dependencies.py—.
VERTICAL = [
    "salud urbana",
    "urban health",
    "riesgo sanitario",
    "health risk",
    "indicadores sintéticos",
    "synthetic indicators",
    "centro de mando",
    "command centre",
    "command center",
    "calidad ambiental",
    "radiación electromagnética",
]


def texto(path):
    return path.read_text(encoding="utf-8")


@pytest.mark.parametrize("pagina", PAGINAS, ids=lambda p: p.name)
def test_ningun_enlace_lleva_a_una_pagina_que_no_existe(pagina):
    contenido = texto(pagina)
    destinos = re.findall(r'(?:href|src)="\./([^"?#]+)', contenido)
    rotos = [
        d
        for d in destinos
        if d not in GENERADOS_EN_EL_ARRANQUE and not (UI / d).exists()
    ]
    assert not rotos, (
        f"{pagina.name} enlaza a ficheros que no existen: {', '.join(sorted(set(rotos)))}. "
        "Un botón que lleva a un 404 es lo primero que ve quien entra."
    )


# Todo lo que la interfaz carga: páginas, guiones y hojas de estilo.
FICHEROS_DE_INTERFAZ = sorted(
    p for p in UI.rglob("*") if p.suffix in {".html", ".js", ".css"} and p.is_file()
)


@pytest.mark.parametrize(
    "fichero", FICHEROS_DE_INTERFAZ, ids=lambda p: p.name
)
def test_ningun_import_apunta_a_un_fichero_que_no_existe(fichero):
    """`import()` y `from "..."`, que `href`/`src` no ven.

    Aquí se coló el fallo que más caro salió: la fase 1 borró
    `app/ui/vendor/` por parecer lastre de terceros, y dentro estaba el
    adaptador de Keycloak que **cuatro ficheros importan en tiempo de
    ejecución**. El `import()` falla, alguien se lo traga en un `catch`, y la
    página dice «No se pudo completar el login» sin decir por qué.

    Un `import` roto no da error al construir ni al servir: da error cuando
    alguien intenta entrar.
    """
    contenido = texto(fichero)
    destinos = re.findall(
        r"""(?:import\(|from\s+)["']\.{1,2}/([^"']+)["']""", contenido
    )
    rotos = []
    for destino in destinos:
        candidato = (fichero.parent / destino).resolve()
        if candidato.name in GENERADOS_EN_EL_ARRANQUE:
            continue
        if not candidato.exists():
            rotos.append(destino)
    assert not rotos, (
        f"{fichero.name} importa ficheros que no existen: "
        + ", ".join(sorted(set(rotos)))
        + ". Un import roto sólo da error cuando alguien intenta usar la página."
    )


def test_el_adaptador_de_keycloak_viaja_en_el_arbol():
    """Vendorizado, no desde un CDN.

    La regla de la sección 0b: un nodo tiene que funcionar con lo que hay en
    el árbol. La página de acceso no puede depender de que un tercero esté
    disponible — y menos la página de acceso.
    """
    adaptador = UI / "vendor" / "keycloak.js"
    assert adaptador.is_file(), (
        "falta app/ui/vendor/keycloak.js: sin él ni el acceso ni la consola "
        "pueden autenticar a nadie"
    )
    for fichero in FICHEROS_DE_INTERFAZ:
        contenido = texto(fichero)
        for cdn in ("cdn.jsdelivr", "unpkg.com", "cdnjs.", "//code.jquery"):
            assert cdn not in contenido, (
                f"{fichero.name} carga algo desde {cdn}: eso es una dependencia "
                "de un servicio que quien instala no controla"
            )


@pytest.mark.parametrize("pagina", PAGINAS, ids=lambda p: p.name)
def test_ninguna_pagina_habla_de_la_vertical_podada(pagina):
    contenido = texto(pagina).lower()
    encontradas = [v for v in VERTICAL if v in contenido]
    assert not encontradas, (
        f"{pagina.name} sigue hablando de la vertical que la sección 9 poda: "
        + ", ".join(f"«{v}»" for v in encontradas)
        + ". La poda miró el código y no la prosa."
    )


def test_el_catalogo_del_portal_no_pide_un_servicio_que_no_existe():
    """Leía el catálogo de una gobernanza externa que este producto no tiene.

    El síntoma no era un error: era una tabla que decía «No se encontraron
    productos de datos federados» en un nodo que tenía dos publicados. Un
    fallo que se lee como una respuesta.
    """
    guion = texto(UI / "home-catalog.js")
    assert "/api/v1/catalog" in guion, (
        "el catálogo del portal no lee el catálogo público de los nodos"
    )
    assert "/api/v1/nodes" in guion, (
        "el catálogo del portal no consulta la lista de nodos conocidos"
    )
    for muerto in ("governanceBaseUrls", "/api/governance", "dataspaceGovernanceId"):
        assert muerto not in guion, (
            f"el catálogo del portal todavía usa {muerto}, que se podó"
        )


@pytest.mark.parametrize("generado", sorted(GENERADOS_EN_EL_ARRANQUE))
def test_lo_que_se_da_por_generado_lo_genera_alguien(generado):
    """Una excepción que no corresponde a nada real es un agujero.

    Si el generador deja de escribir ese fichero, la excepción sigue en pie y
    el enlace pasa a estar muerto sin que nadie se entere.
    """
    generador = (RAIZ / "app" / "tools" / "render_ui_runtime_config.py").read_text(
        encoding="utf-8"
    )
    assert generado in generador, (
        f"{generado} está en la lista de generados y nadie lo genera"
    )


def test_un_nodo_remoto_lento_no_deja_el_portal_cargando():
    """Con un plazo por nodo, y todos a la vez.

    En serie y sin plazo, un solo nodo que no cierra la conexión deja la
    página cargando indefinidamente y se lleva por delante la oferta de los
    que sí contestaron.
    """
    guion = texto(UI / "home-catalog.js")
    assert "AbortController" in guion, "no hay plazo por nodo"
    assert "Promise.all" in guion, "los nodos se consultan en serie"
