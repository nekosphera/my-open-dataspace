# -*- coding: utf-8 -*-
"""Toda la configuración sale de un sitio y está declarada.

La regla de la sección 5 es que `.env` es la única ruta de configuración.
Eso se rompe de dos maneras, y ninguna da error al arrancar:

- **Una variable que el código lee y nadie declara.** Quien instala no puede
  saber que existe. Se queda con su valor por omisión para siempre, y cuando
  ese valor no le sirve no hay nada que le diga qué tocar.
- **Una variable declarada que nadie lee.** Ponerla no hace nada. Es peor que
  no ofrecerla: quien la configura cree que ha cambiado algo. `ODS_TLS` estuvo
  así hasta que se le puso el arranque que lo mira.
"""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

FUENTES = [
    RAIZ / "app" / "onboarding_api.py",
    RAIZ / "app" / "tools" / "render_ui_runtime_config.py",
    RAIZ / "app" / "tools" / "seed_demo.py",
]

ENV_EXAMPLE = RAIZ / ".env.example"
COMPOSE = RAIZ / "docker-compose.yml"

# Cableado interno: lo pone la composición y no es cosa de quien instala.
# Cada una tiene que estar puesta en docker-compose.yml, cosa que este mismo
# módulo comprueba abajo.
CABLEADO_INTERNO = {
    "ODS_CONNECTOR_URL",
    # El PostgreSQL del nodo, para crear la base de cada conector. Los fija la
    # composición, que es quien sabe cómo se llaman sus propios contenedores.
    "ODS_DB_CONTAINER",
    "ODS_DB_USER",
    "ODS_DB_NAME",
    # La red y la imagen con las que se levanta el conector de un participante.
    "ODS_DOCKER_NETWORK",
    "ODS_DOCKER_SOCKET",
    "ODS_FILES_DIR",
    "ODS_FUSEKI_URL",
    "ODS_FUSEKI_DATASET",
    "ODS_FUSEKI_ADMIN_USER",
    "ODS_PROFILES_DIR",
    "ODS_SEED_DIR",
    "ODS_CONNECTOR_CLIENT_ID",
    "ODS_AUDIT_SIGNING_KID",
    "ODS_AUDIT_PRIVATE_KEY_FILE",
    "ODS_DCAT_IDENTIFIER_PREFIX",
    "ODS_FEDERATED_IDENTITY_PROVIDERS",
    # Lo fija la imagen todo-en-uno en su propio Dockerfile. No se ofrece en
    # .env.example a proposito: es un interruptor que apaga la autenticacion,
    # y ponerlo en la lista de opciones de una instalacion normal es invitar a
    # que alguien lo pruebe «a ver si asi arranca».
    "ODS_EVALUATION_MODE",
}

# Declaradas para quien instala pero todavía sin consumidor. Vaciar esta lista
# es parte de terminar la fase que las use; tenerla escrita es lo que impide
# que una variable muerta pase inadvertida.
PENDIENTES = {
    # La usa el instalador para crear el administrador (fase 5).
    "ODS_ADMIN_PASSWORD",
}


def leidas_por_el_codigo():
    encontradas = set()
    patron = re.compile(
        r'(?:os\.getenv|os\.environ\.get|env\.get)\(\s*"(ODS_[A-Z0-9_]+)"'
    )
    for fuente in FUENTES:
        encontradas |= set(patron.findall(fuente.read_text(encoding="utf-8")))
    return encontradas


def declaradas_en_env_example():
    return set(
        re.findall(r"^(ODS_[A-Z0-9_]+)=", ENV_EXAMPLE.read_text(encoding="utf-8"), re.M)
    )


def puestas_por_la_composicion():
    texto = COMPOSE.read_text(encoding="utf-8")
    # Tanto `ODS_X: "..."` como `${ODS_X:-...}` cuentan: la primera la fija la
    # composición, la segunda la toma del .env.
    return set(re.findall(r"^\s+(ODS_[A-Z0-9_]+):", texto, re.M)) | set(
        re.findall(r"\$\{(ODS_[A-Z0-9_]+)", texto)
    )


def test_nada_de_lo_que_el_codigo_lee_queda_sin_declarar():
    huerfanas = leidas_por_el_codigo() - declaradas_en_env_example() - CABLEADO_INTERNO
    assert not huerfanas, (
        "Variables que el código lee y que nadie declara: "
        + ", ".join(sorted(huerfanas))
        + ". Quien instala no puede saber que existen. Decláralas en "
        ".env.example, o añádelas a CABLEADO_INTERNO si de verdad las fija la "
        "composición."
    )


def test_el_cableado_interno_lo_pone_la_composicion():
    """Declararla interna no basta: alguien tiene que ponerla de verdad."""
    puestas = puestas_por_la_composicion()
    usadas = leidas_por_el_codigo()
    sin_poner = {
        nombre
        for nombre in CABLEADO_INTERNO & usadas
        if nombre not in puestas
    }
    # Las que el código resuelve solo con un valor por omisión razonable no
    # necesitan estar en la composición; las que apuntan a otro servicio, sí.
    apuntan_a_un_servicio = {
        "ODS_CONNECTOR_URL",
        "ODS_FUSEKI_URL",
        "ODS_FUSEKI_DATASET",
        "ODS_FILES_DIR",
    }
    assert not (sin_poner & apuntan_a_un_servicio), (
        "Cableado interno que apunta a otro servicio y que la composición no "
        "pone: " + ", ".join(sorted(sin_poner & apuntan_a_un_servicio))
    )


def test_nada_declarado_se_queda_sin_consumidor():
    usadas = leidas_por_el_codigo() | puestas_por_la_composicion()
    muertas = declaradas_en_env_example() - usadas - PENDIENTES
    assert not muertas, (
        "Variables declaradas en .env.example que no lee nadie: "
        + ", ".join(sorted(muertas))
        + ". Configurarlas no hace nada, que es peor que no ofrecerlas."
    )


def test_las_pendientes_siguen_pendientes():
    """Si una pendiente ya tiene consumidor, sobra de la lista.

    Una lista de excepciones que nadie limpia deja de decir nada.
    """
    usadas = leidas_por_el_codigo() | puestas_por_la_composicion()
    ya_usadas = PENDIENTES & usadas
    assert not ya_usadas, (
        "Estas ya tienen quien las lea y sobran de PENDIENTES: "
        + ", ".join(sorted(ya_usadas))
    )
