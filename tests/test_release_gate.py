# -*- coding: utf-8 -*-
"""«Si la prueba de extremo a extremo falla, no hay versión.»

Eso es una frase hasta que algo la sostiene. Lo que la sostiene es la forma
del flujo de trabajo: que construir dependa de probar, y que nada tenga
permiso para seguir adelante después de un rojo.

Se rompe de maneras que no dan error y que en una revisión pasan
desapercibidas: un `continue-on-error` puesto para desatascar una publicación
un viernes, un `if: always()` en el trabajo que sube las imágenes, o quitar el
`needs`. Cada una deja el flujo verde y publica una versión que no ha pasado
por la puerta.
"""
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml", reason="hace falta pyyaml para leer los flujos")

RAIZ = Path(__file__).resolve().parents[1]
FLUJOS = RAIZ / ".github" / "workflows"
RELEASE = FLUJOS / "release.yml"
TESTS = FLUJOS / "tests.yml"


def cargar(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_los_dos_flujos_existen():
    assert RELEASE.is_file(), "falta .github/workflows/release.yml"
    assert TESTS.is_file(), "falta .github/workflows/tests.yml"


def test_publicar_empieza_por_probar():
    trabajos = cargar(RELEASE)["jobs"]
    assert "pruebas" in trabajos, "el flujo de publicación no ejecuta las pruebas"
    assert trabajos["pruebas"].get("uses", "").endswith("tests.yml"), (
        "el flujo de publicación tiene que reutilizar tests.yml, no una copia "
        "suya: dos puertas distintas dejan de ser una puerta"
    )


def test_construir_depende_de_probar():
    trabajos = cargar(RELEASE)["jobs"]
    necesita = trabajos["imagenes"].get("needs")
    necesita = [necesita] if isinstance(necesita, str) else (necesita or [])
    assert "pruebas" in necesita, (
        "el trabajo que construye y sube las imágenes no depende de las "
        "pruebas: un rojo no impediría publicar"
    )


def test_la_publicacion_depende_de_las_imagenes():
    trabajos = cargar(RELEASE)["jobs"]
    necesita = trabajos["publicacion"].get("needs")
    necesita = [necesita] if isinstance(necesita, str) else (necesita or [])
    assert "imagenes" in necesita


def test_el_analisis_de_vulnerabilidades_no_bloquea_la_publicacion():
    """Lo que la documentación promete tiene que ser lo que el flujo hace.

    `docs/publicar.md` dice que el análisis no bloquea. Con
    `needs: [imagenes, vulnerabilidades]` sí bloqueaba, y no sólo por
    encontrar algo: cualquier fallo del trabajo lo hacía. En la v0.1.0 la
    acción de trivy no resolvió por una versión que no existe, y la
    publicación se saltó **con las tres imágenes ya subidas** -- imágenes
    publicadas sin publicación que las anuncie.

    El `exit-code: "0"` de trivy sólo evita que falle por encontrar algo. El
    resto lo deciden los `needs`, y ahí es donde tiene que estar la decisión.
    """
    trabajos = cargar(RELEASE)["jobs"]
    necesita = trabajos["publicacion"].get("needs")
    necesita = [necesita] if isinstance(necesita, str) else (necesita or [])
    assert "vulnerabilidades" not in necesita, (
        "la publicación depende del análisis de vulnerabilidades, pero "
        "docs/publicar.md dice que no bloquea. Una de las dos cosas está mal, "
        "y la que se descubre tarde es siempre la del flujo."
    )

    doc = (RAIZ / "docs" / "publicar.md").read_text(encoding="utf-8")
    assert "no bloquea" in doc, (
        "docs/publicar.md ya no dice que el análisis no bloquea: si la "
        "decisión ha cambiado, cámbiala también en los needs"
    )


def test_las_acciones_estan_fijadas_a_una_version_que_existe():
    """Una versión inventada no falla al escribirla: falla al publicar.

    `aquasecurity/trivy-action@0.28.0` no existe -- las etiquetas llevan `v`
    delante-- y eso no se ve hasta que el trabajo intenta resolverla, con la
    versión ya cortada.
    """
    import re

    texto = RELEASE.read_text(encoding="utf-8") + TESTS.read_text(encoding="utf-8")
    usos = re.findall(r"uses:\s*([\w.-]+/[\w.-]+)@([^\s]+)", texto)
    sin_fijar = [f"{a}@{v}" for a, v in usos if v in ("main", "master", "latest")]
    assert not sin_fijar, (
        "acciones sin fijar a una versión: " + ", ".join(sin_fijar)
    )
    # aquasecurity/trivy-action publica con `v` delante; sin ella no resuelve.
    trivy = [v for a, v in usos if a == "aquasecurity/trivy-action"]
    for version in trivy:
        assert version.startswith("v"), (
            f"trivy-action@{version}: sus etiquetas llevan «v» delante y sin "
            "ella la acción no resuelve"
        )


@pytest.mark.parametrize("flujo", [RELEASE, TESTS], ids=lambda p: p.name)
def test_nadie_sigue_adelante_despues_de_un_rojo(flujo):
    """Ni `continue-on-error`, ni un `if: always()` en un trabajo."""
    definicion = cargar(flujo)
    fallos = []
    for nombre, trabajo in definicion["jobs"].items():
        if trabajo.get("continue-on-error"):
            fallos.append(f"el trabajo {nombre} tiene continue-on-error")
        condicion = str(trabajo.get("if", ""))
        if "always()" in condicion:
            fallos.append(f"el trabajo {nombre} corre con if: always()")
        for paso in trabajo.get("steps", []) or []:
            if paso.get("continue-on-error"):
                fallos.append(f"{nombre}: el paso «{paso.get('name', '?')}» tiene continue-on-error")
    assert not fallos, "; ".join(fallos)


def test_el_recorrido_completo_esta_en_la_puerta():
    trabajos = cargar(TESTS)["jobs"]
    assert "extremo-a-extremo" in trabajos, (
        "tests.yml no ejecuta el recorrido completo, así que la frase «si el "
        "E2E falla no hay versión» no la sostiene nada"
    )
    pasos = trabajos["extremo-a-extremo"]["steps"]
    corre = any("golden_path.py" in str(paso.get("run", "")) for paso in pasos)
    assert corre, "el trabajo de extremo a extremo no ejecuta golden_path.py"


def test_los_pasos_de_limpieza_pueden_correr_siempre():
    """`if: always()` en un paso de limpieza es correcto, y hay que distinguirlo.

    Bajar la composición o volcar registros después de un fallo es justamente
    lo que se quiere. Lo que no vale es un trabajo entero condicionado así.
    """
    trabajos = cargar(TESTS)["jobs"]
    pasos = trabajos["extremo-a-extremo"]["steps"]
    con_always = [p for p in pasos if "always()" in str(p.get("if", ""))]
    for paso in con_always:
        run = str(paso.get("run", ""))
        assert "down" in run or "logs" in run, (
            f"el paso «{paso.get('name')}» corre siempre y no es limpieza"
        )


# `id-token` y `packages` son permisos del flujo, no credenciales. Buscarlos
# por «token» los confunde con un secreto y la prueba deja de decir nada.
CLAVES_DE_PERMISO = {"id-token", "packages", "contents", "attestations"}


def test_ninguna_credencial_escrita_en_los_flujos():
    """Los secretos se referencian; nunca se escriben."""
    for flujo in (RELEASE, TESTS):
        for numero, linea in enumerate(flujo.read_text(encoding="utf-8").splitlines(), 1):
            limpia = linea.strip()
            if ":" not in limpia or limpia.startswith("#"):
                continue
            clave, _, valor = limpia.partition(":")
            clave = clave.strip().lower()
            if clave in CLAVES_DE_PERMISO:
                continue
            if not (clave.endswith("password") or clave.endswith("token") or clave.endswith("secret")):
                continue
            # Sin el comentario de final de línea, que no es parte del valor.
            valor = valor.split("#", 1)[0].strip()
            if not valor:
                continue
            assert valor.startswith("${{"), (
                f"{flujo.name}:{numero}: valor literal donde debería ir un "
                f"secreto -> {limpia}"
            )


def test_las_imagenes_salen_para_las_dos_arquitecturas():
    trabajos = cargar(RELEASE)["jobs"]
    pasos = trabajos["imagenes"]["steps"]
    construir = next(
        (p for p in pasos if "build-push-action" in str(p.get("uses", ""))), None
    )
    assert construir, "no hay paso de construcción de imagen"
    plataformas = str(construir["with"].get("platforms", ""))
    assert "linux/amd64" in plataformas and "linux/arm64" in plataformas, (
        f"las imágenes no salen para las dos arquitecturas: {plataformas}"
    )


def test_las_imagenes_se_firman_y_llevan_inventario():
    pasos = cargar(RELEASE)["jobs"]["imagenes"]["steps"]
    texto = str(pasos)
    assert "cosign" in texto, "las imágenes no se firman"
    assert "attest-build-provenance" in texto, "las imágenes no llevan procedencia"
    construir = next(p for p in pasos if "build-push-action" in str(p.get("uses", "")))
    assert construir["with"].get("sbom") is True, "las imágenes no llevan inventario de componentes"
