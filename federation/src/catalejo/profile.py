"""Validate data product metadata against a DCAT-AP profile and its shapes.

This is the validation half of Catalejo, extracted from the MyDataSpace
onboarding API so that it can be shipped and used on its own. Nothing here
knows about participants, credentials, contracts or connectors: it takes a
metadata record and a profile, and answers whether the record conforms.

The profile is described twice by nature - as the SHACL shapes that decide
conformance, and as the list of required keys that produces a readable "these
are missing" answer. The shapes are the authority: the keys are read from them
rather than restated, and what SHACL says is what decides `ok`.

Requirement Req.-BB-DSO-002 of the DSSC Catalogue self-assessment asks whether
the service provides validation mechanisms ensuring the data product conforms
to data model specifications. This is that mechanism.
"""
import time

try:
    import rdflib
    from pyshacl import validate as run_shacl
except ImportError:  # pragma: no cover - a deployment installs both
    rdflib = None
    run_shacl = None


SHAPE_TARGET_CLASS = "dcat:Dataset"
SHAPE_NAMESPACES = {
    "dcat": "http://www.w3.org/ns/dcat#",
    "dct": "http://purl.org/dc/terms/",
    "ods": "urn:ods:",
    # So a violation reads sh:MinCountConstraintComponent in the response
    # instead of a full URI nobody scans.
    "sh": "http://www.w3.org/ns/shacl#",
}
# Only this one is split; the others are single values that may legitimately
# contain a comma.
SHAPE_MULTIVALUED = {"dcat:keyword"}


def metadata_aliases():
    """What a publisher may call each term before it is normalised."""
    return {
        "dct:identifier": ["identifier", "id", "@id"],
        "dct:title": ["name", "title"],
        "dct:description": ["description", "summary", "notes"],
        "dct:publisher": ["publisher", "provider", "organization"],
        "dct:license": ["license", "licenseUrl", "licence"],
        "dct:accessRights": ["accessRights", "access", "access_rights"],
        "dcat:theme": ["theme", "category"],
        "dcat:keyword": ["keywords", "tags"],
        "dcat:mediaType": ["mediaType", "contenttype", "contentType", "format"],
        "ods:deliveryMode": ["deliveryMode", "delivery_mode"],
    }


def metadata_value(metadata, key):
    metadata = metadata if isinstance(metadata, dict) else {}
    for candidate in [key] + metadata_aliases().get(key, []):
        if candidate in metadata:
            return metadata.get(candidate)
    return None


def expand_term(term):
    prefix, _, local = str(term).partition(":")
    base = SHAPE_NAMESPACES.get(prefix)
    return base + local if base else str(term)


def shorten_term(uri):
    for prefix, base in SHAPE_NAMESPACES.items():
        if str(uri).startswith(base):
            return prefix + ":" + str(uri)[len(base):]
    return str(uri)


def utc_now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class CatalogueProfile:
    """A metadata profile: its shapes, and what they expect."""

    def __init__(self, shapes_path, descriptor=None, shapes_id=None):
        self.shapes_path = shapes_path
        # What the responses name. Never the filesystem path: an API answer
        # that carries /opt/<product>-releases/<sha>/... tells every caller
        # how the host is laid out.
        self.shapes_id = shapes_id or getattr(shapes_path, "name", str(shapes_path))
        self.descriptor = descriptor or {}
        self._graph = None
        self._expectations = None

    # -- the shapes ---------------------------------------------------------
    def shapes_graph(self):
        if self._graph is None:
            graph = rdflib.Graph()
            graph.parse(self.shapes_path, format="turtle")
            self._graph = graph
        return self._graph

    def expectations(self):
        """What the shapes require, read from the shapes rather than restated."""
        if self._expectations is not None:
            return self._expectations
        sh = rdflib.Namespace(SHAPE_NAMESPACES["sh"])
        graph = self.shapes_graph()
        required, controlled, datatypes = [], {}, {}
        target = rdflib.URIRef(expand_term(SHAPE_TARGET_CLASS))
        for shape in graph.subjects(sh.targetClass, target):
            for constraint in graph.objects(shape, sh.property):
                path = graph.value(constraint, sh.path)
                if path is None:
                    continue
                name = shorten_term(path)
                minimum = graph.value(constraint, sh.minCount)
                if minimum is not None and int(minimum) >= 1:
                    required.append(name)
                datatype = graph.value(constraint, sh.datatype)
                if datatype is not None:
                    datatypes[name] = str(datatype)
                allowed = graph.value(constraint, sh["in"])
                if allowed is not None:
                    controlled[name] = [str(item) for item in graph.items(allowed)]
        self._expectations = {
            "required": required,
            "controlledValues": controlled,
            "datatypes": datatypes,
        }
        return self._expectations

    # -- the record ---------------------------------------------------------
    def metadata_graph(self, metadata):
        """The submitted metadata as the dcat:Dataset the shapes expect."""
        expectations = self.expectations()
        graph = rdflib.Graph()
        subject = rdflib.BNode()
        graph.add(
            (subject, rdflib.RDF.type, rdflib.URIRef(expand_term(SHAPE_TARGET_CLASS)))
        )
        for name in expectations["required"]:
            value = metadata_value(metadata, name)
            if value is None or value == "" or value == []:
                continue
            if isinstance(value, list):
                items = value
            elif name in SHAPE_MULTIVALUED:
                items = str(value).split(",")
            else:
                items = [value]
            datatype = expectations["datatypes"].get(name)
            for item in items:
                item = str(item).strip()
                if not item:
                    continue
                literal = (
                    rdflib.Literal(item, datatype=rdflib.URIRef(datatype))
                    if datatype
                    else rdflib.Literal(item)
                )
                graph.add((subject, rdflib.URIRef(expand_term(name)), literal))
        return graph

    def conformance(self, metadata):
        """Apply the shapes, or say plainly that they were not applied."""
        if rdflib is None or run_shacl is None:
            return {
                "ok": False,
                "engine": None,
                "shapes": self.shapes_id,
                "reason": "no SHACL engine is installed, so the shapes were not applied",
                "violations": [],
            }
        conforms, results, _report = run_shacl(
            self.metadata_graph(metadata),
            shacl_graph=self.shapes_graph(),
            inference="none",
            advanced=False,
        )
        sh = rdflib.Namespace(SHAPE_NAMESPACES["sh"])
        violations = []
        for result in results.subjects(rdflib.RDF.type, sh.ValidationResult):
            path = results.value(result, sh.resultPath)
            component = results.value(result, sh.sourceConstraintComponent)
            violations.append(
                {
                    "path": shorten_term(path) if path is not None else "",
                    "constraint": shorten_term(component)
                    if component is not None
                    else "",
                    "message": str(results.value(result, sh.resultMessage) or "").strip(),
                }
            )
        violations.sort(key=lambda item: (item["path"], item["constraint"]))
        return {
            "ok": bool(conforms),
            "engine": "pyshacl",
            "shapes": self.shapes_id,
            "violations": violations,
        }

    def validate(self, metadata):
        """Whether the record conforms, and everything needed to fix it."""
        metadata = metadata if isinstance(metadata, dict) else {}
        expectations = self.expectations()
        required = expectations["required"]
        controlled = expectations["controlledValues"]

        missing = []
        for key in required:
            value = metadata_value(metadata, key)
            if value is None or value == "" or value == []:
                missing.append(key)

        warnings, recommendations = [], []
        normalized = {key: metadata_value(metadata, key) for key in required}

        theme = str(normalized.get("dcat:theme") or "").strip()
        if theme and not (
            theme.startswith("http://") or theme.startswith("https://") or "." in theme
        ):
            warnings.append("dcat:theme should use a registered URI or controlled code")
        for key in controlled:
            value = str(normalized.get(key) or "").strip()
            if value and value not in controlled[key]:
                warnings.append(f"{key} is outside the profile's controlled values")
        license_url = str(normalized.get("dct:license") or "").strip()
        if license_url and not (
            license_url.startswith("http://") or license_url.startswith("https://")
        ):
            warnings.append("dct:license should be a resolvable URL")

        keywords = normalized.get("dcat:keyword")
        if isinstance(keywords, str):
            keyword_count = len([item for item in keywords.split(",") if item.strip()])
        elif isinstance(keywords, list):
            keyword_count = len([item for item in keywords if str(item).strip()])
        else:
            keyword_count = 0
        if keyword_count and keyword_count < 2:
            recommendations.append(
                "add at least two dcat:keyword values for federated discovery"
            )
        access_rights = str(normalized.get("dct:accessRights") or "").strip()
        delivery_mode = str(normalized.get("ods:deliveryMode") or "").strip()
        if access_rights in {"contractual-dashboard", "controlled-governed-reuse"} and not delivery_mode:
            recommendations.append(
                "set ods:deliveryMode so policy enforcement can choose the right contract path"
            )

        conformance = self.conformance(metadata)
        total_checks = len(required) + 4
        penalty = (
            len(missing) * 10
            + len(conformance["violations"]) * 10
            + len(warnings) * 4
            + len(recommendations) * 2
        )
        score = max(0, min(100, 100 - int((penalty / max(total_checks, 1)) * 10)))
        return {
            # Both halves must hold: the keys are present and the shapes accept
            # the values.
            "ok": (not missing) and conformance["ok"],
            "profile": self.descriptor.get("id", ""),
            "checkedAt": utc_now(),
            "missing": missing,
            "warnings": warnings,
            "recommendations": recommendations,
            "score": score,
            "normalized": normalized,
            "vocabularies": self.descriptor.get("vocabularies", []),
            "shapes": self.descriptor.get("shapes", [self.shapes_id]),
            "shapeConformance": conformance,
        }
