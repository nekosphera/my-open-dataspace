# -*- coding: utf-8 -*-
"""Borrarlo todo tiene que llevarse también los conectores de los participantes.

Los levanta el nodo a demanda, así que no están en la composición: Compose no
los conoce y `docker compose down -v` los deja en pie, apuntando a una base de
datos que acaba de desaparecer. Quien pide una instalación limpia se encuentra
contenedores viejos girando contra la nada.

Se reconocen por su etiqueta y no por su nombre, que es lo que garantiza que la
orden no toca ningún otro contenedor de la máquina.
"""
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
GUION = (RAIZ / "deploy" / "reiniciar.sh").read_text(encoding="utf-8")
MODULO = (RAIZ / "app" / "conectores.py").read_text(encoding="utf-8")


def rama_de_borrarlo_todo():
    inicio = GUION.index('if [[ "${ACCION}" == "todo" ]]')
    return GUION[inicio:]


def test_el_borrado_completo_retira_los_conectores_de_los_participantes():
    rama = rama_de_borrarlo_todo()
    assert "docker compose down -v" in rama
    assert "org.myopendataspace.connector=true" in rama, (
        "`--todo` no retira los conectores de los participantes: Compose no los "
        "conoce, así que sobreviven al borrado y quedan apuntando a una base "
        "que ya no existe"
    )


def test_se_retiran_por_etiqueta_y_no_por_nombre():
    """Por etiqueta: un filtro por nombre podría llevarse algo ajeno."""
    rama = rama_de_borrarlo_todo()
    assert "--filter 'label=org.myopendataspace.connector=true'" in rama


def test_la_etiqueta_es_la_que_el_nodo_pone():
    """La que se borra y la que se pone tienen que ser la misma.

    Si se separaran, el borrado dejaría de encontrar nada y no lo diría: la
    orden acabaría con éxito y los contenedores seguirían ahí.
    """
    assert 'ETIQUETA = "org.myopendataspace.connector"' in MODULO
    assert "org.myopendataspace.connector=true" in rama_de_borrarlo_todo()
