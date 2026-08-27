# La aplicacion: portal, consola, API de alta y el federador del catalogo.
FROM python:3.12-slim

# bash, curl y jq porque el federador es un guion de shell; ca-certificates
# para poder hablar con un nodo remoto por HTTPS.
RUN apt-get update \
 && apt-get install -y --no-install-recommends bash curl jq ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /srv/ods

COPY app/requirements.txt app/requirements.txt
COPY federation/requirements.txt federation/requirements.txt
RUN pip install --no-cache-dir -r app/requirements.txt -r federation/requirements.txt

COPY app/ app/
COPY federation/ federation/
COPY profiles/ profiles/
COPY seed/ seed/
COPY deploy/entrypoint.sh /usr/local/bin/ods-entrypoint
RUN chmod +x /usr/local/bin/ods-entrypoint federation/federator/*.sh 2>/dev/null || true

# El estado del nodo vive en un volumen, no en el arbol de la imagen: si
# viviera aqui, cada actualizacion se llevaria por delante las altas, los
# participantes y el registro de evidencias.
ENV ONBOARDING_DATA_DIR=/var/lib/ods \
    ODS_FILES_DIR=/var/lib/ods/files \
    ONBOARDING_HOST=0.0.0.0 \
    ONBOARDING_PORT=8092 \
    PYTHONUNBUFFERED=1
VOLUME ["/var/lib/ods"]

EXPOSE 8092
ENTRYPOINT ["/usr/local/bin/ods-entrypoint"]
