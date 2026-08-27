# Delivery status

One line per phase. Updated as each one is finished.

| Phase | Status | Date | Deliverable |
|---|---|---|---|
| 1 — Clean repository | ✅ done | 2026-08-27 | New tree with no history, licence, community files and folder structure |
| 2 — Pruning | ✅ done | 2026-08-27 | Six containers, no references to what was removed |
| 3 — A single connector | ✅ done | 2026-08-27 | Single console, full cycle |
| 3b — Merged catalogue | ✅ done | 2026-08-27 | Two nodes see each other's offer |
| 4 — Configuration | ✅ done | 2026-08-27 | Everything in `.env`, zero hard-coded values |
| 5 — Wizard and installer | ✅ done | 2026-08-27 | The ten-minute criterion |
| 6 — Images and release | ✅ done | 2026-08-27 | Downloadable images, E2E green |
| 7 — Documentation | ✅ done | 2026-08-27 | README, installation and customisation guides |
| 8 — Pre-release review | ✅ released | 2026-08-27 | Repository ready to go public |

---

## Phase 1 — Clean repository

**Done on 2026-08-27.**

New tree in `repos/my-open-dataspace` with the structure from section 10 and
the source code vendored inside, with no submodules or external references.
What was brought in and from where, in [procedencia.md](procedencia.md).

Project files: `LICENSE` (Apache-2.0), `NOTICE`, `SECURITY.md`,
`CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `CHANGELOG.md`, `.gitignore` and
`.gitattributes` — the latter forces LF across the whole tree, because an
`install.sh` with CRLF does not start inside the container.

---

## Phase 2 — Pruning

**Done on 2026-08-27, with one pending check described below.**

### What has been removed

**AI layer.** All of Mistral: the document analysis, the two `/analyze`
routes, the functions that composed metadata suggestions from a model, and
the three columns in the console's audit table that showed its verdict.

**SIMPL.** The EDC bridge and its two routes, the IAA bootstrap plan, the
`lab`/`live` environment, forwarding of the audit log to an external
governance service, and the labels that attributed each profile to a SIMPL
block.

**Advanced identity.** Verifiable credentials with their four routes and
`did:web` resolution with publication of the DID document. On the login
pages, the Cl@ve/eIDAS and EU Login cards with their handlers: they were
hidden by default, and the specification says none of that goes in "not even
disabled".

**Surplus infrastructure.** Vault, MinIO, Airflow and the observability
stack. Assets move from the object store to a disk volume, with the key
resolved against the folder so that a `..` cannot read the whole container.

**Verticals.** The urban dashboards, the Málaga case, the federated risk
panel, the article manifest and the diagrams of the original ecosystem, which
named FIWARE, Orion, NGSI-LD and the original brand.

**Traces of the current deployment.** The five domains, the public IP of a
VPS that was in the download smoke test, three real email addresses in the
RBAC account matrix, the OVH SMTP server, and Google analytics, which sent
data to a third party without anyone having asked for it.

### What is kept, because the specification keeps it

The full cycle of sign-up, publication, catalogue, negotiation and mediated
download. The two controls that provide the value: requiring a completed
negotiation to download and restricting delivery destinations. The log of
operations and denials — still signed and chained, but signed by the node's
own identity and not forwarded to anyone ([D-005](decisiones.md)). Fuseki with
TDB2 and the delta federator with its purge of orphaned graphs and its
DCAT-AP validator.

### The composition

From eighteen services to six: `caddy`, `app`, `connector`, `postgres`,
`keycloak` and `fuseki`. A single exposed port. The database, Keycloak,
Fuseki and the connector's management surface no longer show up on the host
machine. The realm is imported on startup with its roles, its groups, the
console client and the connector's service account: zero manual steps.

The federator now lives inside `app` ([D-006](decisiones.md)).

### The test

`tests/test_no_hidden_dependencies.py` is the forbidden-terms search that the
phase asked to leave behind as an automated test. It checks three things:
that not a single domain, email, IP or server path from the original
deployments remains; that nothing pruned has come back; and that
`.env.example` carries no secret with a value.

It searches for the terms **as words and not as substrings**, because
«minio» lives inside «dominio» (Spanish for "domain") and «ngsi» inside
«alongside»: a test that fails for that reason stops meaning anything and
ends up being disabled.

State of the suite: **53 pass, 8 skipped.** The 8 are the delta federator
ones, which need `jq`, and this machine does not have it; they run inside the
`app` image, which does install it.

### Startup, checked

`docker compose up -d` brings up the six containers and everything answers:

| Check | Result |
|---|---|
| The six containers running | ✅ `app`, `caddy`, `connector`, `postgres`, `keycloak`, `fuseki` |
| Portal through Caddy (`/`, `/styles.css`, `/app.js`, `/login.html`) | ✅ 200 |
| API through Caddy (`/api/onboarding/health`) | ✅ 200 |
| Keycloak through Caddy (`/auth/realms/dataspace/...`) | ✅ 200 |
| Path traversal (`/../../etc/passwd`) | ✅ 404 |
| Fuseki over the internal network | ✅ 200 |
| Connector surface over the internal network | ✅ 401 — it is up and requires identity |
| Connector surface from outside | ✅ not published |
| Realm imported: groups | ✅ `connector-users`, `dataspace-admins`, `dataspace-negotiators`, `dataspace-users` |
| Realm imported: roles | ✅ `connector-user`, `dataspace-admin`, `dataspace-negotiator`, `dataspace-user` |
| Connector service account | ✅ with its three roles, without a single manual step |

**Three real failures that only appeared when bringing it up:**

1. **Caddy did not start.** `{$ODS_DOMAIN::80}` only falls back to the default
   when the variable **is not defined**, and the composition always defines
   it. With `ODS_DOMAIN` empty the block key was left empty and Caddy read it
   as a second global block. The address is now resolved in the composition,
   with `${ODS_DOMAIN:-:80}`, which does fall back to the default when it is
   empty.

2. **Keycloak went into a restart loop:** the `keycloak` database did not
   exist. `db/01-create-databases.sql` came from the original and created six
   databases for three connectors and a wallet, none of them the one Keycloak
   needs.

3. **The portal answered 404.** In the original deployment the interface was
   served by a separate nginx, so the API answered 404 to anything that did
   not start with `/api`. Here there is no such nginx — there are six
   containers — and `app` is the one that has to serve it. It has been added,
   with the path checked against the resolved folder.

**And a hidden dependency that startup gave away:** the service tried to
register itself on every startup against `GOVERNANCE_API_BASE_URL`, an
external governance service, and announced it with a warning. It has gone
completely: the three functions and the `governance.env` file that fed them.
The three values read from there — public address, organisation name and
identity URL — now come from `ODS_PUBLIC_URL`, `ODS_ORG_NAME` and
`ODS_AUTH_URL`.

---

## Phase 3 — A single connector

**Done on 2026-08-27.**

The connector identifier comes from `ODS_CONNECTOR_ID`. The tables of three
predefined connectors — directory, profiles and static identifiers —
collapse to a single entry. The table of legacy redirects, which named three
accounts from the original deployment, is gone.

The `connector-2*` and `connector-3*` pages go; `connector-1*` becomes
`console.html` and `console-en.html`. **The console lives at a single
address** because the connector identifier is configurable and therefore
cannot be in the URL. The tabs are the ones the specification asks for:
Operation — with its two views, provider and consumption —, Audit, and Users
and requests.

`setup_keycloak_rbac.sh` creates one `connector-users` group and one service
account, not three of each.

---

## Phase 3b — Merged catalogue

**Done on 2026-08-27, except for the test with two real nodes.**

### The list of known nodes

The node's own entry always goes first and **is not stored**: it is composed
on every read, so that it does not go stale when `ODS_CONNECTOR_ID` or the
public address changes. Remote nodes are registered from the console with
`POST /api/v1/nodes`, removed with `DELETE /api/v1/nodes/<id>` and synced on
demand with `POST /api/v1/nodes/sync`, which is the «Refresh now» button.

Listing is public — it is who makes up this data space —; adding, removing
and forcing a sync require administrator identity.

### The federator

It lives inside `app`, in its own thread, and syncs every
`ODS_FEDERATION_INTERVAL` seconds. It is given the list through
`FEDERATION_NODES_FILE`; without it, it still accepts the fixed catalogue
configuration, which is how it runs standalone. **One named graph per node**,
so that removing one does not touch the rest of the store.

### Checked, actually started

| Check | Result |
|---|---|
| Seeding publishes the example | ✅ 2 assets, 2 policies, 2 contracts |
| And it is idempotent | ✅ the second time: `ya_existian=6`, no duplicates |
| The federator picks up the offer | ✅ `contributing=1`, 91 triples in `urn:ods:catalog/connector` |
| Download without a completed negotiation | ✅ 403 `completed negotiation required for this asset` |
| Registering a node without identity | ✅ 403 |
| A node that does not answer | ✅ it is marked `unreachable` and **does not empty the view of the others**: the own node's graph still has its 91 triples |
| Removing a node | ✅ takes its graph with it, and only its own |

### Four chained failures that only show up when starting it

1. **The connector answered 401 to everything.** It verified token signatures
   against `identity-hub:8080`, a service from the original deployment that
   does not exist here, and the failure was logged as
   `JWT validation failed: null`. Now the composition passes it the JWKS and,
   if it is missing, **it says so on startup** instead of keeping quiet.

2. **Keycloak issued tokens with the wrong issuer.** `KC_HOSTNAME` is a full
   URL and its path takes precedence over `--http-relative-path`: without
   `/auth` at the end, Keycloak issued `iss=<pública>/realms/…` while serving
   at `<pública>/auth/realms/…`, and the connector rejected all of them.

3. **The example files were not versioned.** The `data/` rule in `.gitignore`
   was not anchored, so it matched `seed/data/`. Whoever cloned the
   repository got a manifest pointing to files that are not there and two
   published products whose download gives 404 — worse than publishing none,
   because it looks as if it works. Anchored to `/data/`, and with
   `tests/test_seed_is_shippable.py` so that it does not come back.

4. **A script with CRLF does not start inside the container.** The federator
   returned `ok=False` without saying why: bash rejected it on its first line
   with `pipefail: invalid option name`. `.gitattributes` guarantees it for
   what goes into the repository but does not rewrite what was already on
   disk. Forty files normalised and `tests/test_line_endings.py` so that it
   does not come back — which has already caught two relapses of mine.

### The test with two nodes, done

A second complete node was brought up on the same machine — another Docker
project, other ports, another connector, its own volumes — and introduced to
the first one from the list of known nodes. The procedure is in
[dos-nodos.md](dos-nodos.md).

| Acceptance criterion | Result |
|---|---|
| **8** — the offer of two nodes on a single screen | ✅ `contributing=2`, 4 offers from 2 nodes in one query |
| **9** — shut down the second one and the view holds | ✅ it still shows the 4 offers; the neighbour is left `unreachable` **keeping the date of its last successful sync**, not the current one |
| Recovery | ✅ on starting it again, `unavailable=0` at the next sync |
| The portal during the outage | ✅ `/`, `/api/onboarding/health`, `/api/v1/nodes` and `/api/v1/catalog`, all 200 |

**How nodes federate with each other, and why it had to change.** The
original federator read the connector's management API with a Keycloak
token. That works within a node and is **impossible between organisations**:
node A has no credentials in node B's Keycloak, and publishing that surface
is exactly what section 3 does not do.

Each node now exposes `GET /api/v1/catalog`: public, read-only, and with only
the offer. No users, no requests, no operations log. That is what reduces
registering a node to typing its address. The own node is still read through
the management API with the service account; a remote node, through its
public catalogue.

**A failure that only appears with the second node shut down.** The
federator counted the downed node as `contributing=0` but `unavailable=0`, so
the console showed it as «disponible, sin ofertas» ("available, no offers")
— which reads as a node that has withdrawn its catalogue, not as one that is
not answering. They are different things and the operator has to be able to
tell them apart.

### The console

The **Known nodes** tab is in: add, remove, «Refresh now», and the table with
the status and the date of the last successful sync of each node. Tab
switching is no longer hard-wired to two: it is read from the DOM through
`aria-controls`, which is what the buttons already had to declare.

**The console is generated on every startup**, not served statically: it
carries inside it the list of nodes, the connector identifier and the profile
of whoever uses it, and all three change without anyone touching a file. The
`console*.html` files that travel in the repository are what is seen before
the first startup.

### The pass-through to the connector

The console needs to publish assets and open negotiations, and that lives in
the connector's management API, which **is not published**: Caddy has no
route to it and the service exposes no ports.

`/api/connector` reaches it over the internal network and **forwards the
caller's token as is**. It grants nothing: a token from another realm and a
made-up one get 401 from the connector itself. It only lets through the four
resources the console uses. `tests/test_connector_surface_is_not_published.py`
watches the four things that would turn it into a hole: that Caddy does not
route to the connector, that the connector does not publish ports, that the
allow-list does not grow and that the pass-through does not acquire
credentials of its own.

A leftover from the original deployment that nobody would have noticed was
also fixed: the console decided whether to filter resources by owner with
`/^connector-[123]$/`, the three identifiers of that deployment. In any other
installation that expression matches nothing.

**99 tests green**, 8 skipped because `jq` is missing on this machine.

### What is missing

Nothing from phases 3 and 3b. Next is phase 4 — reviewing that no hard-coded
deployment value is left — and 5, the first-start wizard and the installer,
which is where the ten-minute criterion is measured.

---

## Phase 4 — Configuration

**Done on 2026-08-27.**

The review found **three options declared in `.env.example` that nobody
read**. Setting them did nothing, which is worse than not offering them:
whoever set them believed they had changed something.

- **`ODS_TLS`.** Setting `off` with a domain still requested a certificate.
  The address is now computed by Caddy's startup, which does know how to
  branch between the three cases — no domain, domain with TLS, domain without
  TLS —. The composition cannot: it has no conditionals.
- **`ODS_SPARQL_PUBLIC`.** The query endpoint did not exist, either open or
  closed. It is now **closed by default and returns 404, not 403**: an
  endpoint that is not open has no reason to announce that it exists. When
  open, it only allows reading.
- **`ODS_ADMIN_PASSWORD`**, which still has no consumer on purpose: the
  installer uses it, and it is noted as pending in the drift test.

**A failure of my own in the "this is only a read" check.** It stripped
comments with `#[^
]*` and swallowed the hash of an IRI fragment, so any query with
`PREFIX dcat: <http://…/dcat#>` — that is, almost any query — was rejected
as if it were a write. Now the query is walked skipping IRIs and literals.
The test covers both sides: eleven reads that have to pass, including one
with `"insert data"` inside a literal, and twelve writes that must not,
including ones hidden behind a `PREFIX` and behind a comment that says
`select`.

**The administrator's email reaches its four places**: the realm's
administrator user, the certificate's ACME registration, the participant's
contact in the catalogue and the recipient of notifications.

**Drift test.** No variable that the code reads can be left undeclared, and
no declared one can be left without a consumer. The pending list empties
itself: there is a test that fails when a pending one already has something
reading it, so that the exceptions list does not stop meaning anything.

---

## Phase 5 — Wizard and installer

**Done on 2026-08-27.**

### The wizard

An unconfigured node sends **any** route to `/setup` — except the stylesheet
the wizard itself needs, without which the page comes out blank —. Four
steps: organisation, administrator, language and brand, confirmation. On
finishing it creates the administrator in Keycloak with their four groups,
saves the settings, regenerates the console and the brand, publishes the
example and marks the node as configured. From then on **`/setup` returns
404**.

The marker and the settings live in the state volume, not in the tree: if
they lived in the tree, every image upgrade would send the node back to the
setup screen.

### Two failures that only show up when using it

1. **Whoever reached the wizard before Keycloak had finished coming up got a
   raw `Connection refused`.** It does not say what happened or that waiting
   is enough. The wizard now checks whether identity is answering: it warns
   before you press Finish, and if you press it anyway the error says what to
   do. The check comes **before** writing anything, because failing halfway
   would leave settings saved with no administrator to use them.

2. **The wizard's settings reached the interface but not the backend.** The
   brand looked right — `runtime-config.js` is regenerated with it — while the
   catalogue kept publishing the name and email from `.env`. In other words:
   one of the four places the administrator's email has to reach was left
   with the example value, and nothing said so.

### The installer

`./install.sh` asks four things, derives the identifier from the name,
generates any missing service passwords, writes `.env` with 600 permissions,
brings up the composition, waits until the node **and identity** answer, and
says what to do next.

**It is idempotent, and that is tested.** An existing `.env` is not
overwritten — it holds the node's passwords, and regenerating them leaves the
database inaccessible —: it is reused and only the missing keys are added.
The second run detects that the node has already been through the wizard and
says so instead of sending you to a screen that returns 404.

Without an interactive terminal it does not ask: it takes the default values.
A script that questions a closed stdin hangs in CI.

### The ten-minute criterion

Measured, from zero to a published data product:

| Step | Time |
|---|---|
| `./install.sh` with the images already built | 52 s |
| Completing the wizard | 1 s |
| **Total** | **53 s** |

With the images already built. A machine that really starts from zero has to
build the Java connector, which takes several minutes; that goes away in
phase 6, when `docker compose pull` replaces the `build`. **That is the
walkthrough that has to be timed again once the images are published**,
because it is the one the README describes.

**150 tests green**, 8 skipped because `jq` is missing on this machine.

---

## Phase 6 — Images and release

**The workflow is done and tested. Publishing is Francisco's action, not
mine.**

### The namespaces, checked

Section 15 asked for this to be confirmed before this phase:

| | Status |
|---|---|
| Docker Hub `myopendataspace` | ✅ **free** — 404 as a user and as an organisation |
| GitHub `myopendataspace` | free, but not needed: `nekosphera` is used |
| `github.com/nekosphera/my-open-dataspace` | ⚠️ **already exists** — created on 2026-08-27 at 13:01 UTC, **empty**, and **already public**, with the description from section 10b |

The repository being empty is good: it does not clash with "a single initial
commit". It **already being public** changes the risk and is worth saying:
there is no intermediate step in which to push, look and correct. The first
`git push` publishes. The section 14 list has to be closed **before**, not
after.

### The gate

`.github/workflows/tests.yml` is the gate, and `release.yml` reuses it
instead of copying it: two different gates stop being a gate.

`tests/e2e/golden_path.py` checks the acceptance criterion against a node
that is really running, not a list of functions. **Thirteen checks, green
from scratch:**

| | |
|---|---|
| An unconfigured node sends you to the wizard | ✅ |
| The wizard completes | ✅ |
| Afterwards, `/setup` returns 404 | ✅ |
| Portal and console respond | ✅ |
| There is a published example product | ✅ |
| The catalogue declares the participant's contact | ✅ |
| Each product declares its policy and its contract | ✅ |
| The connector's administration API is not published | ✅ |
| The pass-through to the connector requires identity | ✅ |
| Downloading without a completed negotiation is rejected | ✅ |
| The SPARQL endpoint is closed by default | ✅ |

**"If the E2E fails, there is no release" stops being just a phrase.** The
job that builds declares `needs: pruebas`. `tests/test_release_gate.py`
watches the four ways of breaking it without anything raising an error — a
`continue-on-error` added on a Friday to unblock a release, an `if: always()`
on a whole job, removing the `needs`, or duplicating the gate instead of
reusing it — and it can tell a clean-up `always()`, which is correct, from
one that is not.

### The images

Three, always on GHCR and on Docker Hub when there are credentials. Intel and
ARM under the same tag; four tags per release (`1.2.3`, `1.2`, `1`,
`latest`); signed keylessly, against the workflow's own identity; with a
software bill of materials and provenance.

**Docker Hub is optional on purpose.** Without its two secrets the workflow
does not fail: it pushes only to GHCR and carries on. Whoever forks the
repository has to be able to cut their releases without credentials that are
not theirs.

**The vulnerability scan does not block.** It runs and its report is saved,
but it does not break the release: a known vulnerability in a dependency of
the base image turns up daily, and blocking every release for that leads —
always — to someone disabling the scan. A report that gets looked at is worth
more than a gate that ends up being removed. What does block is the full
walkthrough, because that depends on this repository's code.

### Evaluation mode

The all-in-one image does not ship Keycloak, and the connector requires a
valid token on every request: `rbacEnabled` only controls roles, not
authentication. An explicit mode was needed, and it is a security switch,
so:

- it is enabled **only** with the variable set to `true`, never by default;
- it switches itself off if it detects a configured identity provider or
  domain, because having both at once means someone has inherited it by
  accident from an evaluation template — and then it says so, instead of
  keeping quiet —;
- it is announced on the connector's startup and on the application's.

It does not appear in `.env.example`: putting it in the list of options of a
normal installation is inviting someone to try it "to see if that makes it
start".

### A failure of my own in the all-in-one Dockerfile

The Fuseki checksum check trimmed the hash by hand with `tr -d` and `sed`,
and since Apache publishes `<hash>  <fichero>`, the `tr` glued the file name
onto the end of the hash: **it never matched and the build always failed**,
for the wrong reason. `sha512sum -c` reads that format as is.

I also went as far as writing a made-up hash as the default value of an
`ARG`. That really would have been serious: a check that looks as if it
verifies and verifies nothing. It is gone.

### What is missing from this phase

**Publishing.** It requires Docker Hub credentials and pushing a tag to the
repository, which is moreover already public. Both are Francisco's
decisions.

**Timing the ten-minute walkthrough again** once the images are published:
today it is 53 seconds with the images already built locally, but the
walkthrough the README describes starts by downloading them.

**The scope notice** moves to `docs/alcance.md`, which is its only copy: it
was in the README, in the security policy and in each release's notes, and
three hand-kept copies diverge — the one that goes stale is always the one
someone reads —.

**167 tests green**, 8 skipped because `jq` is missing on this machine; in
CI they are not skipped.

---

## The all-in-one image, tested

`docker run -p 8080:8080 myopendataspace/my-open-dataspace` starts healthy,
is configured through the wizard, publishes the example and **passes the full
walkthrough: 14 checks**.

What matters most in that result: **"downloading without a completed
negotiation is rejected" still passes with authentication switched off.**
Evaluation mode removes identity, not the connector's controls. They are
different things and it was important to check that they had not been
confused.

The walkthrough asks which mode the node is in instead of assuming it: a node
without authentication and one with it look the same from outside until
someone tries something, so `/api/onboarding/health` declares it.

### Four failures that give no error at build time

The image came out, started and the portal answered 200 with the product
broken inside. Each one now has its check in
`tests/test_allinone_image.py`, which looks at the shape — bringing up the
image takes several minutes and does not fit in the quality gate —:

1. **PostgreSQL did not start.** The `postgres` user cannot write its log to
   the volume, which belongs to root. `pg_ctl` waited for a server that never
   came, and without an `|| true` the `set -e` took the script down without
   saying anything useful.
2. **Fuseki died twice in a row.** `--loc` does not create the store folder
   — it says "Does not exist" and exits — and without `FUSEKI_HOME` it looks
   for its `webapp` relative to the working directory.
3. **The connector did not run.** It is compiled with Java 21 and the image
   installed Debian's OpenJDK 17: `UnsupportedClassVersionError` in its log
   while the portal kept answering 200.
4. **The watchdog did not watch.** It detected the crash and ran `exit`
   inside a background subshell: it killed the subshell and left the
   container standing serving half a product, which is exactly what it exists
   to prevent.

And one of mine that was more misleading than the four: the Fuseki checksum
check trimmed the hash by hand, and since Apache publishes
`<hash>  <fichero>`, the `tr -d` glued the name onto the end of the hash and
it never matched. I also went as far as writing a made-up hash as the default
value of an `ARG` — a check that looks as if it verifies and verifies
nothing. `sha512sum -c` reads that format as is.

---

## Phase 7 — Documentation and customisation

**Done on 2026-08-27, except for the README screenshot.**

| | |
|---|---|
| [personalizacion.md](personalizacion.md) | Brand, profiles, use cases, nodes and language — and **what cannot be customised without touching code**, stated there so that nobody finds out halfway through a migration |
| [backup.md](backup.md) | What to save, what does not need saving, how to restore and how to check that the backup works **before** you need it |
| [dos-nodos.md](dos-nodos.md) | Bringing up two nodes and seeing federation |
| [publicar.md](publicar.md) | How a release is cut and how to verify an image |
| [alcance.md](alcance.md) | The only copy of the scope notice |
| `deploy/backup.sh` | The minimal backup script that section 6.3 asked for |

The README links the eight documents and says plainly that the images **are
not yet published**, so the `docker run` commands on the front page do not
resolve yet.

### What is missing

**The README screenshot.** I cannot take it from here. The node comes up and
the console responds, so it is a matter of opening `http://localhost:8080`
with the node running and saving an image of the console with the example
published.

**A third language** still goes through the templates. It is noted as a
limitation in personalizacion.md, not hidden.

**177 tests green**, 8 skipped because `jq` is missing on this machine.

---

## Phase 8 — Before pressing «public»

**Twelve of the fourteen points in section 14, closed and checked. The two
that remain are not ones I can close.**

The full list, point by point and with who stands behind it, is in
[revision/lista.md](revision/lista.md).

### First, because it changes the procedure

The target repository **already exists, is empty and is already public**.
There is no intermediate step: you cannot push, look at how it turns out and
correct. **The first `git push` publishes.**

That is why the local tree has no remote configured, and there is a test
that fails if someone adds one too early. It is not paranoia: configuring a
remote and pushing are two commands, and the second one does not ask.

### The secrets sweep

**detect-secrets 1.5.0** over the versioned files — not over the working
tree: what matters is what would be published, and a local `.env` is not
published —. Result in `.secrets.baseline`, triage in
[revision/secretos.md](revision/secretos.md).

**9 findings, all 9 false positives:** interface labels that contain the word
"password", and test passwords that are only given to a validator so that it
rejects them.

**What it did find, and was fixed.** The full walkthrough created the
administrator with a password written in the file. Against a throwaway node
that does not matter; against the node of someone who ran the walkthrough "to
see if it works" and then kept it, it does: that node would have an
administrator whose password is published. Now a different one is generated
on every run and it is not printed.

`tests/test_secret_scan.py` sweeps again and fails if something appears that
is not in the baseline — and also if the baseline carries findings that no
longer exist, because an exception that is no longer needed stops meaning
anything and gets in the way.

### The exception lists, watched

This is the design flaw that worried me most in this phase: **a test with an
exceptions list stops meaning anything as soon as someone adds an entry to
get unstuck on a Tuesday.** There are three lists and all three now have
their limit checked:

- **`PROSA`** — what may name SIMPL, Gaia-X, FIWARE, IDSA or EHDS — only
  admits documents and test files. Never code. A `.py` from `app/` in there
  would leave the pruning unchecked in that file forever.
- **The traces** — real domains, emails and IPs — **are never exempted**, not
  even inside a paragraph explaining why they are there. There is a test that
  reads the actual function, with `inspect`, and fails if it ever consults
  `PROSA`.
- **`PENDIENTES`**, in the configuration test, empties itself: it fails when a
  variable listed as pending already has something reading it.

### Issue templates

Two — a bug and an idea — and a configuration that **sends security problems
to a private channel** and disables blank issues. An issue is public from the
very first moment, and anyone's first reflex is to open one: without that
diversion, the first exploitable bug someone finds ends up published before
the fix exists.

The bug template asks for the logs and **warns to look at them before pasting
them**: they carry email addresses and machine names of whoever pastes them.

---

## What remains, and why I am not the one closing it

### 1. The README screenshot — done, and it found a hole

It is taken with `./deploy/capturas.sh`, in headless Chrome or Edge, against
a node configured as «Organización de Ejemplo» ("Example Organisation").

**What it showed had not been seen by any test:** the public portal was
still, in its entirety, the one from the original deployment — «espacio de
datos de salud urbana» ("urban health data space"), «indicadores sintéticos
de calidad ambiental, confort, afluencia, energía, incendios y radiación
electromagnética» ("synthetic indicators of environmental quality, comfort,
footfall, energy, fires and electromagnetic radiation") — with two big
buttons leading to pages the pruning had deleted. And the catalogue table
said «No se encontraron productos de datos federados» ("No federated data
products were found") on a node that had two published, because it read from
an external governance service this product does not have.

**The pruning looked at the code and not at the prose.** The forbidden-terms
sweep searched for `ehds`, `fhir`, `healthdcat`: none of them appear in a
paragraph written in Spanish about urban health. A failure that moreover
gives no error — an empty table reads as an answer, not as a fault —.

Fixed: portal rewritten in both languages, catalogue reading the
`/api/v1/catalog` of each known node, with a timeout per node and all at once
so that a slow one does not leave the page loading. And two new checks that
did not exist: **no link leads to a page that does not exist**, and **no page
talks about the pruned vertical**.

This is exactly what section 14 asks for a screenshot for.

### 2. The installation tested by someone other than the author

Section 14 asks for someone who has not seen the code to install this on a
clean machine following **only the README**. What I can say honestly:

- The full walkthrough passes — 14 checks — against the composition and
  against the all-in-one image.
- The installation from zero is timed: 53 seconds.
- **But I tested it, having written the code, and that is not what section 14
  asks for.** What a test of one's own never detects is the step one takes
  without thinking because one already knows how it works.

### 3. Squashing the history — done

`main` has **a single commit and it is the root commit**, as D-001 requires.
The squash did not change a single byte: the tree is the same object before
and after, `00bb8c08`.

**The working history is in the local branch `historia-de-trabajo`**, with
its 22 commits, and it is not pushed. Its messages document why each thing is
the way it is — the six failures that only show up when starting it, the three
options that were declared and did nothing, the four in the all-in-one image,
the `.gitignore` that took the example data with it — and that does not get
written again.

**Anything still missing from now on goes in with `git commit --amend`**, or
`main` stops having a single commit without anyone noticing. It is stated in
[revision/lista.md](revision/lista.md), with the one-line check.

### 4. Publishing

Configure the remote, push, and cut `v0.1.0`. All three publish and all three
are Francisco's decision.

**237 tests green**, 8 skipped because `jq` is missing on this machine.

---

## Released

**2026-08-27.** [github.com/nekosphera/my-open-dataspace](https://github.com/nekosphera/my-open-dataspace),
one commit, public, with `v0.1.0` cut.

### What CI found and this machine did not

The first push left the three jobs red. The gate did exactly what it was
built to do, and one of the four failures was serious.

**All the scripts were versioned as `100644`.** The development machine is
Windows and has `core.filemode=false`: `chmod +x` leaves no trace in the git
index. Here it made no difference. Whoever cloned on Linux or macOS ran into
this, on the first command in the README:

```
$ ./install.sh
bash: ./install.sh: Permission denied
```

And Caddy's startup died with `exec: permission denied` without saying why.
**It is exactly what the installation by another person was going to run
into.** CI got there first.

Now the bit is checked **on the freshly made clone**, which is where it
matters: a test that looks at the working tree of whoever wrote it never
detects this.

### And a failure of mine in a test, which is worse than the failure

`test_ningun_enlace_lleva_a_una_pagina_que_no_existe` **passed locally for
the wrong reason.** `runtime-config.js` is generated on startup and is not in
the tree; on my machine it had been left over from a previous run, so the
file existed and the test passed. In a clean clone, it did not.

A test that depends on the leftovers of a previous run checks nothing, and
the worst part is that it gives confidence. Now the list of generated files is
explicit, and there is another test that checks that something really
generates them — because an exception that does not correspond to anything
real is a hole shaped like a comment.

The other two were minor: the `historia-de-trabajo` checks failed in CI,
where that branch does not exist because it is not pushed; and shellcheck
warned about a `source` with a variable path in the federator, which is
exactly what allows it to run standalone.

### Release 0.1.0, cut and checked

All jobs green. The three images on GHCR, **public and for Intel and ARM**,
signed with the workflow's identity and with their software bill of
materials.

**The published image was downloaded and passed the full walkthrough: 14
checks.** Not the one built on the development machine: the one CI built and
the one anyone will pull.

### Two more failures, and both of shape

**The vulnerability scan blocked the release, and it should not have.**
`docs/publicar.md` said it does not block; the wiring said
`needs: [imagenes, vulnerabilidades]`. The `exit-code: "0"` I set only stops
trivy failing *because it found something* — it does nothing for a failure
of the job. And the job failed because of an action version that does not
exist (`trivy-action@0.28.0`; its tags carry a `v`). Result: **the three
images pushed and the release skipped**, which is the worst of both worlds.

Now `publicacion` depends only on `imagenes`, and there is a test that fails
if the document and the workflow diverge again: if someone puts
`vulnerabilidades` back into the `needs`, **or** if the document stops saying
that it does not block.

**The README offered an image that does not exist.** `myopendataspace/...` on
Docker Hub gives 404: the workflow pushes there only if its two secrets
exist, and they do not. A `docker run` on the front page that does not
resolve is the first impression of whoever arrives. The test that watched
this checked that the README said "not yet published" — when they were
published the phrase disappeared and the test failed, rightly but for the
opposite of what it was watching. Rewritten to check what matters: **that
the README does not offer an image that is not published**, with the list of
empty registries made explicit.

### The only thing left

**The installation by someone other than the author**, cloning from GitHub
and following only the README. Francisco does it from another machine.

What is being looked for there is not that it works: it is where someone who
does not know how it works trips up. The execute bit was of that kind, and it
is gone; the ones left will be of the same kind.

---

## 27 August 2026 — What you see when you open a browser

A real Chrome was driven against `/login.html` and `/console.html`, which is
how the product is used. A chain of failures appeared that no API test could
see, because they all called the correct routes directly without running the
page's JavaScript: the console could neither read nor publish anything — its
calls went to `/api/connector/management/v3/…` and the pass-through only
accepted `/api/connector/v3/…` —; whoever administers the node logged in fine
and landed on the public page; there was no screen on which to approve a
sign-up; approving one took the publishing tab away from the whole node; the
operations log called a function that does not exist; and publishing was not
possible because the console sent a metadata prefix from the original
project. The details are in the CHANGELOG.

**Verified in the browser**, with the two-container installation running:
sign-up through the form, approval from the console, login by whoever signed
up, publication of a data asset with its policy and its contract, federation
with «Refresh now» and appearance in the merged catalogue. These are the
sixteen checks in `tests/e2e/navegador_alta_y_acceso.py`.

**Not verified yet, and it has to be said:** negotiating and downloading
against **another** node from the console. The peer-to-peer path —
`requestNegotiation` against the provider node's address — is now the only
one there is, and the destinations come from the merged catalogue, but that
is tested with two nodes running and here there was only one.
`docs/dos-nodos.md` explains how to set them up.

**The connector does not know how to delete an asset.** There is no `DELETE`
in its administration API, so what has been published cannot be withdrawn.
It is not new today, but it came up when trying to clean up some test assets:
they remain on the local test node, out of the public catalogue because they
have no contract.

---

## 27 August 2026, later — One node, one connector

A second participant signed up on the node could not negotiate: the console
marked all the assets as their own. And they are. Sign-up minted one
connector identifier per person, which section 4 of the specification orders
removed; behind it there was nothing but the node's single EDC. It has been
removed: signing up means joining the node's connector, and that is what the
sign-up page and the server's response now say.

**Negotiating is between nodes.** It is criterion 8 of section 12 and
`docs/dos-nodos.md` explains it. A node on its own does not negotiate with
itself.

Pulling on that thread, two misplaced permissions came out, both fixed and
checked in the browser: any approved person could approve and deny other
people's sign-ups, and signing someone up as a provider made them an
administrator of the node.

**Verified in the browser**, twenty checks in
`tests/e2e/navegador_alta_y_acceso.py`: besides the sign-up, login, approval
and publishing walkthrough, that whoever has a provider profile lands on the
console, publishes on the node's connector, does **not** see the sign-up
approval screen and gets a 403 if they request it on their own.

**The brand colour** is now applied: the stylesheet had its palette written
by hand and nobody read the chosen value. The status colours do not follow
the brand, on purpose.

**Still not verified**, the same as yesterday: negotiating and downloading
against another node from the console. It needs two nodes up.

---

## 28 August 2026 — The full walkthrough, on a single node

Yesterday I blocked negotiation of one's own offer, taking that to be
correct. It was wrong: criterion 6 of section 12 asks for exactly that —
publishing a product and, **from the consumption view of the same node**,
negotiating its contract and downloading the data. With the block, that
criterion could not be met, either by whoever published or by whoever had
just signed up.

With the block removed, two things that were underneath came out: the console
guessed the owner of each resource from the identifier's name — inherited
from the three-connector deployment — and returned owners that do not exist;
and **downloading a product hosted on the node itself had never worked**,
because the connector cannot resolve its own node's public URL from inside.

**Verified in the browser**, twenty-four checks: sign-up, approval, login,
publication with policy and contract, federation, appearance in the merged
catalogue, **negotiation from the consumption view and download of the
data**. And downloading without a completed negotiation is still rejected,
checked with a freshly created account: 403.

**Still not verified**: negotiating and downloading against another node from
the console: it needs two nodes up.

### The «Known nodes» tab, gone

Removed from the console at the request of whoever runs the product, with its
code intact: it is switched off in `visibleFor.operationNodesPanel` and is
switched back on in the same place. It applies to the console that travels in
the repository and to the one each node generates, because both load the
same `app.js`.

Register another node through the API in the meantime — `POST /api/v1/nodes`
—; it is in `docs/dos-nodos.md`, `docs/personalizacion.md` and the README,
all three corrected so as not to send anyone to a tab that no longer exists.

### The README screenshots

Both are taken from a node brought up on purpose for that, with an example
organisation and email, and thrown away afterwards. The participant one
cannot come from the developer's node: it would carry their email and their
organisation's name into a public repository, which is exactly what section
14 forbids.

Taking that screenshot revealed that **the `hidden` attribute did not hide
the buttons**: any author rule with `display` beats the browser's, and they
all have one. The tab that had just been removed was still being drawn, and
the sign-up approval one was being shown to people who cannot use it. The
test looked at the attribute and that is why it did not see it; it now looks
at the width it takes up on screen.

---

## 28 August 2026 — One connector per participant

The specification said "a single connector" and yesterday it was pruned
accordingly. Today it has been amended — section 16 of the Notion page — and
the product follows it: each authorised participant has their own.

**Verified in the browser**, fifteen checks in
`tests/e2e/navegador_conector_por_participante.py`: two people on the same
node, each with their connector in the header of their console and their
email as owner; one publishes an asset, policy and contract; the other does
not see them among their own but does see them in the data space catalogue,
**attributed to the first person's connector**; accepts the policy, completes
the negotiation and downloads the data. And a consumer who tries to publish
gets a 403.

None of this is visible without opening a browser: the identifier travels as
a signed claim, the console reads it to know who is looking, and the
catalogue attributes each offer to its participant.

**The limit, stated plainly.** It is still six containers. Each participant's
connector is an identity within the same EDC runtime: they share process,
database and port. The separation is of data and permissions, not of
resources. It is in the README and in D-015.

**Migration.** An already installed node fixes itself on startup: the claim
goes into the imported realm and each account receives its connector. Checked
against the development node, which had two people in it.

### The offer is visible when it is born, not five minutes later

Removing the known nodes tab took «Refresh now» with it, which was the only
way not to wait for the federator. It was noticed as soon as a participant
published: neither their neighbours nor they themselves could see their
offer.

Federating is now a consequence of creating the contract, and the node does
it in the pass-through to the connector — not the console —, so it works for
any client.

The end-to-end test was hiding it: it had a step in which whoever administers
the node federated by hand. That step has been removed, and with it removed
the test failed until the fix was on the server. A test that does on its own
what the product should do by itself does not test the product.
