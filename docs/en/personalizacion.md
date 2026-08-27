# Customising your node

This is why the project exists: so that an organisation can install it, add
its own things and not have to touch code for any of what follows.

If anything on this page forces you to edit a `.py`, that is a bug in the
project. Say so in an issue.

## The brand

Name, email, colour, logo and legal notice come from the first-start setup
wizard. After that they are changed in `.env` and the node is started again:

```bash
ODS_ORG_NAME="Ayuntamiento de Ejemplo"
ODS_BRAND_COLOR="#0b6e4f"
ODS_LOGO_PATH="/assets/brand/logo.svg"
ODS_ICON_PATH="/assets/brand/icono.ico"
ODS_LEGAL_NOTICE="Aviso legal — Ayuntamiento de Ejemplo"
```

The logo and the icon are paths inside the brand volume, not files in the
repository. You put them there:

```bash
docker compose cp logo.svg app:/srv/ods/app/ui/assets/brand/logo.svg
```

`app/ui/assets/brand/` is in `.gitignore` on purpose: your brand is yours and
has no reason to end up in a `git status` every time you upgrade.

The interface reads all of that from `runtime-config.js`, which **is
generated on every start** from the environment. Do not edit it: it gets
overwritten.

## The metadata and policy profiles

In `profiles/`. Two generic ones are shipped:

```
profiles/
├─ dcat-ap/1.0.0/    perfil DCAT-AP y sus formas SHACL
├─ odrl/1.0.0/       perfil de política ODRL
├─ ns.jsonld         los términos propios del proyecto
└─ manifest.json     el índice que la consola consulta
```

(*`dcat-ap/1.0.0/`: DCAT-AP profile and its SHACL shapes; `odrl/1.0.0/`: ODRL
policy profile; `ns.jsonld`: the project's own terms; `manifest.json`: the
index the console reads.*)

**Adding your own is copying a folder.** Not a single line of code:

1. `cp -r profiles/dcat-ap profiles/mi-perfil`
2. Edit `profiles/mi-perfil/1.0.0/profile.jsonld` and its `shapes.ttl`.
3. Add it to `profiles/manifest.json`.
4. Start the node again.

The validator reads the profile's SHACL shapes; it does not carry its own
copy of the rules. If you tighten a constraint, the console starts rejecting
on it without anything else having to be touched.

The project's own terms hang from `urn:ods:`, not from a domain: a vocabulary
IRI has no reason to resolve, and making it depend on a domain means having
to keep that domain alive for a catalogue to keep validating.

## Your use cases

In `seed/`. What is there are two sample products, so that the first screen
is not empty and so that you can go through publish → negotiate → download
without having uploaded anything.

To put in your own:

1. Leave your files in `seed/data/`.
2. Describe them in `seed/manifest.json`, one per product, with its policy
   and its contract.
3. `ODS_SEED_DEMO="true"` and start the node again.

`tests/test_seed_is_shippable.py` checks that every product in the manifest
has its file **and that the file is versioned**. That second part exists
because an unanchored `.gitignore` rule swept away the sample files, and the
node was publishing two products whose download returned 404: worse than
publishing none, because it looks like it works.

To publish none: `ODS_SEED_DEMO="false"`.

## The nodes you federate with

They are registered through the API —`POST /api/v1/nodes` with `label` and
`baseUrl`—, and their offer enters your merged catalogue on the next sync, or
immediately with `POST /api/v1/nodes/sync`. The full procedure, with the
token and the addresses, is in `docs/dos-nodos.md`.

The console's **Known nodes** tab is not offered in this release. The panel
and everything behind it are still written and tested; the only thing
missing is the button that leads to it.

The only thing needed on the other side is that its `/api/v1/catalog`
answers, which is true of any node of this product without its administrator
having to do anything. No cross credentials, no prior agreements, no opening
up the administration of its connector.

See [dos-nodos.md](dos-nodos.md).

## The language

`ODS_LANG="es"` or `"en"`. It determines which version of each page someone
who arrives without choosing is sent to; the selector in the corner keeps
working in both.

The pages are `*.html` and `*-en.html`. Adding a third language means
touching templates — that is not yet "copying a folder", and it is noted as a
limitation.

## What CANNOT be customised without touching code

Stated here so that nobody finds out halfway through a migration:

- **A third language.** There are two, and adding another goes through the
  templates.
- **The negotiation flow.** It is the connector's; changing it is changing
  the connector.
- **More than one connector per node.** This version ships one, provider and
  consumer at once. For several, you install several nodes and federate them
  — which is also what federation does well.
- **The console's structure.** Its tabs are fixed.
- **The identity provider.** It is Keycloak. Its realm is imported and can be
  edited, but replacing it with another is not planned.
