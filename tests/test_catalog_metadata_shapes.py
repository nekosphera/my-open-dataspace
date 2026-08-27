"""The shapes the catalogue advertises must be the shapes it applies.

`validate_catalog_metadata` returned the path of
profiles/dcat-ap/1.0.0/shapes.ttl in every response,
so a caller could reasonably believe their metadata had been checked against
it. Nothing read that file. What the service actually did was compare the
submitted keys against a list of the same ten paths restated in Python, and
treat a value outside a controlled vocabulary as a warning, while the shape
declared it a violation.

Two descriptions of one profile is the shape of defect this ecosystem keeps
finding: a list of connectors beside a list of ports, a backup enumeration
beside the files it was supposed to cover. So the shapes are executed now, and
the test below refuses the two descriptions drifting apart.

Requirement Req.-BB-DSO-002 of the DSSC Catalogue self-assessment asks whether
the service provides validation mechanisms ensuring the data product conforms
to data model specifications. This is what makes the answer true.
"""
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = ROOT / "app" / "requirements.txt"


def load_api():
    spec = importlib.util.spec_from_file_location(
        "onboarding_api", ROOT / "app" / "onboarding_api.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


try:
    API = load_api()
    IMPORT_ERROR = None
except Exception as error:  # pragma: no cover - reported by the test below
    API = None
    IMPORT_ERROR = error


COMPLETE = {
    "dct:identifier": "urn:ods:dataset:parking-occupancy",
    "dct:title": "Parking occupancy",
    "dct:description": "Surface parking occupancy, refreshed every minute",
    "dct:publisher": "Organización de ejemplo",
    "dct:license": "https://creativecommons.org/licenses/by/4.0/",
    "dct:accessRights": "public",
    "dcat:theme": "https://example.org/theme/transport",
    "dcat:keyword": "parking,mobility",
    "dcat:mediaType": "application/json",
    "ods:deliveryMode": "api",
}


@unittest.skipIf(API is None, f"the onboarding API could not be imported: {IMPORT_ERROR}")
class CatalogMetadataShapesTest(unittest.TestCase):
    def violations(self, result):
        return [
            (item["path"], item["constraint"])
            for item in result["shapeConformance"]["violations"]
        ]

    def test_the_profile_matches_the_shapes(self):
        # The drift guard. If someone adds a property to shapes.ttl and not to
        # the Python profile, or the other way round, this is where it stops.
        profile = API.METADATA_PROFILE_DESCRIPTIONS["ods-dcat-ap-1.0.0"]
        expectations = API.shape_expectations()
        self.assertEqual(sorted(profile["required"]), sorted(expectations["required"]))
        self.assertEqual(
            {key: sorted(values) for key, values in profile["controlledValues"].items()},
            {
                key: sorted(values)
                for key, values in expectations["controlledValues"].items()
            },
        )

    def test_the_shapes_are_executed_and_the_response_says_by_what(self):
        # A response that names a shapes file without running it is the defect
        # this module exists for.
        conformance = API.validate_catalog_metadata(COMPLETE)["shapeConformance"]
        self.assertEqual(conformance["engine"], "pyshacl")
        self.assertEqual(
            conformance["shapes"],
            "profiles/dcat-ap/1.0.0/shapes.ttl",
        )

    def test_complete_metadata_conforms(self):
        result = API.validate_catalog_metadata(COMPLETE)
        self.assertTrue(result["ok"], result)
        self.assertEqual(self.violations(result), [])

    def test_a_missing_required_property_is_refused(self):
        metadata = dict(COMPLETE)
        del metadata["dcat:mediaType"]
        result = API.validate_catalog_metadata(metadata)
        self.assertFalse(result["ok"])
        self.assertIn("dcat:mediaType", result["missing"])
        self.assertIn(
            ("dcat:mediaType", "sh:MinCountConstraintComponent"),
            self.violations(result),
        )

    def test_a_value_outside_the_controlled_vocabulary_is_refused(self):
        # This is a deliberate tightening. It used to pass with a warning,
        # while the shape said sh:in.
        metadata = dict(COMPLETE)
        metadata["dct:accessRights"] = "whatever-the-caller-felt-like"
        result = API.validate_catalog_metadata(metadata)
        self.assertFalse(result["ok"])
        self.assertIn(
            ("dct:accessRights", "sh:InConstraintComponent"), self.violations(result)
        )

    def test_the_published_manifests_still_conform(self):
        # Los datos de ejemplo que un nodo publica solo en el primer arranque,
        # no una prueba escrita para pasar. Si el perfil se aprieta y deja de
        # admitirlos, falla aqui y no en la cara de quien acaba de instalar.
        checked = 0
        for manifest in sorted(ROOT.glob("seed/manifest.json")):
            for entry in self.dcat_entries(json.loads(manifest.read_text(encoding="utf-8"))):
                with self.subTest(manifest=manifest.name, title=entry.get("dct:title")):
                    result = API.validate_catalog_metadata(entry)
                    self.assertTrue(result["ok"], self.violations(result))
                    checked += 1
        self.assertGreater(checked, 0, "no published metadata was found to check")

    def dcat_entries(self, node, found=None):
        found = [] if found is None else found
        if isinstance(node, dict):
            if any(key.startswith(("dct:", "dcat:")) for key in node):
                found.append(node)
            for value in node.values():
                self.dcat_entries(value, found)
        elif isinstance(node, list):
            for value in node:
                self.dcat_entries(value, found)
        return found


class TheServiceUsesThePackageTest(unittest.TestCase):
    """The validation lives in federation/ and the service imports it.

    Two copies of one profile is what this module was written to stop. The
    extraction is only worth something while the service keeps consuming the
    package instead of growing its own copy back.
    """

    def setUp(self):
        self.service = (ROOT / "app" / "onboarding_api.py").read_text(encoding="utf-8")

    def test_the_service_imports_the_package(self):
        self.assertIn("from catalejo.profile import", self.service)

    def test_the_service_carries_no_second_engine(self):
        for token in ("pyshacl", "run_shacl", "rdflib"):
            with self.subTest(token=token):
                self.assertNotIn(token, self.service)

    def test_the_deployment_ships_the_package(self):
        """La imagen tiene que llevar dentro el paquete que el servicio importa.

        Sin esto, el servicio arranca en el contenedor y se cae en el primer
        import: la validacion vive en federation/ y el Dockerfile es el unico
        sitio que decide si esa carpeta viaja o no.
        """
        dockerfile = (ROOT / "app" / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("COPY federation/", dockerfile)
        self.assertIn("COPY profiles/", dockerfile)


class EngineIsPinnedTest(unittest.TestCase):
    def test_production_installs_the_engine(self):
        # The container installs this file at start and refuses to run if the
        # install fails, so pinning it here is what makes the check reachable
        # in production rather than only on a developer machine.
        requirements = REQUIREMENTS.read_text(encoding="utf-8")
        self.assertIn("pyshacl", requirements)
        self.assertIn("rdflib", requirements)


if __name__ == "__main__":
    unittest.main()
