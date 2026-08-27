# Locked out of my node

> Run it from the root of the repository, where you ran `./install.sh`.
> It is also at `deploy/reiniciar.sh`: the one at the root just leads to that
> one. Without being told what to do it prints this list and exits with an
> error, not silently.
>
> **In PowerShell use `.\reiniciar.ps1`**, with the same arguments.
> `.\reiniciar.sh` there runs nothing and says nothing: PowerShell does not run
> `.sh` files. In Git Bash, on Linux and on macOS, `./reiniciar.sh`.

Three ways out, from the least destructive to the most. **Start with the
first**: almost always the problem is a password, and for that there is no
need to tear down a whole node.

All of them are run from the repository folder, with the node running
—except the last one, which starts it itself—.

## 1. I do not remember the password

```bash
./reiniciar.sh --contrasena admin@tu-organizacion.example
```

It asks for a new password and changes it. It touches nothing else: not what
has been published, not the participants, not the log.

If you do not know which email the node was configured with, run it with any
address: it will tell you which accounts exist.

And if the account was disabled, it enables it again — a new password on a
disabled account is the worst possible outcome, because it looks like it has
worked.

## 2. I want to configure it again from the start

```bash
./reiniciar.sh --asistente
```

It reopens `/setup` to choose organisation, administrator, language and brand
again. It **keeps** the published assets, their policies and contracts, the
participants and the operations log.

This is the "explicit command-line order" the specification talks about:
`/setup` returns 404 as soon as the node is configured, and cannot be
reopened from the web. If it could, anyone who reached the node would make
themselves administrator.

## 3. I want to start from scratch

```bash
./reiniciar.sh --todo
```

It deletes the volumes and starts again. **Everything is lost**: the database
with assets, policies and contracts, Keycloak with all the accounts, the
merged catalogue, the published files and the log.

It asks for confirmation by typing `SI`. If you want a backup first:
`./deploy/backup.sh`.

By hand it is the same:

```bash
docker compose down -v
docker compose up -d --build
```

## Before anything else: look at what is happening

```bash
./deploy/diagnostico.sh > diagnostico.txt
```

Often there is nothing to recover. Two frequent causes, both with the same
symptom —"I cannot get in"— and neither fixable by deleting data:

- **A container restarting in a loop.** It shows "Up" one second in every
  three and in a normal `docker compose ps` it looks healthy. The restarts
  column in the diagnostics gives it away.
- **You changed `ODS_DB_PASSWORD` in `.env` after installing.** PostgreSQL
  only sets the password when it creates its database: the connector can no
  longer get in and keeps restarting. There is a warning about it in
  `.env.example`, with the `ALTER USER` that does change it.

## About the all-in-one image

If you launched it with `docker run` **without** `-v`, there is nothing to
recover: Docker gave it an anonymous volume and when the container was
removed the volume went with it. Launch it again with a named volume and it
will not happen again:

```bash
docker run -p 8080:8080 -v ods-datos:/var/lib/ods \
  ghcr.io/nekosphera/my-open-dataspace:0.1.0
```
