# Decisions taken during implementation

The product decisions are settled in the specification. Only the ones the
specification did not cover are recorded here, resolved by choosing the
simplest option that meets the acceptance criteria.

Format: what was decided, why, and what would have to change if it were
decided the other way.

---

## D-001 — History: one commit per phase during development, a single commit on release

**Decision.** Work proceeds with one commit per phase, as the execution rule
requires. Before the repository is made public (phase 8) everything is
squashed into a single initial commit.

**Why.** The two requirements —"commit at the end of each phase" and "a single
initial commit"— refer to different moments: the first to development, the
second to the published tree. Squashing at the end satisfies both and keeps
traceability while the work is in progress.

**If it were decided the other way.** We would have to give up being able to
review phase by phase, or publish a development history that adds nothing for
whoever installs it.

---

## D-002 — The federated catalogue is taken from the `catalejo` repository, not from `mydataspace/catalogue`

**Decision.** `federation/` comes from the public `catalejo` repository.

**Why.** `mydataspace` kept a vendored copy in `catalogue/` that only contains
the profile library and the smoke test. The original repository also brings
the federator, the DCAT-AP and ODRL vocabularies with their SHACL shapes, and
the log rotation configuration. It is the complete tree and it is the one that
receives the upstream improvements.

**If it were decided the other way.** The federator and the vocabularies would
have to be rebuilt by hand, which is exactly what the specification asks not
to do.

---

## D-003 — The working tree lives in `repos/my-open-dataspace`

**Decision.** The new repository is created alongside the source ones, in its
own directory, with no git relationship to any of them.

**Why.** It makes it obvious that it is an independent tree and that the
source ones are not touched.

---

## D-004 — The vocabulary moves to `urn:ods:` instead of a domain

**Decision.** The namespace of the project's own terms, and the identifiers of
the profiles and their SHACL shapes, stop being `https://www.<dominio>/ns#`
URLs and become `urn:ods:` IRIs.

**Why.** A vocabulary IRI does not have to resolve, and neither of the two
alternatives worked: keeping the source domain publishes a production address
in a public repository, and inventing a new one —`myopendataspace.org`— claims
a domain the project does not own and that someone could register and use. A
`urn:` does not require owning anything or keeping a server alive for a
catalogue to keep validating.

**If it were decided the other way.** The domain would have to be bought and
maintained, and the profile documents published on it, so that the only
advantage —that a reader can paste the IRI into a browser— actually existed.

---

## D-005 — A `urn:` for the identity that signs the audit log

**Decision.** The operations log is signed by `AUDIT_ISSUER`, which comes from
`ODS_PUBLIC_URL` or, failing that, from `ODS_ORG_ID`. Previously it was signed
by a DID resolved via `did:web` against a domain of our own.

**Why.** Section 9 prunes `did:web` resolution, but section 9 also explicitly
keeps "the log of operations and denials viewable from the console". Both are
satisfied at once if the log stays signed and chained and the signer is the
node itself, which is the only identity whoever installs it controls.

**If it were decided the other way.** Going back to the DID requires whoever
installs to own a domain and publish a `did.json` document on it, which is
exactly the kind of prerequisite the five-minute install cannot have.

---

## D-006 — The federator lives inside `app`, not in a seventh container

**Decision.** The catalogue federator runs inside the `app` container.

**Why.** Section 3 fixes six containers and no more. The federator needs
exactly what `app` already has: the sync interval, the list of known nodes and
the console's "Refresh now" button. Moving it to a container of its own means
duplicating that configuration and inventing a channel for the button.

**If it were decided the other way.** There would be seven containers, against
the specification, in exchange for being able to restart the federator without
restarting the portal — which is not a problem this product has.

---

## D-007 — The deployment probe and the account matrix are removed from RBAC

**Decision.** `setup_keycloak_rbac.sh` no longer brings a matrix of users and
creates a single account: the one for `ODS_ADMIN_EMAIL`. The probe account
that the interface walkthrough used disappears.

**Why.** The matrix carried three real email addresses written into the code.
The probe was derived from the domain of the first of them, a mechanism that
only makes sense when one repository serves several domains at once; here each
node is one.

**If it were decided the other way.** A probe address would have to be
invented, which is either on an example domain —and then the email does not
arrive— or on the installer's domain without them having asked for it.

---

## D-008 — The node console is a single one and shows what the node can do

**Decision.** `write_connector_pages` always generates the console with the
provider **and** consumer profile. It is no longer generated with the profile
of the person just approved. What each person can do is decided by their
token, and what enforces it is the connector's RBAC: read with
`dataspace-user`, write with `dataspace-admin`, negotiate with
`dataspace-negotiator`.

**Why.** The console is a single file shared by the whole node —the code
itself says so when it retires a connector: "The console is not deleted: there
is only one and the whole node shares it"—. Generating it with one person's
profile applied it to everyone: approving a consumer took the publish tab away
from whoever administers the node, and the form, although still in the HTML,
could no longer be submitted because it lived inside a hidden panel with
required fields. You only see it by logging in.

**If it were decided the other way.** A console per person would have to be
generated —`console-<quien>.html`, served according to the token— or the
capabilities decided in the browser instead of when generating the page. The
latter is the right thing going forward; the former multiplies a generated
file per participant. Right now, whoever clicks something that is not theirs
to use gets the connector's 403, which says which role is missing, and the
console shows it as is.

---

## D-009 — The public catalogue only broadcasts what has a contract

**Decision.** `/api/v1/catalog` leaves out assets that no contract definition
covers. They remain visible to their owner under "View my assets", which reads
from the connector directly.

**Why.** An asset without a contract is not offered: nobody can negotiate it
and the connector would reject it. Broadcasting it sends every neighbouring
node an offer that does not exist, and it happens to anyone who creates the
asset and has not yet created its contract —a normal intermediate step in the
console—.

**If it were decided the other way.** The catalogue would be an inventory
instead of an offer, and whoever reads it from another node would have to
negotiate to discover that there was nothing to negotiate.

---

## D-010 — There is a test that opens a browser

**Decision.** `tests/e2e/navegador_alta_y_acceso.py` drives Chrome through the
DevTools protocol and is part of the integration gate. If there is no browser,
it exits with code 2 and the step warns that it was skipped; it never shows up
as green.

**Why.** The API tests called the correct routes directly and passed green
while the console could neither read nor publish anything, whoever
administered the node landed on the public page and there was no screen at all
on which to approve a sign-up. None of those three things can be seen without
running the page's JavaScript, and running it means opening a browser.

**If it were decided the other way.** Exactly the failures this product has
had would be left outside the gate: the ones that sit between the browser and
the server, and not inside either of them.

---

## D-011 — A sign-up is a participant of the node's connector, not a new connector

**Decision.** Sign-up no longer generates `connector-<sha1 del correo>` with
its client, its wallet, its registry and its participant. Whoever signs up
joins the connector the node already has, with the profile they requested.

**Why.** The specification settles it in two places: decision 5 of section 2
and section 4. That identifier was not a connector —there is a single EDC per
node—, but a label; and since the merged catalogue attributes each offer to
the node that publishes it, the newly signed-up person saw every asset as
their own and could not negotiate anything. The product had told them they
had a connector.

**If it were decided the other way.** One EDC per participant would have to be
started, with its port, its database and its identity, which is exactly what
the non-goal "the second and third connector" rules out for v0.1.

---

## D-012 — Publishing and administering the node are two different permissions

**Decision.** Role `dataspace-provider` and group `dataspace-providers`. The
connector accepts `dataspace-provider` or `dataspace-admin` for writing.
Approving sign-ups stays only in `dataspace-admins`.

**Why.** They were the same thing: to let someone publish you had to put them
in `dataspace-admins`, and that group gave permission to approve and deny
other people's sign-ups and read the data of whoever was waiting. On top of
that, `REQUEST_REVIEWER_GROUPS` included `connector-users`, which every
approved person joins, so in practice anyone could review sign-ups.

**If it were decided the other way.** A node with two providers would have two
administrators, and there would be no way to sign someone up to publish
without also giving them the list of pending requests.

---

## D-013 — The connector reaches its own node from the inside

**Decision.** The connector receives `EDC_UPSTREAM_PUBLIC_URL` and
`EDC_UPSTREAM_INTERNAL_URL` and translates the first into the second before
fetching the data. The list of allowed destinations is checked **against the
declared address**, not against the translated one.

**Why.** An asset hosted on the node carries its public address, and it has
to: that is the one that travels in the federated catalogue and the one
another node uses. From the connector's container that address does not lead
to the portal. Without the translation, downloading any product from the node
itself —the sample one included— always fails.

**The order matters, and that is why there is a test.** If the translation
happened before checking the list, declaring an asset pointing at the public
prefix would be enough to reach any internal route, and the check would say
yes to something it has not looked at.

**If it were decided the other way.** The internal address would have to be
stored in the `dataAddress` and the public one in the metadata, which fixes
what the server writes but not what a person publishes by pasting the public
URL of a file they have uploaded to this same node —which is the usual case—.

---

## D-014 — The "Known nodes" tab is not offered in this release

**Decision.** The button disappears from the console. The panel, its
registration form, the list with each node's last sync and "Refresh now"
**stay in the page and in the code**, intact and tested. It is switched off in
a single place: `visibleFor.operationNodesPanel` in `initOperationTabs`.
Offering it again is changing that `false` to `true`.

**Why.** The product owner asks for it for this release. The door is closed,
the room is not demolished: deleting it would mean rewriting it entirely for
the next version, and what is there works.

**What is lost in the meantime.** The only way from the interface to register
another node, which is what criterion 8 of section 12 needs. Periodic
federation keeps running with the nodes already registered, and the routes are
still there: `POST /api/v1/nodes`, `POST /api/v1/nodes/sync` and
`DELETE /api/v1/nodes/<id>`. `docs/dos-nodos.md` explains the procedure with
them.

**If it were decided the other way.** Deleting the panel would leave the tree
cleaner and would cost rebuilding it entirely when it is needed again; the
cost of keeping it is a panel nobody sees.

---

## D-015 — One connector per participant, inside the node's runtime

**Decision.** Each authorised participant has their own connector. The
separation is of data and permissions: `connector_id` in the connector's
tables, stamped from the token claim and filtered on read. There is no
container per person.

**This replaces D-011**, which said the opposite —a sign-up is access to the
node's connector— following decision 5 of section 2 as it was written.
Amendment 16 to the specification, of 28 August 2026, changes that decision.

**Why this way and not with a container per participant.** Section 3 fixes six
containers. A container per person requires dynamic orchestration from inside
the node —the Docker socket mounted into `app`, ports, a database and an OIDC
client per connector—, which is a large privilege surface in exchange for an
isolation that is not needed here: what separates two participants is that
they neither see nor touch each other's things, and the column and the filter
provide that.

**Where the limit is, stated so that nobody gets a surprise.** They share a
process, database and port. A connector failure stops all of them. There is no
resource isolation between participants. The README says so.

**Who sees the whole node.** `dataspace-admin`, via `EDC_CATALOG_ROLES`. That
is what lets the service account compose the node's public catalogue, and it
is what belongs to whoever operates it.
