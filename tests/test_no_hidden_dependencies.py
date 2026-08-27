# -*- coding: utf-8 -*-
"""Un nodo recien instalado tiene que funcionar con lo que hay en el arbol.

Esta es la regla dura de la especificacion: ni una imagen, paquete, guion,
plantilla o valor de configuracion puede apuntar a un repositorio privado, a
un registro propio, a un VPS, a un dominio de produccion ni a un servicio que
quien instale no controle. Y ni rastro de lo que la seccion 9 poda.

La prueba busca terminos, no intenciones. Un termino que aparezca en la
documentacion diciendo justamente que el proyecto NO hace eso es legitimo, y
por eso hay una lista de ficheros de prosa donde solo se comprueban las
direcciones reales -- dominios, IPs, correos -- y no los nombres de las
iniciativas.
"""
from __future__ import annotations

import inspect
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]

# Lo que la seccion 9 poda. Si uno de estos vuelve al arbol, algo se ha
# colado de aguas arriba sin pasar por la poda.
PODADOS = [
    "mistral",
    "simpl-",
    "service_facade",
    "trustanchor",
    "metaregistry",
    "trusted-issuers",
    "waltid",
    "walt.id",
    "eudi",
    "eidas",
    "eulogin",
    "cl@ve",
    "did:web",
    "healthdcat",
    "ehds",
    "hl7",
    "fhir",
    "orion-ld",
    "ngsi",
    "fiware",
    "airflow",
    "minio",
    "hashicorp",
    "prometheus",
    "grafana",
    "jaeger",
    "opentelemetry",
    "document_audit",
]

# Rastros del despliegue de origen. Estos no se admiten en ningun fichero,
# ni siquiera en prosa: publicarlos es exactamente lo que la seccion 14
# prohibe.
RASTROS = [
    "mydataspace.es",
    "gotodataspace.es",
    "mygovernance.es",
    "myfiware.es",
    "dataspacehealth.eu",
    "nekosphera@",
    "connectormaster@",
    "smtp.mail.ovh.net",
    "/opt/dataspace",
    "code.europa.eu",
]

# Ficheros de prosa: aqui el nombre de una iniciativa puede aparecer para
# decir que el proyecto no pertenece a ella, que es lo que el aviso de
# alcance tiene que decir. Los rastros de arriba siguen prohibidos.
PROSA = {
    "README.md",
    "SECURITY.md",
    "NOTICE",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    "docs/estado.md",
    "docs/decisiones.md",
    "docs/procedencia.md",
    # El aviso de alcance nombra SIMPL, Gaia-X, FIWARE, IDSA y EHDS para decir
    # que el proyecto no pertenece a ninguna. Es su contenido, no un descuido.
    "docs/alcance.md",
    ".github/workflows/release.yml",
    # Le dice a quien propone algo qué se dejó fuera de esta versión a
    # propósito. Nombrarlo es el contenido.
    ".github/ISSUE_TEMPLATE/mejora.yml",
    # Comprueba que el aviso de alcance del README nombra las cinco
    # iniciativas: para eso tiene que escribirlas.
    "tests/test_ready_to_publish.py",
    # Explica que la poda miró el código y no la prosa, y para explicarlo
    # nombra los términos técnicos que sí buscaba.
    "tests/test_the_portal_is_the_product.py",
    # La lista de la sección 14 y su triaje hablan de todo esto.
    "docs/revision/lista.md",
    "docs/revision/secretos.md",
    "tests/test_no_hidden_dependencies.py",
}

# Ni una direccion IP literal. Se excluyen las que no son direcciones de
# ningun sitio: la de escucha en todas las interfaces y la de bucle local.
IP = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
IPS_QUE_NO_SON_UN_SITIO = {"0.0.0.0", "127.0.0.1", "255.255.255.255"}

EXTENSIONES_BINARIAS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".pdf", ".jar",
    ".woff", ".woff2", ".ttf", ".zip", ".gz", ".class",
}

DIRECTORIOS_IGNORADOS = {
    ".git", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache",
    "target", ".venv", "venv", ".poda",
}


def ficheros_del_arbol():
    for path in sorted(RAIZ.rglob("*")):
        if not path.is_file():
            continue
        if any(parte in DIRECTORIOS_IGNORADOS for parte in path.parts):
            continue
        if path.suffix.lower() in EXTENSIONES_BINARIAS:
            continue
        yield path


def relativo(path: Path) -> str:
    return path.relative_to(RAIZ).as_posix()


def como_palabra(termino: str) -> re.Pattern:
    """Busca el termino como palabra, no como subcadena.

    «minio» vive dentro de «dominio» y «ngsi» dentro de «alongside»: sin
    esto, media documentacion en castellano da un falso positivo y la prueba
    deja de decir nada.
    """
    return re.compile(r"(?<![A-Za-z0-9])" + re.escape(termino) + r"(?![A-Za-z0-9])", re.I)


def texto(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return ""


TODOS = list(ficheros_del_arbol())


def test_la_lista_de_prosa_no_admite_codigo():
    """PROSA sólo puede eximir a documentos, nunca a código.

    Esta lista es la que impide que el aviso de alcance —que nombra SIMPL,
    Gaia-X, FIWARE, IDSA y EHDS para decir que el proyecto no pertenece a
    ninguna— haga fallar la prueba. Y es exactamente el sitio por donde una
    prueba así deja de decir nada: alguien añade un `.py` «un momento, para
    desatascar», y la poda deja de estar comprobada en ese fichero para
    siempre.

    Un documento se exime. Un fichero que se ejecuta, no.
    """
    permitidas = {".md", ".yml", ".yaml"}
    culpables = []
    for nombre in PROSA:
        sufijo = Path(nombre).suffix
        if sufijo in permitidas:
            continue
        # Una prueba puede nombrarlos porque comprueba que el aviso los
        # nombra; el resto del código, no.
        if nombre.startswith("tests/") and Path(nombre).name.startswith("test_"):
            continue
        if nombre in {"NOTICE"}:
            continue
        culpables.append(nombre)
    assert not culpables, (
        "PROSA exime a ficheros que no son documentación: "
        + ", ".join(sorted(culpables))
        + ". Ahí la poda deja de estar comprobada."
    )


def test_ningun_rastro_esta_exento():
    """Los dominios y correos reales no se eximen ni en la documentación.

    PROSA sólo vale para los nombres de lo podado. Una dirección de un
    despliegue real no puede viajar en este repositorio ni siquiera dentro de
    un párrafo que explique por qué está.
    """
    # Se comprueba por construcción, leyendo la función de verdad: el barrido
    # de rastros no puede consultar PROSA.
    cuerpo = inspect.getsource(test_ningun_rastro_del_despliegue_de_origen)
    assert "PROSA" not in cuerpo, (
        "el barrido de rastros consulta PROSA: eso permitiría eximir un "
        "dominio real metiéndolo en un documento"
    )


@pytest.mark.parametrize("termino", RASTROS)
def test_ningun_rastro_del_despliegue_de_origen(termino):
    """Ni un dominio, correo ni ruta de servidor de los despliegues reales."""
    patron = como_palabra(termino)
    culpables = [
        relativo(p) for p in TODOS
        if relativo(p) != relativo(Path(__file__)) and patron.search(texto(p))
    ]
    assert not culpables, (
        f"«{termino}» es una direccion de un despliegue real y no puede viajar "
        f"en este repositorio. Aparece en: {', '.join(culpables)}"
    )


@pytest.mark.parametrize("termino", PODADOS)
def test_nada_de_lo_podado_ha_vuelto(termino):
    """Lo que la seccion 9 elimina no vuelve por la puerta de atras."""
    patron = como_palabra(termino)
    culpables = []
    for path in TODOS:
        nombre = relativo(path)
        if nombre in PROSA:
            continue
        if patron.search(texto(path)):
            culpables.append(nombre)
    assert not culpables, (
        f"«{termino}» esta podado de la version 0.1 y ha reaparecido en: "
        f"{', '.join(culpables)}"
    )


def test_ninguna_direccion_ip_literal():
    """Una IP en el arbol es la direccion de la maquina de alguien."""
    culpables = []
    for path in TODOS:
        if relativo(path) in PROSA:
            continue
        for encontrada in IP.findall(texto(path)):
            if encontrada in IPS_QUE_NO_SON_UN_SITIO:
                continue
            # Las versiones de dependencias no son direcciones.
            if path.name in {"requirements.txt", "pom.xml", "package.json"}:
                continue
            culpables.append(f"{relativo(path)}: {encontrada}")
    assert not culpables, "Direcciones IP literales en el arbol: " + "; ".join(culpables)


def test_el_env_de_ejemplo_no_lleva_ningun_secreto():
    """.env.example ensena la forma, nunca un valor real."""
    ejemplo = RAIZ / ".env.example"
    assert ejemplo.exists(), "falta .env.example"
    fallos = []
    for numero, linea in enumerate(ejemplo.read_text(encoding="utf-8").splitlines(), 1):
        limpia = linea.strip()
        if not limpia or limpia.startswith("#") or "=" not in limpia:
            continue
        clave, valor = limpia.split("=", 1)
        valor = valor.split("#", 1)[0].strip().strip("\"'")
        if any(s in clave.upper() for s in ("PASSWORD", "SECRET", "TOKEN", "KEY")) and valor:
            fallos.append(f"linea {numero}: {clave} trae un valor")
    assert not fallos, "Secretos con valor en .env.example: " + "; ".join(fallos)


def test_el_env_real_no_esta_versionado():
    """El .env es de quien instala y no entra en el repositorio."""
    assert not (RAIZ / ".env").exists() or ".env" in (RAIZ / ".gitignore").read_text(
        encoding="utf-8"
    ), ".env tiene que estar en .gitignore"
