# Code provenance

Each block of code brought in from another repository is recorded here with
its origin and the exact commit it comes from. That is what makes it possible
to bring in upstream improvements later on without guessing where each thing
came from.

The source repositories are **read-only** for this project. If something from
a source turns out to be incomplete or wrong it is fixed **here** and recorded
in the "Corrections to the source" section; never upstream.

## Source repositories

| Source | Commit | Date |
|---|---|---|
| `nekosphera/mydataspace` | `395092b4e9a2a27ff270ce079d2a7e6e761bda02` | 2026-08-24 |
| `nekosphera/catalejo` | `dd6c56ad3308d7850a06fb9bf140435a7eedeb73` | 2026-08-24 |

## Incorporated blocks

### `app/` — portal, console and API

| Destination | Source | Source file |
|---|---|---|
| `app/onboarding_api.py` | mydataspace | `tools/onboarding_api.py` |
| `app/requirements.txt` | mydataspace | `tools/onboarding_api.requirements.txt` |
| `app/tools/render_ui_runtime_config.py` | mydataspace | `tools/render_ui_runtime_config.py` |
| `app/tools/setup_keycloak_rbac.sh` | mydataspace | `tools/setup_keycloak_rbac.sh` |
| `app/tools/smoke_secure_download.py` | mydataspace | `tools/smoke_secure_download.py` |
| `app/ui/` | mydataspace | `ui/` without `papers/` or `urban-health-data/` |
| `app/ui/vendor/keycloak.js` | mydataspace | `ui/vendor/keycloak.js` — Keycloak adapter, Apache-2.0, unmodified |

### `connector/` — the project's own EDC connector

| Destination | Source | Source file |
|---|---|---|
| `connector/src/` | mydataspace | `src/` (Java, `main` and `test`) |
| `connector/pom.xml` | mydataspace | `pom.xml` |
| `connector/Dockerfile` | mydataspace | `Dockerfile` (the one at the root) |
| `connector/config/edc-config.properties` | mydataspace | `config/edc-config.properties` |

### `federation/` — federated catalogue

Taken from the public `catalejo` repository, **not** from the vendored copy
that `mydataspace` kept in `catalogue/`: the original repository is more
complete (it brings the federator, the vocabularies and the observability) and
it is the one that receives the improvements.

| Destination | Source | Source file |
|---|---|---|
| `federation/src/catalejo/` | catalejo | `src/catalejo/` |
| `federation/federator/` | catalejo | `federator/` |
| `federation/smoke/`, `federation/smoke.sh` | catalejo | `smoke/`, `smoke.sh` |
| `federation/requirements.txt` | catalejo | `requirements.txt` |

### `profiles/` — metadata and policy profiles

| Destination | Source | Source file |
|---|---|---|
| `profiles/dcat-ap/1.0.0/` | catalejo | `vocabularies/dcat-ap/1.0.0/` |
| `profiles/odrl/1.0.0/` | catalejo | `vocabularies/odrl/1.0.0/` |
| `profiles/ns.jsonld` | catalejo | `vocabularies/ns.jsonld` |

### `db/`

| Destination | Source | Source file |
|---|---|---|
| `db/01-create-databases.sql` | mydataspace | `config/postgres-init/01-create-databases.sql` |

### `tests/`

| Destination | Source | Source file |
|---|---|---|
| `tests/test_catalog_federation_delta.py` | mydataspace | `tests/test_catalog_federation_delta.py` |
| `tests/test_catalog_metadata_shapes.py` | mydataspace | `tests/test_catalog_metadata_shapes.py` |
| `tests/e2e/` | mydataspace | `tests/e2e/` |

## Corrections to the source

Recorded here as they come up.

### C-001 — The connector's Dockerfile

`mydataspace` has two Java Dockerfiles and does not say which one builds the
project's own connector. `eclipse-runtime/Dockerfile` clones the official
Eclipse connector from `main` at build time; the one at the root is the one
that compiles `org.eclipse.dataspace.DataSpaceApplication`, which is the
project's own connector with its `management/v3` surface and the mediated
download.

The one at the root is brought in. The official runtime one is left out: as
well as not being the connector the specification says to reuse, it builds
from `main` without pinning a version, which makes the image irreproducible.

Two OCI labels that pointed to the source repository have been changed
(`image.source` and `image.title`).

### C-002 — The Keycloak adapter came back into the tree

Phase 1 deleted `ui/vendor/` entirely, taking it for third-party dead weight.
Inside it was `keycloak.js`, which **four files import at runtime**: the two
login pages, the console and the audit panel. Without it, the `import()`
fails, is swallowed in a `catch` and the page says "Login could not be
completed" without saying why.

It comes back as is, unmodified. **Vendored and not from a CDN**, which is the
rule in section 0b: a node has to work with what is in the tree, and the login
page cannot depend on a third party being available.

### C-003 — The console talked to services that stayed behind in the source

`app/ui/app.js` and `app/ui/console-audit.js` came from the source project's
panel, which relied on an external governance service. When they were brought
in, the service was removed but the calls were left, and they kept requesting
routes this product does not serve:
`/api/governance/dataspaces/<id>/catalog` for four identifiers —three of them
from the source: `dataspace-a`, `dataspace-b`, `myfiware`—,
`/api/governance/audit/traces`, `/api/v1/edc/bridge/payloads` and
`papers_manifest.json`. All of it returned 404.

`console-audit.js` is retired entirely: besides the routes, it began with
`if (cfg.id !== "connector-1") return;` and looked for the identifiers of a
`console.html` that the generated console does not have, so it never ran in
this product. What was actually needed —approving sign-ups and viewing
participants— is in `app/ui/console-solicitudes.js`, written for the console
this product generates.

In `app.js` the governance layer, the EDC bridge, the papers manifest and the
document audit hanging off downloads are retired —the one for the analysis
with Mistral, which this version does not have—. The peer-to-peer path is
kept, which was the only one that could work here.

The correction goes in the destination repository and **does not go back to
the source**, as section 0 requires.

### C-004 — Source prefixes and identifiers in the metadata

The console wrote `myds:deliveryMode`, `myds:policyId` and `myds:contractId`
—the source project's prefix— and this product's metadata profile requires
`ods:`. The ones it writes are changed; on read both are accepted, because
assets published before the change carry `myds:` and no longer seeing them
would mean losing them from the catalogue.

### C-005 — Dynamic connector provisioning

The source `onboarding_api.py` served a deployment with three connectors and
signed participants up by creating one per person:
`make_connector_id(correo)` plus its Keycloak client, its wallet, its
registry, its participant and its console. Section 4 of the specification
requires removing it —"everything that instantiates more than one"— and the
pruning took the pages and the groups but not this part, which is the one that
instantiated it.

It is retired entirely, together with the reconciliation that existed to
support it (`create_connector_for_owner`, `rollback_connector_artifacts`,
`connector_is_complete`, `ensure_connector_artifacts_for_existing_user`). What
remains in its place migrates anyone who had been left hanging off one of
those connectors to the node's connector, without touching their account.

`app/ui/home-audit.js` queried `/api/connector-1/…`, `-2` and `-3`, from the
same source deployment; it now queries the pass-through to this node's
connector.

### C-005 bis — Per-participant provisioning, redone

C-005 retired the source project's dynamic connector provisioning because the
specification asked for one connector per node. Amendment 16 asks for the
opposite, so the idea comes back —one connector per participant— but **not
the code**: that code created an identifier, a client and a wallet without
anything behind it separating the offer, so all participants shared the same
pool of assets and each of them saw everything as their own.

What is there now has been written for this product: the signed claim, the
owner column in the connector's three tables and the filter on read.
