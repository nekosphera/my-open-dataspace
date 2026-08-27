# Copias de seguridad

## Qué hay que salvar

Cuatro cosas, y sólo estas cuatro:

| Qué | Dónde | Por qué no se reconstruye |
|---|---|---|
| PostgreSQL | volumen `pgdata` | Activos, políticas, contratos, negociaciones — y el realm de Keycloak con sus usuarios |
| Ficheros publicados | volumen `files` | Son los datos. Si se pierden, tus productos apuntan a nada |
| Estado del nodo | volumen `ods-data` | Altas, participantes, registro de evidencias, nodos conocidos y **las claves de firma de la auditoría** |
| Almacén RDF | volumen `fuseki-data` | El catálogo consolidado |

Lo que **no** hace falta salvar, porque vuelve solo: las imágenes, los
certificados de Caddy —se vuelven a pedir— y la parte del catálogo
consolidado que viene de nodos remotos, que se rellena en la siguiente
sincronización.

**El `.env` no entra en la copia.** Lleva las contraseñas del nodo dentro, y
una copia de seguridad acaba en sitios donde un fichero de secretos no debería
estar: un disco compartido, un bucket, el portátil de alguien. Guárdalo donde
guardes los secretos. Sin él la copia no sirve de nada, así que anota **dónde**
está.

## Hacer una

```bash
./deploy/backup.sh                    # a ./backups/<sello-de-tiempo>/
./deploy/backup.sh /mnt/copias        # a donde quieras
```

Con el nodo levantado. El volcado de PostgreSQL y el del almacén RDF se piden
por sus propias APIs, no copiando ficheros: copiar los ficheros de TDB2 con
Fuseki en marcha da una copia que a veces restaura y a veces no, y no se sabe
cuál hasta que hace falta.

Automatizarlo es un `cron` corriente:

```cron
0 3 * * * cd /opt/my-open-dataspace && ./deploy/backup.sh /mnt/copias >> /var/log/ods-backup.log 2>&1
```

## Restaurar

En un nodo parado, y **con el mismo `.env`**: las contraseñas del volcado son
las de entonces.

```bash
docker compose down
docker compose up -d postgres
sleep 10

gunzip -c copia/postgres.sql.gz | docker compose exec -T postgres psql -U dataspace postgres

docker compose up -d app
docker compose exec -T app sh -c 'rm -rf /var/lib/ods/* && tar xzf - -C /var/lib/ods' < copia/estado.tar.gz

docker compose exec -T app sh -c '
  curl -sf -u "admin:${ODS_FUSEKI_ADMIN_PASSWORD}" \
    -H "Content-Type: application/n-quads" --data-binary @- \
    "${ODS_FUSEKI_URL}/${ODS_FUSEKI_DATASET}/data"
' < <(gunzip -c copia/fuseki.nq.gz)

docker compose up -d
```

Si el almacén RDF falla, no pares: se reconstruye solo en la siguiente
sincronización. El catálogo consolidado nunca es la copia que importa.

## Compruébala antes de necesitarla

**Una copia que nadie ha restaurado nunca es una carpeta con datos dentro.**

La forma barata de comprobarlo es restaurarla en un nodo aparte, en otros
puertos, como en [dos-nodos.md](dos-nodos.md):

```bash
docker compose -p ods-prueba --env-file .env.prueba up -d
# …restaurar ahí…
python tests/e2e/golden_path.py http://localhost:8081
```

Si el recorrido completo pasa contra el nodo restaurado, la copia sirve. Si no
pasa, lo has descubierto un martes por la tarde y no el día que se rompió el
disco.

## Actualizar de versión

No es una copia de seguridad, pero se hace igual de mal por el mismo motivo:

```bash
./deploy/backup.sh                    # primero esto
# cambiar ODS_IMAGE_APP y ODS_IMAGE_CONNECTOR en .env
docker compose pull && docker compose up -d
```

Los volúmenes sobreviven a un `docker compose down`. Lo que se los lleva es
`down -v`, y eso hay que escribirlo a propósito.
