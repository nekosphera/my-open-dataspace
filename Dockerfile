# Imagen todo-en-uno: portal, conector, base de datos y almacén RDF.
#
#     docker run -p 8080:8080 myopendataspace/my-open-dataspace
#
# Para evaluación y docencia. Sin Keycloak, sin TLS y **sin autenticación**:
# cualquiera que alcance el puerto puede publicar, negociar y descargar. Lo
# dice al arrancar y lo dice el portal.
#
# La composición de seis contenedores es la que se instala de verdad. Esta
# existe porque la barrera de entrada de un producto se mide en el primer
# minuto, y pedir un `docker compose` y cuatro contraseñas antes de que nadie
# haya visto nada es perder a quien sólo quería mirar.

FROM eclipse-temurin:21-jre AS jre

FROM eclipse-temurin:21-jdk AS connector-build
WORKDIR /build
RUN apt-get update \
 && apt-get install -y --no-install-recommends maven \
 && rm -rf /var/lib/apt/lists/*
COPY connector/pom.xml .
RUN mvn -q dependency:resolve
COPY connector/src src
RUN mvn -q clean package -DskipTests


FROM debian:bookworm-slim

ARG VCS_REF=unknown
ARG BUILD_DATE=unknown
ARG VERSION=dev
LABEL org.opencontainers.image.source="https://github.com/nekosphera/my-open-dataspace" \
      org.opencontainers.image.title="My Open Dataspace (all-in-one)" \
      org.opencontainers.image.description="Self-hosted EDC dataspace, single-container evaluation build. Not for production." \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.version="${VERSION}"

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      postgresql postgresql-contrib \
      python3 python3-pip python3-venv \
      curl jq ca-certificates bash \
 && rm -rf /var/lib/apt/lists/*

# El JRE, de la misma imagen con la que se compila el conector.
#
# Debian bookworm trae OpenJDK 17, y el conector se compila con 21: el
# resultado era un UnsupportedClassVersionError -- class file 65 contra un
# runtime que llega a 61 -- que el contenedor sólo enseñaba en el registro del
# conector, mientras el portal seguía contestando 200 como si nada.
COPY --from=jre /opt/java/openjdk /opt/java/openjdk
ENV JAVA_HOME=/opt/java/openjdk
ENV PATH="${JAVA_HOME}/bin:${PATH}"

# Fuseki, del archivo de Apache.
#
# Se comprueba la suma que Apache publica junto al fichero. Ojo con lo que eso
# vale y lo que no: viene del mismo origen que el tarball, asi que no protege
# contra un archive.apache.org comprometido. Lo que si detecta es una descarga
# truncada o corrompida, que es el fallo que de verdad pasa y que sin esto se
# manifiesta como un contenedor que arranca y no sirve.
ARG FUSEKI_VERSION=5.1.0
WORKDIR /opt
RUN set -eux; \
    base="https://archive.apache.org/dist/jena/binaries/apache-jena-fuseki-${FUSEKI_VERSION}.tar.gz"; \
    curl -fsSL -o "apache-jena-fuseki-${FUSEKI_VERSION}.tar.gz" "${base}"; \
    curl -fsSL -o fuseki.sha512 "${base}.sha512"; \
    sha512sum -c fuseki.sha512; \
    tar xzf "apache-jena-fuseki-${FUSEKI_VERSION}.tar.gz"; \
    mv "apache-jena-fuseki-${FUSEKI_VERSION}" /opt/fuseki; \
    rm -f "apache-jena-fuseki-${FUSEKI_VERSION}.tar.gz" fuseki.sha512

WORKDIR /srv/ods
COPY app/requirements.txt app/requirements.txt
COPY federation/requirements.txt federation/requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages \
      -r app/requirements.txt -r federation/requirements.txt

COPY app/ app/
COPY federation/ federation/
COPY profiles/ profiles/
COPY seed/ seed/
COPY --from=connector-build /build/target/edc-identity-hub-integration-jar-with-dependencies.jar /opt/connector.jar
COPY connector/config/ /opt/connector-config/
COPY deploy/allinone-entrypoint.sh /usr/local/bin/ods-allinone
RUN chmod +x /usr/local/bin/ods-allinone federation/federator/*.sh

# Sin identidad y sin TLS. Las dos son deliberadas y las dos se anuncian.
ENV ODS_EVALUATION_MODE=true \
    EDC_EVALUATION_MODE=true \
    ODS_ORG_NAME="My Open Dataspace" \
    ODS_ORG_ID="evaluation" \
    ODS_ADMIN_EMAIL="admin@localhost.invalid" \
    ODS_PUBLIC_URL="http://localhost:8080" \
    ODS_CONNECTOR_ID="connector" \
    ODS_CONNECTOR_URL="http://127.0.0.1:9090" \
    ODS_FUSEKI_URL="http://127.0.0.1:3030" \
    ODS_FUSEKI_DATASET="dataspace" \
    ODS_FUSEKI_ADMIN_USER="admin" \
    ODS_SEED_DEMO="true" \
    ODS_FEDERATION_INTERVAL="300" \
    ODS_SPARQL_PUBLIC="false" \
    ONBOARDING_DATA_DIR=/var/lib/ods \
    ODS_FILES_DIR=/var/lib/ods/files \
    ONBOARDING_HOST=0.0.0.0 \
    ONBOARDING_PORT=8080 \
    PGDATA=/var/lib/ods/pgdata \
    PYTHONUNBUFFERED=1

VOLUME ["/var/lib/ods"]
EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=5s --start-period=90s --retries=5 \
  CMD curl -fsS http://127.0.0.1:8080/api/onboarding/health || exit 1

ENTRYPOINT ["/usr/local/bin/ods-allinone"]
