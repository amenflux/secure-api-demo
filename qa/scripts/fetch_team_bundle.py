"""Fetch the team's secret bundle from Centrify and export its keys to $GITHUB_ENV.

The real production shape (OAuth2 client-credentials -> Redrock query -> secret
retrieve) is preserved verbatim in the triple-quoted comment block below. The
demo path underneath reads a GitHub secret (or a hardcoded default bundle) so
this file runs end-to-end with zero secrets configured.
"""

# ---------------------------------------------------------------------------
# REAL PRODUCTION CODE (Centrify vault flow, all three legs).
#
# """
# import json, os, sys, requests
#
# TENANT_PREFIX = os.environ["CENTRIFY_CNAME_PREFIX"]     # e.g. "corp-tenant-prefix"
# APP_ID        = os.environ["CENTRIFY_APP_ID"]           # OAuth2 application id
# SCOPE         = os.environ["CENTRIFY_SCOPE"]            # OAuth2 scope
# USERNAME      = os.environ["CENTRIFY_USERNAME"]         # decrypted upstream
# PASSWORD      = os.environ["CENTRIFY_PASSWORD"]         # decrypted upstream
# BUNDLE_NAME   = os.environ["CENTRIFY_BUNDLE_NAME"]      # e.g. "secureapi-team-bundle"
#
# base = f"https://{TENANT_PREFIX}.my.centrify.net"
#
# # 1. OAuth2 client-credentials token exchange.
# tok = requests.post(
#     f"{base}/oauth2/token/{APP_ID}",
#     headers={
#         "X-CENTRIFY-NATIVE-CLIENT": "1",
#         "Content-Type": "application/x-www-form-urlencoded",
#     },
#     data={
#         "grant_type": "client_credentials",
#         "scope": SCOPE,
#         "client_id": USERNAME,
#         "client_secret": PASSWORD,
#     },
#     timeout=30,
# )
# tok.raise_for_status()
# bearer = tok.json()["access_token"]
#
# rest_headers = {
#     "X-CENTRIFY-NATIVE-CLIENT": "1",
#     "Content-Type": "application/json",
#     "Authorization": f"Bearer {bearer}",
# }
#
# # 2. Redrock query to resolve the secret's ID from its name.
# q = requests.post(
#     f"{base}/Redrock/query",
#     headers=rest_headers,
#     json={"Script": f"SELECT ID FROM DataVault WHERE SecretName = '{BUNDLE_NAME}'"},
#     timeout=30,
# )
# q.raise_for_status()
# results = q.json()["Result"]["Results"]
# if not results:
#     print(f"::error::Secret '{BUNDLE_NAME}' not found", file=sys.stderr); sys.exit(1)
# secret_id = results[0]["Row"]["ID"]
#
# # 3. Retrieve the secret contents — SecretText is a JSON blob shaped like the
# #    team's bundle contract (DEV_API_URL, TEST_SP_CLIENT_ID, etc).
# s = requests.post(
#     f"{base}/ServerManage/RetrieveSecretContents",
#     headers=rest_headers,
#     json={"ID": secret_id},
#     timeout=30,
# )
# s.raise_for_status()
# bundle = json.loads(s.json()["Result"]["SecretText"])
#
# # Export every known key to $GITHUB_ENV, sensitive ones masked first.
# gh_env = os.environ["GITHUB_ENV"]
# for k, v in bundle.items():
#     if k not in NON_SENSITIVE:
#         print(f"::add-mask::{v}")
#     with open(gh_env, "a") as fh:
#         fh.write(f"{k}={v}\n")
# """
# ---------------------------------------------------------------------------

import json
import os
import sys


DEFAULT_BUNDLE = {
    "DEV_API_URL": "http://localhost:8000",
    "OPENAPI_PATH": "/openapi.json",
    "LOGIN_PATH": "/login",
    "TEST_SP_CLIENT_ID": "demo-client",
    "TEST_SP_CLIENT_SECRET": "demo-secret",
    "POSTMAN_API_KEY": "demo-postman-api-key-placeholder",
    "POSTMAN_WORKSPACE_ID": "demo-workspace-uuid-placeholder",
}

AUTH_REQUIRED = {
    "none": [],
    "api-key": ["TEST_API_KEY"],
    "oauth-client-credentials": ["AAD_SCOPE", "TEST_SP_CLIENT_ID", "TEST_SP_CLIENT_SECRET"],
    "service-credentials": ["TEST_SP_CLIENT_ID", "TEST_SP_CLIENT_SECRET"],
    "custom": [],
}

NON_SENSITIVE = {
    "DEV_API_URL", "OPENAPI_PATH", "LOGIN_PATH",
    "API_KEY_HEADER", "AAD_SCOPE", "AAD_TENANT_ID",
    "TEST_SP_CLIENT_ID", "POSTMAN_WORKSPACE_ID",
}


def emit(name: str, value: str) -> None:
    gh_env = os.environ.get("GITHUB_ENV")
    if not gh_env:
        print(f"WARN: GITHUB_ENV not set; skipping export of {name}", file=sys.stderr)
        return
    if name not in NON_SENSITIVE:
        print(f"::add-mask::{value}")
    with open(gh_env, "a") as fh:
        fh.write(f"{name}={value}\n")
    if name in NON_SENSITIVE:
        print(f"  exported {name} = {value}")
    else:
        print(f"  exported {name} (masked)")


def load_demo_bundle() -> tuple[dict, str]:
    raw = os.environ.get("DEMO_TEAM_BUNDLE_JSON", "").strip()
    if not raw:
        return dict(DEFAULT_BUNDLE), "hardcoded default bundle"
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"::warning::DEMO_TEAM_BUNDLE_JSON is not valid JSON ({exc}); using hardcoded default")
        return dict(DEFAULT_BUNDLE), "hardcoded default bundle (secret JSON invalid)"
    if not isinstance(parsed, dict):
        print("::warning::DEMO_TEAM_BUNDLE_JSON must be a JSON object; using hardcoded default")
        return dict(DEFAULT_BUNDLE), "hardcoded default bundle (secret not an object)"
    # Merge on top of defaults so partial overrides work.
    merged = dict(DEFAULT_BUNDLE)
    merged.update({str(k): str(v) for k, v in parsed.items()})
    return merged, "DEMO_TEAM_BUNDLE_JSON secret"


def main() -> int:
    bundle_name = os.environ.get("CENTRIFY_BUNDLE_NAME", "").strip()
    auth_type = os.environ.get("AUTH_TYPE", "").strip().lower()

    print("=" * 72)
    print("STAGE: Fetch team bundle from Centrify vault")
    print("=" * 72)
    print()
    print(f"  bundle_name: {bundle_name!r}")
    print(f"  auth_type:   {auth_type!r}")
    print()
    print("Real production path (see triple-quoted block at the top of this file):")
    print("  1. POST https://{TENANT}.my.centrify.net/oauth2/token/{APP_ID}")
    print("     grant_type=client_credentials, X-CENTRIFY-NATIVE-CLIENT header,")
    print("     client_id/client_secret from decrypted CENTRIFY_USERNAME/PASSWORD.")
    print("  2. POST /Redrock/query with Bearer token to resolve secret ID by name.")
    print("  3. POST /ServerManage/RetrieveSecretContents to fetch the SecretText.")
    print("  4. Parse SecretText as JSON, export every key to $GITHUB_ENV (mask sensitive).")
    print()

    bundle, source = load_demo_bundle()
    print(f"DEMO PATH: sourcing bundle from {source}.")
    print(f"  keys present: {sorted(bundle.keys())}")
    print()

    missing = [k for k in AUTH_REQUIRED.get(auth_type, []) if k not in bundle or not bundle[k]]
    if missing:
        print(f"::error::Bundle missing required keys for AUTH_TYPE={auth_type!r}: {missing}")
        return 1

    for key, value in bundle.items():
        emit(key, str(value))

    print()
    print("[OK] Team bundle stage complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
