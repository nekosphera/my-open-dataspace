"""The federator must write only what changed.

It used to rebuild the catalog on every run - stage a full copy, drop the live
graph, copy the staged one over it - once every fifteen minutes. TDB2 reclaims
nothing until it is compacted, so a catalog that never changed still grew the
store without limit: a node reached 17 GB holding 371 triples.

These tests drive the delta logic directly, with the two HTTP helpers replaced
by stubs that record what would have been sent, so "nothing changed" can be
asserted as "nothing was written" rather than inferred.
"""
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "federation" / "federator" / "federate-catalogues.sh"

HARNESS = r"""
set -Eeuo pipefail
export FUSEKI_BASE_URL=http://stub FUSEKI_DATASET=stub
export FUSEKI_ADMIN_USER=stub FUSEKI_ADMIN_PASSWORD=stub
export CONNECTOR1_NAME=stub CONNECTOR1_URL=http://stub
# The script parses its own arguments when loaded, so it is sourced with none.
set --
source ./federation/federator/federate-catalogues.sh

# Every update the run would send, one file each, so an empty directory is
# proof that nothing was written.
sparql_update() {
  local n
  n=$(find "$UPDATES_DIR" -type f | wc -l)
  printf '%s' "$1" >"$UPDATES_DIR/update-$n.sparql"
}

sparql_select_json() {
  case "$1" in
    *STRSTARTS*)
      printf '{"results":{"bindings":[]}}'
      ;;
    *)
      # Apply the query's own FILTER, the way the server would. Without this
      # the stub would hand back the marker the query excludes, and the test
      # would be measuring the stub rather than the federator.
      local excluded
      excluded=$(printf '%s' "$1" |
        sed -n 's/.*STR(?s) != "\([^"]*\)".*/\1/p' | head -1)
      jq -c --arg excluded "$excluded" \
        '.results.bindings |= map(select($excluded == "" or .s.value != $excluded))' \
        "$CURRENT_JSON"
      ;;
  esac
}

DESIRED_FILE="$DESIRED_LINES"
sync_graph "urn:dataspace:catalog/stub" stub http://stub 1 0 0
"""

CATALOG = [
    ("urn:dataspace:stub:asset:a1", "urn:edc:assetId", "a1", "literal"),
    ("urn:dataspace:stub:asset:a1", "urn:edc:name", "Parking", "literal"),
]


def bindings(triples):
    return json.dumps(
        {
            "results": {
                "bindings": [
                    {
                        "s": {"type": "uri", "value": s},
                        "p": {"type": "uri", "value": p},
                        "o": {"type": kind, "value": o},
                    }
                    for s, p, o, kind in triples
                ]
            }
        }
    )


def model(triples):
    return "".join(
        json.dumps({"s": s, "p": p, "o": o, "t": kind}, separators=(",", ":")) + "\n"
        for s, p, o, kind in triples
    )


class DeltaFederationTest(unittest.TestCase):
    def sync(self, current, desired):
        bash = shutil.which("bash")
        if not bash:
            self.skipTest("bash is not available")
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            updates = base / "updates"
            updates.mkdir()
            (base / "current.json").write_text(current, newline="\n")
            (base / "desired.jsonl").write_text(desired, newline="\n")
            result = subprocess.run(
                [bash, "-s"],
                input=HARNESS,
                capture_output=True,
                text=True,
                cwd=ROOT,
                env={
                    "PATH": subprocess.os.environ.get("PATH", ""),
                    "UPDATES_DIR": str(updates),
                    "CURRENT_JSON": str(base / "current.json"),
                    "DESIRED_LINES": str(base / "desired.jsonl"),
                },
            )
            if result.returncode != 0:
                if "missing dependency" in result.stderr:
                    self.skipTest(result.stderr.strip())
                self.fail(f"harness failed: {result.stderr.strip()}")
            return sorted(p.read_text() for p in updates.iterdir()), result.stdout

    def test_an_unchanged_catalog_writes_nothing(self):
        updates, output = self.sync(bindings(CATALOG), model(CATALOG))

        self.assertEqual(updates, [])
        self.assertIn("nothing written", output)

    def test_a_new_asset_is_inserted_without_rewriting_the_rest(self):
        added = CATALOG + [
            ("urn:dataspace:stub:asset:a2", "urn:edc:assetId", "a2", "literal")
        ]
        updates, _ = self.sync(bindings(CATALOG), model(added))

        self.assertEqual(len(updates), 1)
        # The asset that did not change is not touched.
        self.assertIn("urn:dataspace:stub:asset:a2", updates[0])
        self.assertNotIn("DELETE DATA", updates[0])
        self.assertNotIn("urn:dataspace:stub:asset:a1", updates[0])

    def test_a_difference_longer_than_the_log_does_not_kill_the_run(self):
        # The change log printed the first twenty entries by piping jq into
        # head. With pipefail, head stopping made jq die of SIGPIPE and took
        # the run with it - exit 141, after the update had already been
        # written, so the catalogue was correct and the run reported failure.
        # It survived while differences were small enough to fit in the pipe
        # buffer before head exited.
        many = [
            (f"urn:dataspace:stub:asset:a{index}", "urn:edc:assetId", f"a{index}", "literal")
            for index in range(60)
        ]
        updates, _ = self.sync(bindings([]), model(many))
        self.assertEqual(len(updates), 1)
        self.assertIn("INSERT DATA", updates[0])

    def test_a_withdrawn_asset_is_deleted_rather_than_left_behind(self):
        updates, _ = self.sync(bindings(CATALOG), model(CATALOG[:1]))

        self.assertEqual(len(updates), 1)
        self.assertIn("DELETE DATA", updates[0])
        self.assertIn('"Parking"', updates[0])

    def test_the_marker_never_makes_an_unchanged_run_write(self):
        # The old marker carried the run's own timestamp inside the catalog
        # graph, so every run differed from the last by construction. It is
        # compared separately now and rewritten only when the catalog moved.
        stored = CATALOG + [
            (
                "urn:dataspace:catalog/stub/sync",
                "urn:edc:lastChangedAt",
                "2026-08-18T00:00:00Z",
                "literal",
            )
        ]
        updates, output = self.sync(bindings(stored), model(CATALOG))

        self.assertEqual(updates, [])
        self.assertIn("nothing written", output)

    def test_a_changed_catalog_refreshes_the_marker_in_the_same_update(self):
        added = CATALOG + [
            ("urn:dataspace:stub:asset:a2", "urn:edc:assetId", "a2", "literal")
        ]
        updates, _ = self.sync(bindings(CATALOG), model(added))

        # One request, so the catalog is never visible without its marker.
        self.assertEqual(len(updates), 1)
        self.assertIn("urn:edc:lastChangedAt", updates[0])
        self.assertNotIn("urn:edc:syncedAt", updates[0])

    def test_quotes_and_backslashes_survive_the_round_trip(self):
        awkward = [
            (
                "urn:dataspace:stub:asset:a1",
                "urn:edc:name",
                'He said "hi" \\ bye',
                "literal",
            )
        ]
        updates, _ = self.sync(bindings([]), model(awkward))

        self.assertIn('\\"hi\\"', updates[0])
        self.assertIn("\\\\ bye", updates[0])

    def test_iri_objects_are_written_as_iris_not_literals(self):
        contract = [
            (
                "urn:dataspace:stub:contract:c1",
                "urn:edc:asset",
                "urn:dataspace:stub:asset:a1",
                "uri",
            )
        ]
        updates, _ = self.sync(bindings([]), model(contract))

        self.assertIn("<urn:edc:asset> <urn:dataspace:stub:asset:a1> .", updates[0])

    def test_sync_graph_receives_every_argument_it_reads(self):
        # A lost line continuation once left this call with three of its six
        # arguments, and the federator died in production on "$4: unbound
        # variable". Neither bash -n nor the delta tests can see it: both
        # halves parse, and both halves are only reached through ingestion.
        lines = SCRIPT.read_text().splitlines()
        index = next(
            (i for i, line in enumerate(lines) if line.strip().startswith("sync_graph ")),
            None,
        )
        self.assertIsNotNone(index, "the federator never calls sync_graph")

        call = lines[index]
        while call.endswith("\\"):
            index += 1
            call = call[:-1] + " " + lines[index]

        self.assertEqual(len(re.findall(r'"[^"]*"', call)), 6, call)

    def test_the_staging_graph_is_gone_from_the_federator(self):
        script = SCRIPT.read_text()

        # No run stages a full copy any more, so no run can leave one behind.
        self.assertNotIn(".sync-${FEDERATION_RUN_ID}", script)
        self.assertNotIn("ADD GRAPH", script)
        self.assertNotIn("DROP SILENT GRAPH <${graph_iri}>", script)
        # It still clears the ones earlier versions left behind.
        self.assertIn("drop_orphan_sync_graphs", script)


if __name__ == "__main__":
    unittest.main()
