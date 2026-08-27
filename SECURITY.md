# Security policy

## Reporting a vulnerability

Report security issues privately through GitHub's **Report a vulnerability**
button on the Security tab of this repository. Do not open a public issue for
anything that could be exploited before a fix exists.

Include, as far as you can: the version or commit, how to reproduce it, and
what an attacker gains.

## Response

- **Acknowledgement:** within 5 working days.
- **First assessment:** within 15 working days, including whether we consider
  it a vulnerability and a rough severity.
- **Fix or mitigation:** targeted within 90 days of the acknowledgement.
  If it takes longer we say so and explain why.

We credit reporters in the release notes unless asked not to.

## Scope

This project ships a self-hosted deployment. The node an operator installs is
theirs to secure: the network it sits on, the strength of the passwords it is
given, and who can reach its console.

In scope: defects in this repository's code, its default configuration, its
container build, and its installation script.

Out of scope: vulnerabilities in upstream components reported without an
accompanying defect here — take those upstream; findings that require an
operator to have already granted the attacker administrator access; the
all-in-one evaluation image, which is documented as not for production.

## What this project does not claim

The project demonstrates concrete publication, discovery, negotiation,
transfer and evidence scenarios. It does not certify conformance, does not
guarantee universal interoperability, and does not accredit membership of
SIMPL, Gaia-X, FIWARE, IDSA or EHDS.

Full text in [docs/alcance.md](docs/alcance.md), which is the only copy.
