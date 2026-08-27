# -*- coding: utf-8 -*-
"""El conector de cada participante, en Kubernetes.

Lo mismo que `conectores.py` hace con el socket de Docker, contra la API del
cluster: un Deployment y un Service por participante, con el mismo nombre que
tendria su contenedor (`ods-connector-...`), de modo que el resto del nodo le
habla igual -- `http://ods-connector-...:8080` -- en los dos sitios.

Se habla con la API con `urllib` y la cuenta de servicio del pod: no se anade
ninguna dependencia. Lo que esa cuenta puede hacer lo dice el Role de
k8s/manifiestos.yaml, y se limita al espacio de nombres del nodo: es bastante
menos que el socket de Docker, que es root en la maquina.

`ejecutar_en` es la pieza que no tiene equivalente directo. Con Docker, la
base de datos de cada conector se crea con un `docker exec psql` dentro del
contenedor de PostgreSQL. Aqui la misma orden corre en un Job de una sola vez
con la imagen de PostgreSQL, apuntando al servicio `postgres` con PGHOST y
PGPASSWORD: las ordenes no cambian, y su salida se lee del registro del pod.
"""
from __future__ import annotations

import json
import os
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

CUENTA = "/var/run/secrets/kubernetes.io/serviceaccount"
API = os.getenv("ODS_K8S_API", "https://kubernetes.default.svc").rstrip("/")
CONNECTOR_IMAGE = os.getenv("ODS_IMAGE_CONNECTOR", "myopendataspace/connector:dev")
PSQL_IMAGE = os.getenv("ODS_K8S_PSQL_IMAGE", "postgres:16-alpine")
DB_HOST = os.getenv("ODS_DB_HOST", "postgres")
DB_SECRET = os.getenv("ODS_K8S_DB_SECRET", "ods-secret")
DB_SECRET_KEY = os.getenv("ODS_K8S_DB_SECRET_KEY", "ODS_DB_PASSWORD")

# Las mismas etiquetas que en Docker: es lo que permite listar y retirar solo
# lo que este modulo ha creado. Como claves de Kubernetes son validas tal cual.
ETIQUETA = "org.myopendataspace.connector"
ETIQUETA_NODO = "org.myopendataspace.node.connector"
NOMBRE_VALIDO = re.compile(r"^connector-[a-z0-9-]{1,40}$")
PUERTOS = (8080, 9090, 9091)


class KubernetesNoDisponible(RuntimeError):
    """La API no contesta, o este pod no tiene cuenta de servicio."""


def _leer(fichero):
    with open(os.path.join(CUENTA, fichero), encoding="utf-8") as f:
        return f.read().strip()


def espacio():
    return os.getenv("ODS_K8S_NAMESPACE", "").strip() or _leer("namespace")


def _pedir(metodo, ruta, cuerpo=None, crudo=False, contenido="application/json"):
    try:
        token = _leer("token")
        contexto = ssl.create_default_context(cafile=os.path.join(CUENTA, "ca.crt"))
    except OSError as exc:
        raise KubernetesNoDisponible(
            "este pod no tiene cuenta de servicio de Kubernetes: sin ella no "
            "puede levantar el conector de un participante"
        ) from exc
    datos = json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None
    peticion = urllib.request.Request(f"{API}{ruta}", data=datos, method=metodo)
    peticion.add_header("Authorization", f"Bearer {token}")
    peticion.add_header("Accept", "application/json")
    if datos is not None:
        peticion.add_header("Content-Type", contenido)
    try:
        with urllib.request.urlopen(peticion, context=contexto, timeout=30) as r:
            texto = r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        detalle = exc.read()[:300].decode("utf-8", "replace")
        raise KubernetesNoDisponible(f"kubernetes {metodo} {ruta} -> {exc.code}: {detalle}") from exc
    except (OSError, ValueError) as exc:
        raise KubernetesNoDisponible(str(exc)) from exc
    if crudo:
        return texto
    return json.loads(texto) if texto.strip() else {}


def _no_existe(exc):
    return "-> 404" in str(exc)


def disponible():
    """Si se puede levantar conectores. No lanza: se pregunta y se sigue."""
    try:
        _pedir("GET", f"/apis/apps/v1/namespaces/{espacio()}/deployments?limit=1")
        return True
    except (KubernetesNoDisponible, OSError):
        return False


def _nombre(connector_id):
    import conectores  # aqui y no arriba: conectores importa este modulo

    return conectores.nombre_contenedor(connector_id)


def manifiestos_del_conector(connector_id, entorno):
    """El Deployment y el Service de un participante. Sin efectos: se prueba."""
    nombre = _nombre(connector_id)
    etiquetas = {"app": nombre, ETIQUETA: "true", ETIQUETA_NODO: connector_id}
    despliegue = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": nombre, "labels": etiquetas},
        "spec": {
            "replicas": 1,
            "selector": {"matchLabels": {"app": nombre}},
            "template": {
                "metadata": {"labels": etiquetas},
                "spec": {
                    "containers": [{
                        "name": "connector",
                        "image": CONNECTOR_IMAGE,
                        "imagePullPolicy": "IfNotPresent",
                        "env": [{"name": k, "value": str(v)} for k, v in entorno.items()],
                        "ports": [{"containerPort": p} for p in PUERTOS],
                    }],
                },
            },
        },
    }
    # Sin NodePort ni LoadBalancer: al conector de un participante se llega
    # por el paso del nodo, nunca desde fuera del cluster.
    servicio = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {"name": nombre, "labels": etiquetas},
        "spec": {
            "selector": {"app": nombre},
            "ports": [{"name": f"p{p}", "port": p} for p in PUERTOS],
        },
    }
    return despliegue, servicio


def listar():
    """Los conectores de participante que hay en el espacio de nombres."""
    selector = urllib.parse.quote(f"{ETIQUETA}=true")
    lista = _pedir("GET", f"/apis/apps/v1/namespaces/{espacio()}/deployments?labelSelector={selector}")
    salida = {}
    for d in lista.get("items", []):
        meta = d.get("metadata", {})
        cid = (meta.get("labels") or {}).get(ETIQUETA_NODO, "")
        if cid:
            listos = int((d.get("status") or {}).get("readyReplicas") or 0)
            salida[cid] = {
                "id": str(meta.get("uid", ""))[:12],
                "estado": "running" if listos > 0 else "starting",
                "nombre": meta.get("name", ""),
            }
    return salida


def crear(connector_id, entorno, red=None):  # noqa: ARG001 - la red es cosa de Docker
    """Levanta el conector de un participante. Idempotente.

    Si ya existe no se toca -- volver a crearlo no pierde datos, que viven en
    PostgreSQL, pero no hace falta --; solo se asegura de que tenga su replica.
    """
    if not NOMBRE_VALIDO.match(connector_id):
        raise ValueError(f"identificador de conector no valido: {connector_id!r}")
    ns = espacio()
    nombre = _nombre(connector_id)
    despliegue, servicio = manifiestos_del_conector(connector_id, entorno)

    creado = False
    try:
        _pedir("GET", f"/apis/apps/v1/namespaces/{ns}/deployments/{nombre}")
        _pedir(
            "PATCH", f"/apis/apps/v1/namespaces/{ns}/deployments/{nombre}",
            {"spec": {"replicas": 1}}, contenido="application/merge-patch+json",
        )
    except KubernetesNoDisponible as exc:
        if not _no_existe(exc):
            raise
        _pedir("POST", f"/apis/apps/v1/namespaces/{ns}/deployments", despliegue)
        creado = True
    try:
        _pedir("GET", f"/api/v1/namespaces/{ns}/services/{nombre}")
    except KubernetesNoDisponible as exc:
        if not _no_existe(exc):
            raise
        _pedir("POST", f"/api/v1/namespaces/{ns}/services", servicio)
    return {"creado": creado, "nombre": nombre}


def retirar(connector_id):
    """Borra el Deployment y el Service de un conector. No toca su base de datos."""
    if not NOMBRE_VALIDO.match(connector_id):
        raise ValueError(f"identificador de conector no valido: {connector_id!r}")
    ns = espacio()
    nombre = _nombre(connector_id)
    habia = False
    for ruta in (
        f"/apis/apps/v1/namespaces/{ns}/deployments/{nombre}",
        f"/api/v1/namespaces/{ns}/services/{nombre}",
    ):
        try:
            _pedir("DELETE", ruta)
            habia = True
        except KubernetesNoDisponible as exc:
            if not _no_existe(exc):
                raise
    return habia


def trabajo_de_una_vez(nombre, orden):
    """El Job que ejecuta `orden` contra PostgreSQL. Sin efectos: se prueba."""
    return {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {"name": nombre, "labels": {ETIQUETA + ".tarea": "true"}},
        "spec": {
            "backoffLimit": 0,
            "ttlSecondsAfterFinished": 300,
            "template": {
                "metadata": {"labels": {ETIQUETA + ".tarea": "true"}},
                "spec": {
                    "restartPolicy": "Never",
                    "containers": [{
                        "name": "orden",
                        "image": PSQL_IMAGE,
                        "imagePullPolicy": "IfNotPresent",
                        "command": list(orden),
                        "env": [
                            {"name": "PGHOST", "value": DB_HOST},
                            {"name": "PGPASSWORD", "valueFrom": {"secretKeyRef": {
                                "name": DB_SECRET, "key": DB_SECRET_KEY,
                            }}},
                        ],
                    }],
                },
            },
        },
    }


def ejecutar_en(contenedor, orden, segundos=180):  # noqa: ARG001 - siempre es PostgreSQL
    """Ejecuta `orden` contra PostgreSQL en un Job y devuelve (codigo, salida).

    En Docker se ejecuta dentro del contenedor que se nombre; aqui el unico que
    se usa es el de la base de datos, y la orden llega al servicio `postgres`
    por PGHOST. La salida mezcla stdout y stderr, igual que en Docker.
    """
    ns = espacio()
    nombre = f"ods-sql-{int(time.time() * 1000) % 10**10}-{os.getpid() % 1000}"
    _pedir("POST", f"/apis/batch/v1/namespaces/{ns}/jobs", trabajo_de_una_vez(nombre, orden))
    try:
        fin = time.time() + segundos
        selector = urllib.parse.quote(f"job-name={nombre}")
        while time.time() < fin:
            pods = _pedir("GET", f"/api/v1/namespaces/{ns}/pods?labelSelector={selector}").get("items", [])
            for pod in pods:
                for estado in (pod.get("status") or {}).get("containerStatuses") or []:
                    terminado = (estado.get("state") or {}).get("terminated")
                    if terminado:
                        salida = _pedir(
                            "GET", f"/api/v1/namespaces/{ns}/pods/{pod['metadata']['name']}/log",
                            crudo=True,
                        )
                        return int(terminado.get("exitCode") or 0), salida
            time.sleep(1)
        raise KubernetesNoDisponible(f"la orden en {nombre} no termino en {segundos} s")
    finally:
        try:
            _pedir("DELETE", f"/apis/batch/v1/namespaces/{ns}/jobs/{nombre}?propagationPolicy=Background")
        except KubernetesNoDisponible:
            pass
