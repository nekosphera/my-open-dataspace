# Secrets scan

**Tool:** [detect-secrets](https://github.com/Yelp/detect-secrets) 1.5.0
**Scope:** the versioned files. Not the working tree: what matters is what
would be published, and a local `.env` or a `.pytest_cache` is not published.

Two are left out of the scan, and for the same reason: **they exist to talk
about the scan, so scanning them duplicates every finding.** The baseline
stores the hashes — finding them there would declare them new findings, and
each regeneration would produce a baseline different from the previous one,
indefinitely — and this very page quotes the code it explains. Nothing is
hidden: what they quote is scanned in its source file, which is where it
matters.

```bash
python -m detect_secrets scan \
  $(git ls-files \
      | grep -v -e '\.secrets\.baseline' -e 'revision/secretos\.md') \
  > .secrets.baseline
```

**Result: 9 findings, all 9 false positives.** Each one, with why:

## `app/ui/setup.html` — 4

Lines 96, 97, 106 and 117. They are the translations of the wizard's
interface:

```js
l_password: "Password",
h_password: "Nine characters or more, with an upper-case letter, a digit and a symbol.",
weak_password: "The password does not meet the requirements.",
```

Labels and error messages. The word "password" next to a string, which is
exactly the pattern the tool looks for.

## `app/ui/registration.js` — 2

Lines 11 and 24, the same thing: the message shown to someone whose password
does not meet the profile, in Spanish and in English.

## `tests/test_first_run_wizard.py` — 3

Lines 74, 76 and 77. They are the cases the wizard **has to reject**:

```python
({"orgName": "X", "adminEmail": "a@b.org", "adminPassword": "corta"}, "weak_password"),
({"orgName": "X", "adminEmail": "a@b.org", "adminPassword": "sinmayusculas1!"}, "weak_password"),
```

They never reach any system: the test loads the module with its state in a
temporary directory, without Keycloak, and checks that validation rejects
them before writing anything.

---

## What the scan did find, and was fixed

**`tests/e2e/golden_path.py` created the administrator with a password
written in the file** — `Prueba2026!`. Against a throwaway node it makes no
difference. Against the node of someone who ran the walkthrough "to see if it
works" and then kept it, it does: that node has an administrator whose
password is published in the repository.

Now a different one is generated on each run and it is not printed.

## How it is maintained

`.secrets.baseline` is versioned and `tests/test_secret_scan.py` compares it
with the tree: **it fails when a finding appears that is not in the
baseline**. That is what stops the baseline becoming a rug to sweep things
under, which is the fate of every exceptions list nobody looks at.

To scan again after a legitimate change, the command above. And **explain
here** each new finding before accepting it: a baseline without this page
next to it is a list of things someone decided to ignore without saying why.
