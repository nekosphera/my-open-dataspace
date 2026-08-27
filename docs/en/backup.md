# Backups

## What needs saving

Four things, and only these four:

| What | Where | Why it cannot be rebuilt |
|---|---|---|
| PostgreSQL | volume `pgdata` | Assets, policies, contracts, negotiations — and the Keycloak realm with its users |
| Published files | volume `files` | They are the data. If they are lost, your products point to nothing |
| Node state | volume `ods-data` | Sign-ups, participants, evidence log, known nodes and **the audit signing keys** |
| RDF store | volume `fuseki-data` | The merged catalogue |

What does **not** need saving, because it comes back on its own: the images,
Caddy's certificates —they are requested again— and the part of the merged
catalogue that comes from remote nodes, which is filled in on the next sync.

**The `.env` is not part of the backup.** It holds the node's passwords, and a
backup ends up in places where a secrets file should not be: a shared disk, a
bucket, somebody's laptop. Keep it wherever you keep your secrets. Without it
the backup is useless, so write down **where** it is.

## Making one

```bash
./deploy/backup.sh                    # to ./backups/<timestamp>/
./deploy/backup.sh /mnt/copias        # wherever you like
```

With the node running. The PostgreSQL dump and the RDF store dump are
requested through their own APIs, not by copying files: copying the TDB2
files while Fuseki is running gives a backup that sometimes restores and
sometimes does not, and you do not know which until you need it.

Automating it is an ordinary `cron` job:

```cron
0 3 * * * cd /opt/my-open-dataspace && ./deploy/backup.sh /mnt/copias >> /var/log/ods-backup.log 2>&1
```

## Restoring

On a stopped node, and **with the same `.env`**: the passwords in the dump are
the ones from back then.

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

If the RDF store fails, do not stop: it rebuilds itself on the next sync. The
merged catalogue is never the copy that matters.

## Check it before you need it

**A backup nobody has ever restored is a folder with data in it.**

The cheap way to check it is to restore it on a separate node, on other
ports, as in [dos-nodos.md](dos-nodos.md):

```bash
docker compose -p ods-prueba --env-file .env.prueba up -d
# …restore there…
python tests/e2e/golden_path.py http://localhost:8081
```

If the full walkthrough passes against the restored node, the backup works.
If it does not pass, you have found out on a Tuesday afternoon and not on the
day the disk broke.

## Upgrading to a new version

It is not a backup, but it gets done just as badly for the same reason:

```bash
./deploy/backup.sh                    # this first
# change ODS_IMAGE_APP and ODS_IMAGE_CONNECTOR in .env
docker compose pull && docker compose up -d
```

Volumes survive a `docker compose down`. What takes them away is `down -v`,
and that has to be typed on purpose.
