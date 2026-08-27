# -*- coding: utf-8 -*-
"""Publicar hacia un destino no permitido se dice al publicar.

El conector solo va a buscar datos a los hosts de `ODS_DOWNLOAD_ALLOWED_HOSTS`
—es uno de los dos controles que la especificacion manda conservar—, pero eso
se descubria al final: se publicaba el producto, se le hacia su politica y su
contrato, otro participante lo negociaba, pulsaba descargar, y entonces salia
`asset source host is not allowed`. Cuatro pasos y una negociacion cerrada para
enterarse de que la oferta no servia, y sin decir que host era ni donde se
permite.

Se comprueba al crear el activo, que es cuando se puede arreglar.
"""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
API = (RAIZ / "app" / "onboarding_api.py").read_text(encoding="utf-8")
CONECTOR = (
    RAIZ / "connector" / "src" / "main" / "java" / "org" / "eclipse" / "dataspace"
    / "DataSpaceConnector.java"
).read_text(encoding="utf-8")


def test_el_nodo_comprueba_el_destino_al_crear_el_activo():
    inicio = API.index("def proxy_to_connector(")
    cuerpo = API[inicio: API.index("\n\n\n", inicio)]
    assert "download_host_allowed" in cuerpo, (
        "el paso no comprueba a donde apunta el dato al publicar: el fallo "
        "volveria a aparecer al descargar, cuatro pasos despues"
    )
    assert "download_host_not_allowed" in cuerpo


def test_el_aviso_dice_el_host_y_donde_permitirlo():
    """Un «no permitido» a secas obliga a leer el codigo para saber que tocar."""
    inicio = API.index("def proxy_to_connector(")
    cuerpo = API[inicio: API.index("\n\n\n", inicio)]
    assert "ODS_DOWNLOAD_ALLOWED_HOSTS" in cuerpo, "no dice que variable hay que tocar"
    assert "{host}" in cuerpo, "no dice que host es"


def test_la_misma_regla_en_los_dos_lados():
    """El nodo y el conector tienen que decidir igual.

    Si el nodo dejara pasar lo que el conector rechaza, la comprobacion al
    publicar seria un adorno y el fallo volveria a aparecer al descargar.
    """
    inicio = API.index("def download_host_allowed(")
    cuerpo = API[inicio: API.index("\n\n\n", inicio)]
    assert 'host == permitido or host.endswith("." + permitido)' in cuerpo

    inicio_java = CONECTOR.index("private boolean isAllowedDownloadUri(")
    cuerpo_java = CONECTOR[inicio_java: CONECTOR.index("\n    }", inicio_java)]
    assert 'host.equals(allowedHost) || host.endsWith("." + allowedHost)' in cuerpo_java


def test_el_403_del_conector_nombra_el_host():
    assert '"host", upstreamUri.getHost()' in CONECTOR, (
        "el rechazo del conector no dice que host ha rechazado"
    )
    assert "ODS_DOWNLOAD_ALLOWED_HOSTS" in CONECTOR, (
        "el rechazo del conector no dice donde se permite"
    )


def test_la_lista_sale_del_mismo_sitio_para_los_dos():
    """Una variable, dos lectores. Dos listas distintas se separan."""
    compose = (RAIZ / "docker-compose.yml").read_text(encoding="utf-8")
    para_app = re.search(r"ODS_DOWNLOAD_ALLOWED_HOSTS: \"\$\{ODS_DOWNLOAD_ALLOWED_HOSTS[^\"]*\"", compose)
    para_conector = re.search(r"EDC_DOWNLOAD_ALLOWED_HOSTS: \"\$\{ODS_DOWNLOAD_ALLOWED_HOSTS[^\"]*\"", compose)
    assert para_app, "el nodo no recibe la lista de destinos permitidos"
    assert para_conector, "el conector no recibe la lista de destinos permitidos"
