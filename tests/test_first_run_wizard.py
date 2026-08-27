# -*- coding: utf-8 -*-
"""El asistente de primer arranque y el instalador.

Es la funcionalidad que separa un producto que la gente instala de uno que
abandona, así que sus invariantes se comprueban aquí y no a ojo:

- Un nodo sin configurar manda a `/setup`, **salvo** lo que el propio
  asistente necesita para pintarse. Sin esa excepción la hoja de estilo
  también acaba redirigida y la página sale en blanco.
- Configurado, `/setup` deja de existir. Que la página siga en el árbol no
  puede significar que siga sirviéndose.
- El marcador vive en el volumen de estado, no en el árbol: si viviera en el
  árbol, cada actualización de la imagen devolvería el nodo a la pantalla de
  configuración.
- `install.sh` no sobrescribe un `.env` que ya existe. Regenerar sus
  contraseñas deja la base de datos inaccesible.
"""
import importlib.util
import os
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
INSTALL = (RAIZ / "install.sh").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def api(tmp_path_factory):
    """El módulo cargado con su estado en un directorio de usar y tirar."""
    datos = tmp_path_factory.mktemp("ods-state")
    os.environ["ONBOARDING_DATA_DIR"] = str(datos)
    os.environ.setdefault("ODS_ADMIN_EMAIL", "admin@example.org")
    spec = importlib.util.spec_from_file_location(
        "ods_api_setup", RAIZ / "app" / "onboarding_api.py"
    )
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_un_nodo_recien_instalado_no_esta_configurado(api):
    assert api.is_configured() is False


def test_el_marcador_vive_en_el_volumen_de_estado(api):
    """Y no dentro del árbol, que se reemplaza en cada actualización."""
    marcador = Path(api.SETUP_MARKER_FILE)
    assert marcador.parent == Path(api.DATA_DIR)
    assert RAIZ not in marcador.parents, (
        "el marcador de configuración está dentro del árbol: una actualización "
        "de la imagen devolvería el nodo a la pantalla de configuración"
    )


def test_los_ajustes_del_asistente_tambien(api):
    assert Path(api.SITE_OVERRIDES_FILE).parent == Path(api.DATA_DIR)


def test_el_estado_inicial_no_filtra_la_contrasena(api):
    estado = api.setup_state()
    plano = repr(estado).lower()
    for prohibido in ("password", "secret"):
        assert prohibido not in plano, (
            f"setup_state() devuelve algo con «{prohibido}» dentro: la "
            "contraseña no puede salir de aquí"
        )


@pytest.mark.parametrize(
    "payload, esperado",
    [
        ({"orgName": "", "adminEmail": "a@b.org", "adminPassword": "Abcdef1!x"}, "missing_org_name"),
        ({"orgName": "X", "adminEmail": "noesuncorreo", "adminPassword": "Abcdef1!x"}, "invalid_email"),
        ({"orgName": "X", "adminEmail": "a@b.org", "adminPassword": "corta"}, "weak_password"),
        ({"orgName": "X", "adminEmail": "a@b.org", "adminPassword": "sinmayusculas1!"}, "weak_password"),
        ({"orgName": "X", "orgId": "MAYÚSCULAS", "adminEmail": "a@b.org", "adminPassword": "Abcdef1!x"}, "invalid_org_id"),
    ],
    ids=lambda v: v if isinstance(v, str) else "",
)
def test_el_asistente_rechaza_lo_que_tiene_que_rechazar(api, payload, esperado):
    with pytest.raises(ValueError) as fallo:
        api.apply_setup(payload)
    assert str(fallo.value) == esperado


def test_nada_se_guarda_cuando_la_validacion_falla(api):
    """Fallar a mitad dejaría ajustes sin administrador que los use."""
    try:
        api.apply_setup({"orgName": "X", "adminEmail": "mal", "adminPassword": "Abcdef1!x"})
    except ValueError:
        pass
    assert not Path(api.SITE_OVERRIDES_FILE).exists()
    assert not Path(api.SETUP_MARKER_FILE).exists()


def test_las_rutas_del_asistente_no_redirigen_su_propia_hoja_de_estilo():
    """La excepción de la redirección tiene que incluir styles.css."""
    api_txt = (RAIZ / "app" / "onboarding_api.py").read_text(encoding="utf-8")
    match = re.search(r"if not is_configured\(\) and path not in \(([^)]*)\)", api_txt)
    assert match, "no se encontró la condición de redirección a /setup"
    excepciones = set(re.findall(r'"([^"]+)"', match.group(1)))
    assert "/styles.css" in excepciones, (
        "la hoja de estilo del asistente también se redirige: la página sale "
        "en blanco"
    )
    assert "/setup" in excepciones and "/setup.html" in excepciones


# --- install.sh -----------------------------------------------------------


def test_el_instalador_no_sobrescribe_un_env_que_ya_existe():
    assert "if [[ -f \"${ENV_FILE}\" ]]; then" in INSTALL
    # El `cp` del ejemplo tiene que estar en la rama del else, no antes.
    antes_del_cp = INSTALL[: INSTALL.index('cp "${EJEMPLO}" "${ENV_FILE}"')]
    assert antes_del_cp.rstrip().endswith("else"), (
        "install.sh copia .env.example encima del .env existente: se llevaría "
        "por delante las contraseñas del nodo"
    )


def test_el_instalador_solo_genera_las_contrasenas_que_faltan():
    assert 'if [[ -z "$(leer_valor "${ENV_FILE}" "${clave}")" ]]; then' in INSTALL, (
        "install.sh regenera contraseñas sin mirar si ya había: eso deja la "
        "base de datos inaccesible en la segunda ejecución"
    )


def test_el_instalador_no_escribe_ninguna_contrasena_por_omision():
    """Ni una contraseña literal en el guion."""
    sospechosas = re.findall(
        r'fijar_valor\s+"\$\{ENV_FILE\}"\s+(\w*PASSWORD\w*)\s+"([^"$]+)"', INSTALL
    )
    assert not sospechosas, f"contraseñas literales en install.sh: {sospechosas}"


def test_el_instalador_no_deja_el_env_legible_por_todos():
    assert 'chmod 600 "${ENV_FILE}"' in INSTALL


def test_el_instalador_no_afloja_los_destinos_de_descarga():
    """Con dominio se añade ese dominio, nunca un comodín."""
    assert "ODS_DOWNLOAD_ALLOWED_HOSTS" in INSTALL
    for comodin in ('"*"', "'*'", '"0.0.0.0/0"'):
        assert comodin not in INSTALL, (
            f"install.sh pone {comodin} en los destinos permitidos: eso desactiva "
            "uno de los dos controles que la especificación conserva"
        )


def test_el_instalador_no_se_cuelga_sin_terminal():
    """Sin stdin interactivo se toman los valores por omisión y se dice."""
    assert 'if [[ ! -t 0 ]]' in INSTALL, (
        "install.sh preguntaría a un stdin cerrado y se quedaría colgado en CI"
    )
