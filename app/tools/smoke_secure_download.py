#!/usr/bin/env python3
import argparse
import json
import ssl
import sys
import urllib.parse
import urllib.request


def request_json(url, headers=None, data=None, method=None, insecure=False, timeout=20):
    ctx = ssl._create_unverified_context() if insecure else None
    req = urllib.request.Request(url, headers=headers or {}, data=data, method=method)
    with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def request_raw(url, headers=None, insecure=False, timeout=20):
    ctx = ssl._create_unverified_context() if insecure else None
    req = urllib.request.Request(url, headers=headers or {})
    return urllib.request.urlopen(req, context=ctx, timeout=timeout)


def get_access_token(args):
    payload = urllib.parse.urlencode(
        {
            "grant_type": "password",
            "client_id": args.client_id,
            "client_secret": args.client_secret,
            "username": args.username,
            "password": args.password,
        }
    ).encode("utf-8")

    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    if args.token_host:
        headers["Host"] = args.token_host

    token_json = request_json(
        args.token_url,
        headers=headers,
        data=payload,
        method="POST",
        insecure=args.insecure,
        timeout=args.timeout,
    )
    return token_json["access_token"]


def pick_paper_asset(assets):
    papers = [a for a in assets if str(a.get("id") or a.get("@id") or "").startswith("paper-")]
    if not papers:
        raise RuntimeError("No paper assets found")
    return papers


def main():
    parser = argparse.ArgumentParser(
        description="Smoke test for the mediated download: direct is refused, negotiated is served."
    )
    parser.add_argument("--ip", default="127.0.0.1", help="Address the node answers on")
    parser.add_argument("--site-host", default="localhost", help="Host header for main site")
    parser.add_argument("--www-host", default="localhost", help="Host header for the direct asset URL check")
    parser.add_argument(
        "--token-url",
        default="http://localhost:8080/auth/realms/dataspace/protocol/openid-connect/token",
        help="Keycloak token endpoint URL",
    )
    parser.add_argument(
        "--token-host",
        default="",
        help="Optional Host header for token request (useful when token URL uses VPS IP)",
    )
    parser.add_argument("--username", required=True, help="Keycloak username")
    parser.add_argument("--password", required=True, help="Keycloak password")
    parser.add_argument("--client-id", required=True, help="Keycloak client id")
    parser.add_argument("--client-secret", required=True, help="Keycloak client secret")
    parser.add_argument(
        "--direct-paper-path",
        default="/papers/paper-01-es-functional-overview.pdf",
        help="Direct paper URL path to verify 403",
    )
    parser.add_argument(
        "--connector-prefix",
        default="/api/connector-1",
        help="Ingress prefix for connector management API",
    )
    parser.add_argument("--insecure", action="store_true", help="Disable TLS verification")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout seconds")
    args = parser.parse_args()

    failures = []

    direct_url = f"https://{args.ip}{args.direct_paper_path}"
    try:
        request_raw(
            direct_url,
            headers={"Host": args.www_host},
            insecure=args.insecure,
            timeout=args.timeout,
        )
        failures.append(f"Direct paper URL should be blocked but returned success: {direct_url}")
        print(f"DIRECT_CHECK=FAILED status<400 url={direct_url}")
    except urllib.error.HTTPError as e:
        print(f"DIRECT_CHECK_STATUS={e.code}")
        if e.code != 403:
            failures.append(f"Direct paper URL expected 403 but got {e.code}")

    try:
        token = get_access_token(args)
        print("TOKEN_STATUS=OK")
    except Exception as e:
        print(f"TOKEN_STATUS=FAILED error={e}")
        print("RESULT=FAILED")
        return 2

    assets_url = f"https://{args.ip}{args.connector_prefix}/management/v3/assets"
    try:
        assets = request_json(
            assets_url,
            headers={"Authorization": f"Bearer {token}", "Host": args.site_host},
            insecure=args.insecure,
            timeout=args.timeout,
        )
        papers = pick_paper_asset(assets)
        asset_id = str(papers[0].get("id") or papers[0].get("@id"))
        print(f"PAPER_ASSETS={len(papers)}")
        print(f"ASSET_ID={asset_id}")
    except Exception as e:
        failures.append(f"Unable to list/select paper assets: {e}")
        print(f"ASSET_LIST_STATUS=FAILED error={e}")
        print("RESULT=FAILED")
        return 3

    download_url = (
        f"https://{args.ip}{args.connector_prefix}/management/v3/assets/"
        f"{urllib.parse.quote(asset_id)}/download"
    )
    try:
        with request_raw(
            download_url,
            headers={"Authorization": f"Bearer {token}", "Host": args.site_host},
            insecure=args.insecure,
            timeout=args.timeout,
        ) as resp:
            status = getattr(resp, "status", 200)
            content_disposition = resp.headers.get("Content-Disposition", "")
            first_bytes = len(resp.read(256))
            print(f"DOWNLOAD_STATUS={status}")
            print(f"CONTENT_DISPOSITION={content_disposition}")
            print(f"FIRST_BYTES={first_bytes}")
            if status != 200:
                failures.append(f"Download expected 200 but got {status}")
            if "attachment" not in content_disposition.lower():
                failures.append("Download missing attachment Content-Disposition")
            if first_bytes <= 0:
                failures.append("Download returned empty content")
    except urllib.error.HTTPError as e:
        failures.append(f"Download request failed with HTTP {e.code}")
        print(f"DOWNLOAD_STATUS={e.code}")
    except Exception as e:
        failures.append(f"Download request failed: {e}")
        print(f"DOWNLOAD_STATUS=FAILED error={e}")

    if failures:
        print("RESULT=FAILED")
        for f in failures:
            print(f"FAILURE={f}")
        return 1

    print("RESULT=OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
