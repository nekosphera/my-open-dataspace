#!/usr/bin/env python3
"""A data space small enough to run in a smoke test.

The federator needs two things it cannot invent: a token endpoint to
authenticate against, and a connector that answers the EDC management API.
This is both, in the standard library, answering fixed fixtures. It exists so
that the quickstart can be proved end to end without standing up Keycloak and
a connector — and a quickstart nobody has run is a README, not a quickstart.

    python3 smoke/stub_dataspace.py --port 8099

It is a fixture. It authenticates nobody and authorises nothing.
"""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ASSETS = [
    {
        "@id": "asset-air-quality",
        "properties": {
            "name": "Air quality, hourly",
            "description": "Hourly air quality readings from street cabinets",
            "language": "en",
            "publisher": "Example City",
            "licenseUrl": "https://creativecommons.org/licenses/by/4.0/",
            "accessRights": "public",
            "theme": "https://example.org/theme/environment",
            "dcat:keyword": ["air", "quality", "environment"],
            "dcat:mediaType": "application/json",
            "ods:deliveryMode": "api",
        },
        "dataAddress": {"baseUrl": "https://connector.example.org/data/air-quality"},
    }
]

POLICIES = [{"@id": "policy-open", "policy": {"name": "Open reuse"}}]
CONTRACTS = [
    {
        "@id": "contract-air-quality",
        "accessPolicyId": "policy-open",
        "contractPolicyId": "policy-open",
    }
]


class Handler(BaseHTTPRequestHandler):
    def answer(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path.endswith("/protocol/openid-connect/token"):
            length = int(self.headers.get("Content-Length") or 0)
            self.rfile.read(length)
            return self.answer({"access_token": "stub-token", "expires_in": 300})
        return self.answer({"error": "not_found"}, 404)

    def do_GET(self):
        if self.path.startswith("/management/v3/assets"):
            return self.answer(ASSETS)
        if self.path.startswith("/management/v3/policydefinitions"):
            return self.answer(POLICIES)
        if self.path.startswith("/management/v3/contractdefinitions"):
            return self.answer(CONTRACTS)
        return self.answer({"error": "not_found"}, 404)

    def log_message(self, *_args):
        # The smoke run has its own narration; this would only be noise.
        return


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8099)
    arguments = parser.parse_args()
    server = ThreadingHTTPServer(("0.0.0.0", arguments.port), Handler)
    print(f"[stub] a data space of one connector on :{arguments.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
