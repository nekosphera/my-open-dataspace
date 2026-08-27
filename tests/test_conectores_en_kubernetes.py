# -*- coding: utf-8 -*-
"""El conector de cada participante, también en Kubernetes.

En Kubernetes no hay socket de Docker. Sin otra forma de levantarlos, aprobar
un alta fallaba siempre. `app/conectores_k8s.py` los levanta por la API del
cluster; aquí se sostiene lo que no se ve arrancando:
que el despacho elige ese módulo, que lo que crea se llama y se etiqueta como
en Docker -- el resto del nodo les habla por ese nombre --, que no se publica
fuera del cluster, que el SQL corre con la contraseña del Secret y no en
claro, y que el manifiesto le da a `app` los permisos justos para hacerlo.
"""
import importlib
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "app"))
MANIFIESTO = (RAIZ / "k8s" / "manifiestos.yaml").read_text(encoding="utf-8")


@pytest.fixture
def k8s(monkeypatch):
    monkeypatch.setenv("ODS_ORQUESTADOR", "kubernetes")
    import conectores
    import conectores_k8s

    importlib.reload(conectores_k8s)
    importlib.reload(conectores)
    yield conectores, conectores_k8s
    monkeypatch.setenv("ODS_ORQUESTADOR", "docker")
    importlib.reload(conectores)


def test_el_despacho_elige_kubernetes(k8s):
    conectores, modulo = k8s
    for funcion in ("crear", "disponible", "ejecutar_en", "listar", "retirar"):
        assert getattr(conectores, funcion) is getattr(modulo, funcion), funcion
    # Lo que no cambia sigue siendo de conectores: el nombre y la espera.
    assert conectores.nombre_contenedor("connector-abc") == "ods-connector-abc"


def test_por_omision_sigue_siendo_docker(monkeypatch):
    monkeypatch.delenv("ODS_ORQUESTADOR", raising=False)
    import conectores

    importlib.reload(conectores)
    assert conectores.ORQUESTADOR == "docker"
    assert conectores.crear.__module__ == "conectores"


def test_sin_cuenta_de_servicio_no_esta_disponible(k8s, monkeypatch):
    _, modulo = k8s
    monkeypatch.setattr(modulo, "CUENTA", "/no/existe")
    assert modulo.disponible() is False


def test_el_conector_se_llama_y_se_etiqueta_como_en_docker(k8s):
    _, modulo = k8s
    despliegue, servicio = modulo.manifiestos_del_conector(
        "connector-abc", {"EDC_CONNECTOR_ID": "connector-abc", "DATABASE_PASSWORD": "x"}
    )
    assert despliegue["metadata"]["name"] == "ods-connector-abc"
    assert servicio["metadata"]["name"] == "ods-connector-abc"
    etiquetas = despliegue["spec"]["template"]["metadata"]["labels"]
    assert etiquetas[modulo.ETIQUETA] == "true"
    assert etiquetas[modulo.ETIQUETA_NODO] == "connector-abc"
    contenedor = despliegue["spec"]["template"]["spec"]["containers"][0]
    assert {"name": "EDC_CONNECTOR_ID", "value": "connector-abc"} in contenedor["env"]
    assert 8080 in [p["port"] for p in servicio["spec"]["ports"]]


def test_el_conector_no_se_publica_fuera_del_cluster(k8s):
    _, modulo = k8s
    _, servicio = modulo.manifiestos_del_conector("connector-abc", {})
    assert servicio["spec"].get("type", "ClusterIP") == "ClusterIP"


def test_un_identificador_raro_no_crea_nada(k8s):
    _, modulo = k8s
    with pytest.raises(ValueError):
        modulo.crear("../../kube-system", {})
    with pytest.raises(ValueError):
        modulo.retirar("connector-ABC; rm")


def test_el_sql_lleva_la_contrasena_del_secret_no_en_claro(k8s):
    _, modulo = k8s
    trabajo = modulo.trabajo_de_una_vez("ods-sql-1", ["psql", "-U", "dataspace", "-c", "SELECT 1"])
    contenedor = trabajo["spec"]["template"]["spec"]["containers"][0]
    entorno = {e["name"]: e for e in contenedor["env"]}
    assert entorno["PGHOST"]["value"] == "postgres"
    assert "value" not in entorno["PGPASSWORD"]
    assert entorno["PGPASSWORD"]["valueFrom"]["secretKeyRef"]["name"] == "ods-secret"
    assert contenedor["command"] == ["psql", "-U", "dataspace", "-c", "SELECT 1"]
    assert trabajo["spec"]["backoffLimit"] == 0


def test_el_manifiesto_da_a_app_su_cuenta_y_el_orquestador():
    bloque_app = MANIFIESTO.split("metadata: { name: app, namespace: my-open-dataspace }", 1)[1]
    bloque_app = bloque_app.split("\n---", 1)[0]
    assert "serviceAccountName: ods-app" in bloque_app
    assert "ODS_ORQUESTADOR, value: kubernetes" in bloque_app


def test_los_permisos_son_de_su_espacio_de_nombres_y_nada_mas():
    assert "kind: Role\n" in MANIFIESTO
    assert "kind: ClusterRole" not in MANIFIESTO
    assert "ClusterRoleBinding" not in MANIFIESTO
    reglas = MANIFIESTO.split("kind: Role\n", 1)[1].split("\n---", 1)[0]
    for recurso in ("deployments", "services", "pods/log", "jobs"):
        assert recurso in reglas, recurso
    for de_mas in ("secrets", "\"*\"", "escalate", "bind", "exec"):
        assert de_mas not in reglas, de_mas
