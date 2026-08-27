# -*- coding: utf-8 -*-
"""Un conector de verdad por participante: su contenedor, su base, su puerto.

Aprobar un alta levanta una instancia EDC para esa persona. No comparte proceso
con nadie: tiene su contenedor, su base de datos dentro del mismo PostgreSQL y
su identificador, y el nodo le habla por su nombre de contenedor en la red
interna.

Se habla con el demonio de Docker por su socket, con `urllib` sobre un socket
de dominio: no se anade ninguna dependencia para esto.

Que el socket este montado en `app` es lo que hace posible levantar
contenedores desde dentro, y **es acceso equivalente a root en la maquina**:
quien alcance este proceso puede pedirle al demonio un contenedor privilegiado
o el disco del anfitrion montado. El `:ro` del montaje no lo limita -- solo
impide reescribir el fichero del socket --, asi que no hay que confiar en el.

Lo unico que reduce el riesgo es lo que hace este modulo: crear, listar y
retirar solo lo que el mismo etiqueta, y nunca lo que venga de fuera.
"""
from __future__ import annotations

import http.client
import json
import os
import re
import socket
import time
import urllib.parse

DOCKER_SOCKET = os.getenv("ODS_DOCKER_SOCKET", "/var/run/docker.sock")
# La imagen y la red del nodo, que la composicion le pasa: un contenedor no
# puede adivinar en que proyecto de Docker Compose vive.
CONNECTOR_IMAGE = os.getenv("ODS_IMAGE_CONNECTOR", "myopendataspace/connector:dev")
DOCKER_NETWORK = os.getenv("ODS_DOCKER_NETWORK", "").strip()
# Cada conector lleva esta etiqueta. Es lo que permite listarlos y retirarlos
# sin tocar nada mas de la maquina.
ETIQUETA = "org.myopendataspace.connector"
ETIQUETA_NODO = "org.myopendataspace.node"

NOMBRE_VALIDO = re.compile(r"^connector-[a-z0-9-]{1,40}$")


class DockerNoDisponible(RuntimeError):
    """El demonio no contesta, o el socket no esta montado."""


class _ConexionSocket(http.client.HTTPConnection):
    """HTTP sobre el socket de dominio del demonio."""

    def __init__(self, ruta):
        super().__init__("localhost")
        self.ruta = ruta

    def connect(self):
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(30)
        s.connect(self.ruta)
        self.sock = s


def _pedir(metodo, ruta, cuerpo=None):
    if not os.path.exists(DOCKER_SOCKET):
        raise DockerNoDisponible(
            f"no hay socket de Docker en {DOCKER_SOCKET}: sin el, este nodo no "
            "puede levantar el conector de un participante"
        )
    conexion = _ConexionSocket(DOCKER_SOCKET)
    try:
        datos = json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None
        cabeceras = {"Content-Type": "application/json"} if datos else {}
        conexion.request(metodo, ruta, body=datos, headers=cabeceras)
        respuesta = conexion.getresponse()
        crudo = respuesta.read()
        if respuesta.status >= 400:
            raise DockerNoDisponible(
                f"docker {metodo} {ruta} -> {respuesta.status}: {crudo[:300].decode('utf-8', 'replace')}"
            )
        return json.loads(crudo) if crudo.strip() else {}
    except (OSError, ValueError) as exc:
        raise DockerNoDisponible(str(exc)) from exc
    finally:
        conexion.close()


def disponible():
    """Si se puede levantar conectores. No lanza: se pregunta y se sigue."""
    try:
        _pedir("GET", "/version")
        return True
    except DockerNoDisponible:
        return False


def nombre_contenedor(connector_id):
    return f"ods-{connector_id}"


def nombre_base(connector_id):
    """La base de datos de este conector. Un nombre valido para PostgreSQL."""
    return connector_id.replace("-", "_")


def listar():
    """Los conectores de participante que hay levantados en esta maquina."""
    # Codificado: el filtro es un JSON con llaves, comillas y espacios, y una
    # URL no los admite en crudo.
    filtro = urllib.parse.quote(json.dumps({"label": [f"{ETIQUETA}=true"]}))
    contenedores = _pedir("GET", f"/containers/json?all=true&filters={filtro}")
    salida = {}
    for c in contenedores:
        cid = (c.get("Labels") or {}).get(ETIQUETA_NODO + ".connector", "")
        if cid:
            salida[cid] = {
                "id": c.get("Id", "")[:12],
                "estado": c.get("State", ""),
                "nombre": (c.get("Names") or [""])[0].lstrip("/"),
            }
    return salida


def crear(connector_id, entorno, red=None):
    """Levanta el conector de un participante. Idempotente.

    Si ya existe se arranca por si estaba parado y se devuelve tal cual: volver
    a crearlo perderia lo que tenga publicado.
    """
    if not NOMBRE_VALIDO.match(connector_id):
        raise ValueError(f"identificador de conector no valido: {connector_id!r}")
    red = red or DOCKER_NETWORK
    if not red:
        raise DockerNoDisponible(
            "no se sabe en que red de Docker vive este nodo: falta ODS_DOCKER_NETWORK"
        )

    nombre = nombre_contenedor(connector_id)
    existentes = listar()
    if connector_id in existentes:
        if existentes[connector_id]["estado"] != "running":
            _pedir("POST", f"/containers/{nombre}/start")
        return {"creado": False, "nombre": nombre}

    cuerpo = {
        "Image": CONNECTOR_IMAGE,
        "Env": [f"{k}={v}" for k, v in entorno.items()],
        "Labels": {
            ETIQUETA: "true",
            ETIQUETA_NODO + ".connector": connector_id,
        },
        "HostConfig": {
            # Sin puertos publicados: al conector de un participante se llega
            # por el paso del nodo, nunca desde fuera.
            "RestartPolicy": {"Name": "unless-stopped"},
            "NetworkMode": red,
        },
    }
    _pedir("POST", f"/containers/create?name={nombre}", cuerpo)
    _pedir("POST", f"/containers/{nombre}/start")
    return {"creado": True, "nombre": nombre}


def retirar(connector_id):
    """Para y borra el contenedor de un conector. No toca su base de datos."""
    if not NOMBRE_VALIDO.match(connector_id):
        raise ValueError(f"identificador de conector no valido: {connector_id!r}")
    nombre = nombre_contenedor(connector_id)
    try:
        _pedir("DELETE", f"/containers/{nombre}?force=true")
        return True
    except DockerNoDisponible as exc:
        if "404" in str(exc):
            return False
        raise


def ejecutar_en(contenedor, orden):
    """Ejecuta una orden dentro de otro contenedor y devuelve (codigo, salida).

    Por la API del demonio, no por el cliente `docker`: la imagen de este
    servicio es una python-slim y no lo trae. Es como se crea la base de datos
    de cada conector sin meter un cliente de PostgreSQL aqui dentro.
    """
    creado = _pedir("POST", f"/containers/{contenedor}/exec", {
        "AttachStdout": True,
        "AttachStderr": True,
        "Cmd": orden,
    })
    exec_id = creado.get("Id")
    if not exec_id:
        raise DockerNoDisponible(f"no se pudo preparar la orden en {contenedor}")

    # La salida viene multiplexada por el protocolo de Docker: ocho bytes de
    # cabecera por trozo. Se leen en crudo y se limpian.
    conexion = _ConexionSocket(DOCKER_SOCKET)
    try:
        cuerpo = json.dumps({"Detach": False, "Tty": False}).encode("utf-8")
        conexion.request("POST", f"/exec/{exec_id}/start", body=cuerpo,
                         headers={"Content-Type": "application/json"})
        crudo = conexion.getresponse().read()
    finally:
        conexion.close()

    salida, resto = [], crudo
    while len(resto) >= 8:
        largo = int.from_bytes(resto[4:8], "big")
        salida.append(resto[8:8 + largo])
        resto = resto[8 + largo:]
    texto = b"".join(salida).decode("utf-8", "replace") if salida else crudo.decode("utf-8", "replace")

    estado = _pedir("GET", f"/exec/{exec_id}/json")
    return int(estado.get("ExitCode") or 0), texto


def esperar(connector_id, segundos=60):
    """Espera a que su API de gestion conteste. Devuelve si llego a contestar."""
    import urllib.error
    import urllib.request

    url = f"http://{nombre_contenedor(connector_id)}:8080/management/v3/assets"
    fin = time.time() + segundos
    while time.time() < fin:
        try:
            urllib.request.urlopen(url, timeout=3)
            return True
        except urllib.error.HTTPError:
            # Contesta, aunque sea 401: el proceso esta en pie, que es lo que
            # se pregunta aqui.
            return True
        except Exception:
            time.sleep(2)
    return False
