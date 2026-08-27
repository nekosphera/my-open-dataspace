# -*- coding: utf-8 -*-
"""La imagen todo-en-uno.

Cuatro procesos en un contenedor. Nada de esto da error al construir: la
imagen sale, arranca, el portal contesta 200 — y el producto está roto por
dentro. Lo que sigue son los cuatro fallos que costaron una tarde, cada uno
convertido en una comprobación que se lee en un segundo.

No se prueba levantando la imagen: eso son varios minutos de construcción y no
cabe en la puerta de calidad. Lo hace el recorrido completo, que sí corre
contra un nodo levantado. Aquí se comprueba la forma.
"""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DOCKERFILE = (RAIZ / "Dockerfile").read_text(encoding="utf-8")
ENTRYPOINT = (RAIZ / "deploy" / "allinone-entrypoint.sh").read_text(encoding="utf-8")


def test_el_jre_es_el_mismo_con_el_que_se_compila_el_conector():
    """Debian trae Java 17 y el conector se compila con 21.

    El síntoma era un `UnsupportedClassVersionError` en el registro del
    conector mientras el portal seguía contestando 200: la imagen parecía
    sana.
    """
    compila = re.search(r"FROM eclipse-temurin:(\d+)-jdk", DOCKERFILE)
    assert compila, "no se ve con qué JDK se compila el conector"
    version = compila.group(1)

    assert f"FROM eclipse-temurin:{version}-jre AS jre" in DOCKERFILE, (
        f"el conector se compila con Java {version} pero la imagen no copia "
        f"ese mismo JRE"
    )
    assert "COPY --from=jre /opt/java/openjdk" in DOCKERFILE
    assert "openjdk-17" not in DOCKERFILE, (
        "la imagen instala OpenJDK 17 de Debian, que no puede ejecutar clases "
        "compiladas con 21"
    )


def test_el_vigilante_tumba_el_contenedor():
    """Un `exit` en un subshell mata el subshell, no el contenedor.

    Con eso, el contenedor seguía sirviendo el portal con el conector muerto,
    que es el «medio producto vivo» que el vigilante existe para evitar.
    """
    inicio = ENTRYPOINT.index("vigilar() {")
    fin = ENTRYPOINT.index("vigilar &")
    cuerpo = ENTRYPOINT[inicio:fin]
    assert "kill -TERM" in cuerpo, (
        "el vigilante no le manda ninguna señal al proceso principal: detecta "
        "la caída y no hace nada útil con ella"
    )
    assert "exit 1" not in cuerpo, (
        "el vigilante usa exit dentro de un subshell en segundo plano: mata el "
        "subshell y deja el contenedor en pie"
    )


def test_el_registro_de_postgres_va_donde_postgres_puede_escribir():
    """En el volumen a secas, que es de root, no puede.

    `pg_ctl` se quedaba esperando a un servidor que nunca arrancaba.
    """
    linea = next(l for l in ENTRYPOINT.splitlines() if "pg_ctl" in l and "start" in l)
    assert "${PGDATA}/postgres.log" in linea, (
        f"el registro de PostgreSQL no va dentro de PGDATA: {linea.strip()}"
    )


def test_fuseki_arranca_donde_puede_encontrarse_a_si_mismo():
    """Sin FUSEKI_HOME busca su `webapp` relativa al directorio de trabajo."""
    assert "FUSEKI_HOME=" in ENTRYPOINT, (
        "sin FUSEKI_HOME, Fuseki muere con «Can't find baseResource»"
    )
    assert re.search(r'mkdir -p "\$\{ALMACEN\}"', ENTRYPOINT), (
        "la carpeta del almacén no se crea: `--loc` no la crea y Fuseki dice "
        "«Does not exist» y se muere"
    )
    assert "--tdb2" in ENTRYPOINT, (
        "Fuseki no arranca con TDB2, que es lo que el catálogo consolidado "
        "necesita para poder compactarse sin parar el servicio"
    )


def test_ninguna_suma_de_comprobacion_inventada():
    """Una comprobación que no verifica nada es peor que no tenerla.

    Llegó a haber un `ARG ..._SHA512=` con un hash escrito a mano que no
    correspondía a ningún fichero.
    """
    hashes = re.findall(r"ARG\s+\w*SHA\w*\s*=\s*([0-9a-fA-F]{32,})", DOCKERFILE)
    assert not hashes, (
        "hay sumas escritas a mano en el Dockerfile: se comprueban con la que "
        "publica el origen, no con una copiada"
    )
    if "sha512sum" in DOCKERFILE:
        assert "sha512sum -c" in DOCKERFILE, (
            "la suma se compara a mano en vez de con `sha512sum -c`, que es "
            "quien entiende el formato «<hash>  <fichero>» que publica Apache"
        )


def test_la_imagen_avisa_de_que_no_es_para_produccion():
    """Y lo hace antes de arrancar nada, no en una nota al pie."""
    cabecera = ENTRYPOINT[: ENTRYPOINT.index("mkdir -p")]
    assert "EVALUACION" in cabecera.upper()
    assert "SIN AUTENTICACION" in cabecera.upper(), (
        "el aviso no dice lo único que de verdad importa: que no hay "
        "autenticación"
    )


def test_el_modo_de_evaluacion_no_se_ofrece_como_una_opcion_mas():
    """No aparece en .env.example: es un interruptor que apaga la autenticación.

    Ponerlo en la lista de opciones de una instalación normal es invitar a que
    alguien lo pruebe «a ver si así arranca».
    """
    ejemplo = (RAIZ / ".env.example").read_text(encoding="utf-8")
    assert "ODS_EVALUATION_MODE" not in ejemplo
    assert "ODS_EVALUATION_MODE=true" in DOCKERFILE, (
        "la imagen todo-en-uno no activa el modo de evaluación, así que su "
        "conector rechazará todas las peticiones"
    )


def test_el_modo_de_evaluacion_se_apaga_solo_si_hay_identidad():
    """Heredarlo de una plantilla no puede dejar un nodo sin autenticación."""
    java = (RAIZ / "connector" / "src" / "main" / "java" / "org" / "eclipse"
            / "dataspace" / "DataSpaceConnector.java").read_text(encoding="utf-8")
    inicio = java.index("private final boolean evaluationMode")
    condicion = java[inicio: java.index(";", inicio)]
    assert "KEYCLOAK_JWKS_URL" in condicion, (
        "el modo de evaluación del conector no se apaga cuando hay una "
        "identidad configurada"
    )

    api = (RAIZ / "app" / "onboarding_api.py").read_text(encoding="utf-8")
    inicio = api.index("EVALUATION_MODE = (")
    condicion = api[inicio: api.index("\n)", inicio)]
    assert "ODS_DOMAIN" in condicion, (
        "el modo de evaluación de la aplicación no se apaga cuando hay un "
        "dominio configurado"
    )
