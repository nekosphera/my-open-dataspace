# Running two nodes on the same machine

A single node proves nothing: it shows a catalogue with contracts, not a data
space. This is how to start a second node locally to see federation working
—and to check that a node going down does not break the other's view, which
is the part that has to be tested explicitly and not taken for granted.

You need Docker and nothing else.

## 1. The first node

```bash
./install.sh          # or: cp .env.example .env, fill it in and docker compose up -d
```

It is at `http://localhost:8080`.

## 2. The second

A `.env` of its own with other ports, another connector identifier and its
own passwords. **Do not reuse the first one's `.env`**: they would share a
connector name and their offers would overwrite each other in the merged
graph.

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

Fill in the three passwords in `.env.vecino` —`ODS_DB_PASSWORD`,
`ODS_KEYCLOAK_ADMIN_PASSWORD`, `ODS_FUSEKI_ADMIN_PASSWORD`— and start it as a
separate Docker project, so that it has its own volumes:

```bash
docker compose -p ods-vecino --env-file .env.vecino up -d
```

It is at `http://localhost:8081`. It takes a couple of minutes the first
time: Keycloak creates its database and the seeding waits for the connector
to come up.

The `.env.*` files are in `.gitignore`: they hold passwords.

## 3. Introducing them

The second node is registered in the first. **The "Known nodes" tab is not
offered in this release** —the panel and its code are still in the console,
but there is no button that leads to it—, so it is done through the API,
which is exactly what that button called.

From inside a container, `localhost` is the container itself, so the address
you have to give is the host machine's:

```bash
# The token comes from the console: go to /console.html and, in the
# browser console, `await window.__DATASPACE_ENSURE_FRESH_TOKEN()`.
curl -X POST http://localhost:8080/api/v1/nodes   -H "Authorization: Bearer ${TOKEN}"   -H "Content-Type: application/json"   -d '{"label": "Consorcio Vecino", "baseUrl": "http://host.docker.internal:8081"}'

# And without waiting for the sync interval:
curl -X POST http://localhost:8080/api/v1/nodes/sync -H "Authorization: Bearer ${TOKEN}"
```

On Linux without Docker Desktop that name does not exist. Add to the `app`
service:

```yaml
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

which is the same thing without having to work out any address. If you
prefer the host's address on the Docker network,
`docker network inspect bridge` gives it to you.

Press **Refresh now** instead of waiting for the interval.

## 4. What you should see

In **Data space catalogue**, the offers of both nodes on a single screen, each
one with the node that offers it. By direct query:

```bash
docker compose exec app sh -c 'curl -s -u admin:"$ODS_FUSEKI_ADMIN_PASSWORD" \
  --data-urlencode "query=SELECT ?connector ?assetId ?name WHERE {
    GRAPH ?g { ?a <urn:edc:connector> ?connector ;
                  <urn:edc:assetId> ?assetId ;
                  <urn:edc:name> ?name } } ORDER BY ?connector" \
  -H "Accept: application/sparql-results+json" \
  http://fuseki:3030/dataspace/query'
```

## 5. The test that really matters

Shut down the second node and sync again:

```bash
docker compose -p ods-vecino stop
```

What has to happen, and you have to look at it:

- The catalogue **still shows the offers of both**. The graph of the node that
  went down is kept; its offer does not disappear from the view.
- The node that went down appears as **unavailable**, with **the date of its
  last successful sync** —not the current one—, so that it is clear how old
  the data being shown is.
- The portal, publishing, negotiation and download keep working. The merged
  catalogue never blocks operation.

Start it again (`docker compose -p ods-vecino start`) and on the next sync it
goes back to `up`.

## Cleaning up

```bash
docker compose -p ods-vecino down -v
rm .env.vecino
```

And remove the node from the first one with `DELETE /api/v1/nodes/<id>`,
which takes its graph with it and leaves the rest of the store intact.

## How federation works, underneath

A node does **not** read another node's connector management API. That
surface is not published, and even if it were, it would take a credential in
the other organisation's Keycloak.

What a node exposes is `GET /api/v1/catalog`: public, read-only, and
containing only the offer —what there is, under which policy and under which
contract—. No users, no requests, no operations log. It is all another node
needs to federate you, and it is the only reason registering a node comes
down to typing its address.
