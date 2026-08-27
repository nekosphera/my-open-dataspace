# Contributing

Thanks for looking. This project is a self-hosted data space that an
organisation installs, brands and fills with its own use cases. The best
contributions are the ones that make that easier.

## Before you write code

Open an issue first for anything beyond a typo. It saves you from building
something that does not fit, and it saves us from reviewing it.

Two rules shape most decisions here and are not up for negotiation in a pull
request:

1. **No hidden dependencies.** Nothing in this repository may point at a
   private repository, a private registry, a specific server, a production
   domain, or any service the installer does not control. A freshly installed
   node must work with what is in the tree plus public images. There is an
   automated test for this and it is part of the quality gate.
2. **No hard-coded deployment values.** Domains, e-mail addresses,
   organisation names, colours, paths and identifiers belong in `.env` or in
   the first-run wizard, never in the source.

## Working on it

```bash
git clone https://github.com/nekosphera/my-open-dataspace
cd my-open-dataspace
./install.sh          # writes .env and brings the stack up
```

Run the tests before you push:

```bash
python -m pytest tests
```

The end-to-end test is the one that matters. If it fails, the change is not
ready — we do not cut a release on a red end-to-end run.

## Pull requests

- One concern per pull request.
- Explain what breaks if the change is wrong, not just what it does.
- If you touched behaviour, a test should fail without your change.
- Commit messages in the imperative, describing the effect.

## Code style

Match the file you are editing. Python is formatted with `ruff format`, shell
scripts pass `shellcheck`, and Java follows the layout already in
`connector/`.

## Licence

By contributing you agree that your contribution is licensed under
Apache-2.0, the licence of this repository.
