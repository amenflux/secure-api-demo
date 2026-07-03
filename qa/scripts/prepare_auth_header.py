"""Prepare the AUTH_HEADER env var that downstream Newman steps consume.

Switches on AUTH_TYPE. Two of the strategies (service-credentials, api-key,
custom) run their REAL production path in the demo. The oauth-client-credentials
strategy preserves the real AAD token-exchange shape in a triple-quoted block
and emits a placeholder Bearer, because the AAD tenant + client are not
reproducible outside the corporate environment.
"""

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request


def fail(msg: str) -> None:
    print(f"::error::{msg}", file=sys.stderr)
    sys.exit(1)


def emit(name: str, value: str, mask: bool = True) -> None:
    gh_env = os.environ.get("GITHUB_ENV")
    if not gh_env:
        return
    if mask and value:
        print(f"::add-mask::{value}")
    with open(gh_env, "a") as fh:
        fh.write(f"{name}={value}\n")


# ---------------------------------------------------------------------------
# STRATEGY: none — public endpoints, no auth header.
# ---------------------------------------------------------------------------
def strategy_none() -> str:
    print("  strategy: none — emitting empty AUTH_HEADER")
    return ""


# ---------------------------------------------------------------------------
# STRATEGY: api-key — REAL. Static header, no external call.
# ---------------------------------------------------------------------------
def strategy_api_key() -> str:
    api_key = os.environ.get("TEST_API_KEY", "").strip()
    if not api_key:
        fail("AUTH_TYPE='api-key' requires TEST_API_KEY (from the team bundle).")
    header_name = os.environ.get("API_KEY_HEADER", "").strip() or "X-API-Key"
    print(f"  strategy: api-key — {header_name}: <masked>")
    return f"{header_name}: {api_key}"


# ---------------------------------------------------------------------------
# STRATEGY: service-credentials — REAL. POSTs to the running FastAPI /login
# with client_id/client_secret and reads access_token from the response body.
# ---------------------------------------------------------------------------
def strategy_service_credentials() -> str:
    base = os.environ["DEV_API_URL"].rstrip("/")
    path = os.environ.get("LOGIN_PATH", "").strip() or "/login"
    cid = os.environ["TEST_SP_CLIENT_ID"]
    secret = os.environ["TEST_SP_CLIENT_SECRET"]
    url = f"{base}{path}"
    print(f"  strategy: service-credentials — POST {url}")
    body = json.dumps({"client_id": cid, "client_secret": secret}).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        fail(f"login endpoint returned HTTP {exc.code}: {exc.read().decode(errors='replace')[:200]}")
    token = payload.get("access_token") or (payload.get("data") or {}).get("access_token")
    if not token:
        fail(f"login returned 200 but no access_token in body: {payload}")
    print(f"  received bearer token ({len(token)} chars)")
    return f"Authorization: Bearer {token}"


# ---------------------------------------------------------------------------
# STRATEGY: oauth-client-credentials — real code is preserved verbatim below.
#
# The real path exchanges client_id/client_secret for an Azure AD access
# token via the tenant's OAuth2 v2.0 token endpoint. That call cannot run
# in the public demo (no real AAD tenant), so the demo path emits a
# placeholder Bearer that lets the pipeline complete.
#
# """
# import os, requests
#
# tenant     = os.environ["AAD_TENANT_ID"]           # from team bundle
# client_id  = os.environ["TEST_SP_CLIENT_ID"]       # from team bundle
# client_sec = os.environ["TEST_SP_CLIENT_SECRET"]   # from team bundle
# scope      = os.environ["AAD_SCOPE"]               # from team bundle
#
# token_url = os.environ.get("OAUTH_TOKEN_URL") or \
#             f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
#
# resp = requests.post(
#     token_url,
#     data={
#         "grant_type":    "client_credentials",
#         "client_id":     client_id,
#         "client_secret": client_sec,
#         "scope":         scope,
#     },
#     timeout=30,
# )
# resp.raise_for_status()
# access_token = resp.json()["access_token"]
# return f"Authorization: Bearer {access_token}"
# """
# ---------------------------------------------------------------------------
def strategy_oauth_client_credentials() -> str:
    print("  strategy: oauth-client-credentials")
    print("  DEMO PATH: skipping real AAD token exchange; emitting placeholder Bearer.")
    return "Authorization: Bearer demo-aad-access-token-placeholder"


# ---------------------------------------------------------------------------
# STRATEGY: custom — REAL. Shells out to a team-provided script and uses
# its stdout as the auth header.
# ---------------------------------------------------------------------------
def strategy_custom() -> str:
    path = os.environ.get("CUSTOM_AUTH_SCRIPT_PATH", "").strip()
    if not path:
        fail("AUTH_TYPE='custom' requires CUSTOM_AUTH_SCRIPT_PATH (path to a script that prints the auth header on stdout).")
    if not os.path.exists(path):
        fail(f"CUSTOM_AUTH_SCRIPT_PATH points to a missing file: {path}")
    print(f"  strategy: custom — invoking {path}")
    result = subprocess.run(["bash", path], capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        fail(f"custom auth script exited {result.returncode}: {result.stderr[:200]}")
    header = result.stdout.strip()
    if not header:
        fail("custom auth script produced empty stdout (expected an auth header).")
    return header


STRATEGIES = {
    "none": strategy_none,
    "api-key": strategy_api_key,
    "oauth-client-credentials": strategy_oauth_client_credentials,
    "service-credentials": strategy_service_credentials,
    "custom": strategy_custom,
}


def main() -> int:
    auth_type = os.environ.get("AUTH_TYPE", "").strip().lower()
    print("=" * 72)
    print("STAGE: Prepare AUTH_HEADER")
    print("=" * 72)
    print(f"  AUTH_TYPE = {auth_type!r}")
    print()
    if auth_type not in STRATEGIES:
        fail(f"Unknown AUTH_TYPE={auth_type!r}. Valid: {sorted(STRATEGIES)}")
    header = STRATEGIES[auth_type]()
    emit("AUTH_HEADER", header, mask=bool(header))
    print()
    print("[OK] AUTH_HEADER exported for downstream Newman runs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
