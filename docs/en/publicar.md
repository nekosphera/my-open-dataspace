# Cutting a release

## How it is cut

Tag it. Nothing else:

```bash
git tag v0.1.0
git push origin v0.1.0
```

That triggers `.github/workflows/release.yml`, which does four things **in
this order and without skipping any**:

1. Runs the whole quality gate —`tests.yml`, including the full walkthrough
   against a real running node—.
2. Builds and pushes the three images, for Intel and ARM, signed and with
   their software bill of materials.
3. Scans for vulnerabilities and keeps the report.
4. Creates the release with its notes.

**If the full walkthrough fails, there is no release.** That is not just a
phrase: the job that builds declares `needs: pruebas`, so a red run prevents a
single image from being pushed. `tests/test_release_gate.py` watches that
this stays true, because it breaks in ways that raise no error —a
`continue-on-error` added on a Friday to unblock a release, an
`if: always()`, removing the `needs`— and each of them leaves the workflow
green while publishing something that has not gone through the gate.

## The three images

| Image | What for |
|---|---|
| `ghcr.io/nekosphera/my-open-dataspace` | All-in-one, evaluation and teaching. It is the one the README links to. |
| `ghcr.io/nekosphera/app` | Portal, console, API and federator. For the compose stack. |
| `ghcr.io/nekosphera/connector` | The EDC connector. For the compose stack. |

**Docker Hub is pending.** The workflow pushes there too, under the
`myopendataspace` namespace —which is free—, but only if the two repository
secrets exist; today they do not, so v0.1.0 went out to GHCR only. It is
deliberate that this does not break the release: whoever forks this
repository does not have those credentials and has to be able to cut their
own releases.

**Tags.** Each release goes out with four: `1.2.3`, `1.2`, `1` and `latest`.
Whoever wants reproducibility pins the full one; whoever wants automatic
patches and no surprises pins the minor one.

## Verifying an image before using it

The images are signed with the identity of the workflow itself —no keys to
keep or rotate—, so you can check which repository and which workflow each
one came from:

```bash
cosign verify \
  --certificate-identity-regexp 'https://github.com/nekosphera/my-open-dataspace/.*' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  ghcr.io/nekosphera/app:0.1.0
```

And its provenance and bill of materials:

```bash
gh attestation verify oci://ghcr.io/nekosphera/app:0.1.0 --owner nekosphera
```

## The all-in-one image

```bash
docker run -p 8080:8080 myopendataspace/my-open-dataspace
```

Portal, connector, PostgreSQL and Fuseki in one container. **No identity
provider, no TLS and no authentication**: anyone who can reach the port can
publish, negotiate and download. It says so on startup, with a banner that
fills half the screen, and it cannot be left like that by accident: evaluation
mode switches itself off if it detects a configured identity or domain,
because having both at once means somebody has inherited it from a template
without noticing.

It is what a container should not do —four processes, no per-process restart,
a failure in any of them takes the container down— and that is why it exists
only for evaluation. The six-container compose stack is the one you install.

## What needs configuring on GitHub

For GHCR, nothing: the workflow uses the token GitHub already gives it.

For Docker Hub, two secrets in the repository:

- `DOCKERHUB_USUARIO`
- `DOCKERHUB_TOKEN` — an access token, not the account password.

**Without them the workflow does not fail**: it pushes only to GHCR and
carries on. This is deliberate, so that whoever forks the repository can cut
their own releases without having credentials that are not theirs.

## The vulnerability scan does not block

It runs on every release and its report is kept as an artifact, but it does
not break the release. A known vulnerability in a dependency of the base
image turns up every day, and blocking every release over that leads
—always— to somebody disabling the scan. A report that gets read is worth
more than a gate that ends up being removed.

What does block is the full walkthrough, because that does depend on the code
in this repository.
