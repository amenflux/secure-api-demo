"""Fetch the shared platform bundle from Centrify (LLM endpoint + email webhook).

Same Centrify flow as fetch_team_bundle.py, but targeting a shared bundle name
that holds the LLM gateway coordinates + a Logic App webhook URL for email.
The real HTTP shape is preserved verbatim in the triple-quoted comment block.
The demo path reads a GitHub secret or a hardcoded default so this runs
end-to-end with no secrets configured.
"""

# ---------------------------------------------------------------------------
# REAL PRODUCTION CODE (Centrify vault flow, targeting the platform bundle).
#
# """
# import json, os, requests
#
# TENANT_PREFIX = os.environ["CENTRIFY_CNAME_PREFIX"]
# APP_ID        = os.environ["CENTRIFY_APP_ID"]
# SCOPE         = os.environ["CENTRIFY_SCOPE"]
# USERNAME      = os.environ["CENTRIFY_USERNAME"]
# PASSWORD      = os.environ["CENTRIFY_PASSWORD"]
# BUNDLE_NAME   = "qa-agent-platform-creds"          # shared across all consuming teams
#
# base = f"https://{TENANT_PREFIX}.my.centrify.net"
#
# tok = requests.post(
#     f"{base}/oauth2/token/{APP_ID}",
#     headers={"X-CENTRIFY-NATIVE-CLIENT": "1",
#              "Content-Type": "application/x-www-form-urlencoded"},
#     data={"grant_type": "client_credentials", "scope": SCOPE,
#           "client_id": USERNAME, "client_secret": PASSWORD},
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
# q = requests.post(
#     f"{base}/Redrock/query",
#     headers=rest_headers,
#     json={"Script": f"SELECT ID FROM DataVault WHERE SecretName = '{BUNDLE_NAME}'"},
#     timeout=30,
# )
# q.raise_for_status()
# secret_id = q.json()["Result"]["Results"][0]["Row"]["ID"]
#
# s = requests.post(
#     f"{base}/ServerManage/RetrieveSecretContents",
#     headers=rest_headers,
#     json={"ID": secret_id},
#     timeout=30,
# )
# s.raise_for_status()
# bundle = json.loads(s.json()["Result"]["SecretText"])
#
# # bundle carries: GENAI_BASE_URL, GENAI_MODEL, GENAI_CLIENT_ID,
# #                 GENAI_CLIENT_SECRET, GENAI_TENANT_ID,
# #                 LOGIC_APP_EMAIL_WEBHOOK_URL
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
    "GENAI_BASE_URL": "https://corp-ai-gateway.example.com/openai/v1",
    "GENAI_MODEL": "corp-model-2026",
    "GENAI_CLIENT_ID": "demo-aad-client-id",
    "GENAI_CLIENT_SECRET": "demo-aad-client-secret",
    "GENAI_TENANT_ID": "demo-aad-tenant-id",
    "LOGIC_APP_EMAIL_WEBHOOK_URL": "https://corp-logic-app.example.com/hook",
}

NON_SENSITIVE = {"GENAI_BASE_URL", "GENAI_MODEL"}


def emit(name: str, value: str) -> None:
    gh_env = os.environ.get("GITHUB_ENV")
    if not gh_env:
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
    raw = os.environ.get("DEMO_PLATFORM_BUNDLE_JSON", "").strip()
    if not raw:
        return dict(DEFAULT_BUNDLE), "hardcoded default bundle"
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"::warning::DEMO_PLATFORM_BUNDLE_JSON invalid JSON ({exc}); using hardcoded default")
        return dict(DEFAULT_BUNDLE), "hardcoded default bundle (secret JSON invalid)"
    if not isinstance(parsed, dict):
        print("::warning::DEMO_PLATFORM_BUNDLE_JSON must be a JSON object; using hardcoded default")
        return dict(DEFAULT_BUNDLE), "hardcoded default bundle (secret not an object)"
    merged = dict(DEFAULT_BUNDLE)
    merged.update({str(k): str(v) for k, v in parsed.items()})
    return merged, "DEMO_PLATFORM_BUNDLE_JSON secret"


def main() -> int:
    print("=" * 72)
    print("STAGE: Fetch platform LLM bundle from Centrify vault")
    print("=" * 72)
    print()
    print("Real production path (see triple-quoted block at the top of this file):")
    print("  Same Centrify flow as fetch_team_bundle.py, but targeting the shared")
    print("  bundle name 'qa-agent-platform-creds'. Holds LLM gateway URL, AAD")
    print("  client credentials for it, model name, and the Logic App email webhook.")
    print()

    bundle, source = load_demo_bundle()
    print(f"DEMO PATH: sourcing bundle from {source}.")
    print(f"  keys present: {sorted(bundle.keys())}")
    print()

    for k, v in bundle.items():
        emit(k, str(v))

    print()
    print("[OK] Platform bundle stage complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
