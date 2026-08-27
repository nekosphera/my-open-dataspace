# Before pressing "public"

The section 14 checklist, point by point, with who checks each one.

> **Published on 2026-08-27** at
> [github.com/nekosphera/my-open-dataspace](https://github.com/nekosphera/my-open-dataspace):
> one commit, 108 files, public.
>
> What this list checked before pushing is checked just the same afterwards:
> the same tests run on every change, and the one that required there to be
> no remote now requires the only one to be the destination. A remote added
> for a test and forgotten publishes the work into someone else's repository.

## What is already checked

Each line is backed by a test that runs in the quality gate, not by a check by
eye. `tests/test_ready_to_publish.py`, except where another is given.

| Section 14 point | Status | What backs it |
|---|---|---|
| Automatic secrets scan, with its result saved | ✅ | `.secrets.baseline` + `test_secret_scan.py` |
| "No hidden dependencies" test green | ✅ | `test_no_hidden_dependencies.py` |
| `docs/procedencia.md` complete, with repository and commit | ✅ | `test_ready_to_publish.py` |
| Not a single real IP, domain, server path or email | ✅ | `test_no_hidden_dependencies.py` |
| No trace of the origin brand in the code | ✅ | `test_no_hidden_dependencies.py` |
| Licence and attributions in place | ✅ | |
| README with the three installation paths | ✅ | |
| Security policy with a channel **and concrete deadlines** | ✅ | |
| Contribution guide and code of conduct | ✅ | |
| Issue templates | ✅ | |
| Scope notice, verbatim and visible in the README | ✅ | |
| README with a screenshot | ✅ | |
| No commit inherited from the origin repositories | ✅ | |
| No portal link leads to a page that does not exist | ✅ | `test_the_portal_is_the_product.py` |
| No page talks about the pruned vertical | ✅ | `test_the_portal_is_the_product.py` |

### The secrets scan

9 findings, **all 9 false positives**, each one explained in
[secretos.md](secretos.md). They are interface labels that carry the word
"password" and test passwords that are only given to a validator so that it
rejects them.

**What it did find, and was fixed:** the full walkthrough created the
administrator with a password written in the file. Against a throwaway node
it makes no difference; against the node of someone who ran it "to see if it
works" and then kept it, it does. Now a different one is generated on each
run and it is not printed.

## The screenshot — done, and what it showed

It is taken with `./deploy/capturas.sh` against a node that is up and
configured as "Organización de Ejemplo". It uses Chrome or Edge in headless
mode: nothing needs installing, if you have got this far you have a browser.
And it refuses to capture a node that has not yet been through the wizard,
because then every page redirects to `/setup` and the three screenshots would
come out identical.

**What the screenshot showed, and no test had seen:** the public portal was
still, in its entirety, the one from the origin deployment. "Espacio de datos
de salud urbana" (urban health data space), "indicadores sintéticos de calidad
ambiental, confort, afluencia, energía, incendios y radiación
electromagnética" (synthetic indicators of environmental quality, comfort,
footfall, energy, fires and electromagnetic radiation), and two big buttons
that led to pages the pruning had deleted. And the catalogue table said "No se
encontraron productos de datos federados" (no federated data products found)
on a node that had two published, because it read from an external governance
service that this product does not have.

The pruning looked at the code — imports, routes, dependencies — and did not
look at the prose. The forbidden-terms scan searched for `ehds`, `fhir`,
`healthdcat`: none of them appears in a paragraph written in Spanish about
urban health.

It is fixed — portal rewritten, catalogue reading from the real nodes — and
it is now guarded by `tests/test_the_portal_is_the_product.py`, which checks
two things that had never been checked: that **no link leads to a page that
does not exist**, and that **no page talks about the pruned vertical**.

This is exactly why section 14 asks for a screenshot.

## What is missing, and I cannot close myself

### 1. The installation tested by someone other than the author

Section 14 asks for someone who has not seen the code to install this on a
clean machine following **only the README**, and this is what I can honestly
say:

- The full walkthrough passes — **14 checks** — against the compose setup and
  against the all-in-one image.
- The from-zero installation is timed: **53 seconds** from `./install.sh` to
  a published data product.
- But I tested it, and I wrote the code. **That is not what section 14 asks
  for, and it cannot be taken as equivalent.** What your own test never
  catches is the step you take without thinking because you know how it works.

Someone else still has to do it.

### 2. Timing it again once the images are published

The 53 seconds are with the images already built locally. The walkthrough the
README describes starts by downloading them, and that has not been measured
yet.

## The history — done

`docs/decisiones.md` D-001: commits per phase during development, a single
initial commit on publishing.

**`main` has a single commit, and it is the root commit.** It is checked like
this:

```bash
git rev-list --max-parents=0 HEAD    # tiene que dar el mismo sha que HEAD
```

(*The comment reads: "must give the same sha as HEAD".*)

**The working history has not been lost: it is in the local branch
`historia-de-trabajo`, with its 22 commits.** It is not pushed. Its messages
document why each thing is the way it is — the six failures that only show up
on startup, the three options that were declared and did nothing, the four in
the all-in-one image, the `.gitignore` that swept away the sample data with
it — and that does not get written again.

The squash did not change a single byte of the content: the tree is the same
object before and after, `00bb8c08`. If it ever needs redoing:

```bash
git checkout historia-de-trabajo
git branch historia-de-trabajo-2
git checkout --orphan publicacion
git add -A && git commit
git branch -M publicacion main
```

### What remains to be done goes **inside** that commit

The README screenshot and whatever comes out of the installation by someone
else are changes still to come. If they are added as new commits, `main` stops
having just one and the property is lost without anyone noticing.

```bash
git add -A
git commit --amend --no-edit
```

And if the change deserves telling, `historia-de-trabajo` is where it is told.

## The order

| | Step | Status |
|---|---|---|
| 1 | The README screenshot | ✅ done |
| 2 | Squash the history | ✅ done |
| 3 | Configure the remote and push | ✅ **done on 2026-08-27** |
| 4 | Cut `v0.1.0` | ⬜ publishes the images |
| 5 | Someone else installs from scratch following only the README | ⬜ Francisco does it from another machine |

Step 5 is now done against the published repository, which is the real test:
clone from GitHub and follow the README, with nothing from this machine.

Steps 4 and 5 publish, and step 4 cannot be undone: the destination repository
is already public. Before them, this list has to be entirely green —
including the two points I cannot close myself.
