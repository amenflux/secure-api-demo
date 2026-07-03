"""Fetch the live OpenAPI spec from the deployed service.

Fully REAL: performs an HTTP GET against ${DEV_API_URL}${OPENAPI_PATH}, saves
the raw bytes to qa/artifacts/openapi.json, and prints a short summary. The
downstream generate_tests.py step reads that file.
"""

import json
import os
import sys
import urllib.error
import urllib.request


def main() -> int:
    base = os.environ["DEV_API_URL"].rstrip("/")
    path = os.environ.get("OPENAPI_PATH", "/openapi.json")
    url = f"{base}{path}"

    print("=" * 72)
    print("STAGE: Fetch live OpenAPI spec from deployed service")
    print("=" * 72)
    print(f"  GET {url}")

    headers = {}
    auth_header = os.environ.get("AUTH_HEADER", "")
    if auth_header:
        name, _, value = auth_header.partition(":")
        if name.strip():
            headers[name.strip()] = value.strip()

    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read()
    except urllib.error.HTTPError as exc:
        print(f"::error::spec fetch returned HTTP {exc.code}: {exc.read().decode(errors='replace')[:200]}")
        return 1
    except Exception as exc:  # noqa: BLE001 - want any transport error visible in log
        print(f"::error::spec fetch failed: {exc}")
        return 1

    out = "qa/artifacts/openapi.json"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "wb") as fh:
        fh.write(content)

    try:
        spec = json.loads(content)
    except json.JSONDecodeError as exc:
        print(f"::error::response was not valid JSON: {exc}")
        return 1

    title = spec.get("info", {}).get("title", "(untitled)")
    version = spec.get("info", {}).get("version", "?")
    n_paths = len(spec.get("paths", {}))
    print(f"  spec: {title} v{version}")
    print(f"  {n_paths} path(s) declared")
    print(f"  written to {out} ({len(content)} bytes)")
    print()
    print("[OK] OpenAPI spec fetched.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
