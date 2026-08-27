# -*- coding: utf-8 -*-
"""La superficie de administración del conector no se publica.

La composición expone un único puerto, el de Caddy, y Caddy no tiene ninguna
ruta hacia el conector. Lo que la consola usa es un paso —`/api/connector`—
que vive en `app`, reenvía el token de quien llama tal cual y sólo deja pasar
los cuatro recursos que la consola necesita.

Esto importa porque el paso es, por construcción, un agujero potencial: si
alguien lo convierte en un reenvío de todo, o le añade una credencial propia
«para que funcione», la API de administración del conector queda publicada
con un rodeo y nada lo diría.
"""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
API = (RAIZ / "app" / "onboarding_api.py").read_text(encoding="utf-8")
CADDYFILE = (RAIZ / "deploy" / "Caddyfile").read_text(encoding="utf-8")
COMPOSE = (RAIZ / "docker-compose.yml").read_text(encoding="utf-8")


def test_caddy_no_enruta_hacia_el_conector():
    """Ni una directiva de Caddy puede apuntar al conector."""
    destinos = re.findall(r"reverse_proxy\s+(\S+)", CADDYFILE)
    culpables = [d for d in destinos if d.startswith("connector")]
    assert not culpables, (
        "Caddy enruta hacia el conector: " + ", ".join(culpables) + ". "
        "Eso publica su API de administración en internet."
    )


def test_el_conector_no_publica_puertos():
    """El servicio `connector` no puede tener `ports:` en la composición."""
    bloque = COMPOSE[COMPOSE.index("\n  connector:"):]
    siguiente = re.search(r"\n  [a-z][a-z0-9-]*:", bloque[1:])
    if siguiente:
        bloque = bloque[: siguiente.start() + 1]
    assert "ports:" not in bloque, (
        "El servicio connector publica puertos en la máquina anfitriona: su "
        "API de administración queda accesible saltándose Caddy."
    )


def test_el_paso_solo_deja_los_recursos_de_la_consola():
    """Una lista blanca, no un reenvío de todo."""
    match = re.search(r"CONNECTOR_PROXY_ALLOWED = \((.*?)\)", API, re.S)
    assert match, "no existe la lista blanca del paso al conector"
    permitidos = set(re.findall(r'"([^"]+)"', match.group(1)))
    assert permitidos == {
        "assets",
        "policydefinitions",
        "contractdefinitions",
        "negotiations",
    }, (
        f"la lista blanca del paso ha cambiado: {sorted(permitidos)}. "
        "Añadir un recurso aquí publica esa parte de la API de administración."
    )


def test_el_paso_no_lleva_credenciales_propias():
    """Reenvía el token de quien llama; no pone uno suyo.

    Si el paso obtuviera su propio token, cualquiera que alcance `app`
    operaría el conector con los permisos de la cuenta de servicio, y el RBAC
    del conector dejaría de significar nada.
    """
    inicio = API.index("def proxy_to_connector(")
    fin = API.index("\n\n\n", inicio)
    cuerpo = API[inicio:fin]
    assert 'handler.headers.get("Authorization"' in cuerpo, (
        "el paso no lee el token de quien llama"
    )
    for prohibido in ("connector_service_token", "get_admin_token", "client_secret"):
        assert prohibido not in cuerpo, (
            f"el paso usa {prohibido}: estaría concediendo permisos propios en "
            "vez de reenviar los de quien llama"
        )
