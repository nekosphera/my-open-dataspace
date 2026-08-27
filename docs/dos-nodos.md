# Levantar dos nodos en la misma máquina

Un nodo solo no demuestra nada: enseña un catálogo con contratos, no un
espacio de datos. Esto es cómo levantar un segundo nodo en local para ver la
federación funcionando —y para comprobar que un nodo caído no rompe la vista
del otro, que es la parte que hay que probar explícitamente y no dar por
hecha.

Hace falta Docker y nada más.

## 1. El primer nodo

```bash
./install.sh          # o: cp .env.example .env, rellenar y docker compose up -d
```

Queda en `http://localhost:8080`.

## 2. El segundo

Un `.env` propio con otros puertos, otro identificador de conector y sus
propias contraseñas. **No reutilices el `.env` del primero**: compartirían
nombre de conector y sus ofertas se pisarían en el grafo consolidado.

```bash
sed -e 's/^ODS_ORG_NAME=.*/ODS_ORG_NAME="Consorcio Vecino"/' \
    -e 's/^ODS_ORG_ID=.*/ODS_ORG_ID="consorcio-vecino"/' \
    -e 's/^ODS_ADMIN_EMAIL=.*/ODS_ADMIN_EMAIL="admin@vecino.example"/' \
    -e 's/^ODS_CONNECTOR_ID=.*/ODS_CONNECTOR_ID="connector-vecino"/' \
    -e 's|^ODS_PUBLIC_URL=.*|ODS_PUBLIC_URL="http://localhost:8081"|' \
    -e 's/^ODS_HTTP_PORT=.*/ODS_HTTP_PORT="8081"/' \
    -e 's/^ODS_HTTPS_PORT=.*/ODS_HTTPS_PORT="8444"/' \
    .env.example > .env.vecino
```

Rellena las tres contraseñas de `.env.vecino` —`ODS_DB_PASSWORD`,
`ODS_KEYCLOAK_ADMIN_PASSWORD`, `ODS_FUSEKI_ADMIN_PASSWORD`— y levántalo como
un proyecto de Docker aparte, para que tenga sus propios volúmenes:

```bash
docker compose -p ods-vecino --env-file .env.vecino up -d
```

Queda en `http://localhost:8081`. Tarda un par de minutos la primera vez:
Keycloak crea su base de datos y el sembrado espera a que el conector suba.

Los ficheros `.env.*` están en `.gitignore`: llevan contraseñas dentro.

## 3. Presentarlos

En la consola del primer nodo, pestaña **Nodos conocidos**, añade la dirección
del segundo. Desde dentro de un contenedor, `localhost` es el contenedor
mismo, así que la dirección que hay que dar es la de la máquina anfitriona:

```
http://host.docker.internal:8081
```

En Linux sin Docker Desktop ese nombre no existe. Añade al servicio `app`:

```yaml
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

que es lo mismo sin tener que averiguar ninguna dirección. Si prefieres la del
anfitrión en la red de Docker, la da `docker network inspect bridge`.

Pulsa **Actualizar ahora** en vez de esperar al intervalo.

## 4. Qué tiene que verse

En **Catálogo del espacio de datos**, las ofertas de los dos nodos en una sola
pantalla, cada una con el nodo que la ofrece. Por consulta directa:

```bash
docker compose exec app sh -c 'curl -s -u admin:"$ODS_FUSEKI_ADMIN_PASSWORD" \
  --data-urlencode "query=SELECT ?connector ?assetId ?name WHERE {
    GRAPH ?g { ?a <urn:edc:connector> ?connector ;
                  <urn:edc:assetId> ?assetId ;
                  <urn:edc:name> ?name } } ORDER BY ?connector" \
  -H "Accept: application/sparql-results+json" \
  http://fuseki:3030/dataspace/query'
```

## 5. La prueba que de verdad importa

Apaga el segundo nodo y vuelve a sincronizar:

```bash
docker compose -p ods-vecino stop
```

Lo que tiene que pasar, y hay que mirarlo:

- El catálogo **sigue mostrando las ofertas de los dos**. El grafo del nodo
  caído se conserva; su oferta no desaparece de la vista.
- El nodo caído aparece como **no disponible**, con **la fecha de su última
  sincronización correcta** —no la de ahora—, para que se sepa de cuándo son
  los datos que se están viendo.
- El portal, la publicación, la negociación y la descarga siguen funcionando.
  El catálogo consolidado nunca bloquea la operación.

Vuelve a arrancarlo (`docker compose -p ods-vecino start`) y en la siguiente
sincronización vuelve a `disponible`.

## Limpiar

```bash
docker compose -p ods-vecino down -v
rm .env.vecino
```

Y retira el nodo desde la pestaña **Nodos conocidos** del primero, que se
lleva su grafo con él y deja el resto del almacén intacto.

## Cómo se federa, por debajo

Un nodo **no** lee la API de gestión del conector de otro. Esa superficie no
se publica, y aunque se publicara haría falta una credencial en el Keycloak de
la otra organización.

Lo que un nodo expone es `GET /api/v1/catalog`: público, de sólo lectura, y
sólo con la oferta —qué hay, bajo qué política y bajo qué contrato—. Ni
usuarios, ni solicitudes, ni el registro de operaciones. Es todo lo que otro
nodo necesita para federarte, y es la única razón por la que dar de alta un
nodo se reduce a escribir su dirección.
