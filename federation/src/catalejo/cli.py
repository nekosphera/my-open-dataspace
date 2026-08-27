#!/usr/bin/env python3
"""Validate a metadata record against the catalogue profile, from a terminal.

    python3 -m catalejo.cli vocabularies/dcat-ap/1.0.0/shapes.ttl dataset.json

Exit code 0 when the record conforms, 1 when it does not, so it can gate a
publication pipeline without anybody parsing prose.
"""
import argparse
import json
import sys
from pathlib import Path

from catalejo.profile import CatalogueProfile


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("shapes", type=Path, help="the SHACL shapes of the profile")
    parser.add_argument("metadata", type=Path, help="a JSON metadata record")
    arguments = parser.parse_args(argv)

    profile = CatalogueProfile(
        arguments.shapes, shapes_id=arguments.shapes.name
    )
    record = json.loads(arguments.metadata.read_text(encoding="utf-8"))
    result = profile.validate(record)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
