"""Decrypt Fernet-encrypted vault credentials at workflow runtime.

The real production shape is preserved verbatim in the triple-quoted comment
block below. The demo path underneath reads a GitHub secret (or a hardcoded
placeholder) so this file runs end-to-end with zero secrets configured.

Contract (both paths):
  Writes CENTRIFY_USERNAME and CENTRIFY_PASSWORD to $GITHUB_ENV, masked.
"""

# ---------------------------------------------------------------------------
# REAL PRODUCTION CODE (defense-in-depth secret unwrap).
#
# Two-layer secret model: an org-level Fernet key is scoped to allowlisted
# repositories only; each repository ships two Fernet blobs at repo scope.
# An attacker who leaks either half alone cannot recover the plaintext.
#
# """
# import os
# import sys
# from cryptography.fernet import Fernet, InvalidToken
#
# KEY          = os.environ["QA_AGENT_FERNET_DECRYPTION_KEY"].encode()
# ENC_USERNAME = os.environ["ENC_CENTRIFY_USERNAME"].encode()
# ENC_PASSWORD = os.environ["ENC_CENTRIFY_PASSWORD"].encode()
#
# cipher = Fernet(KEY)
# try:
#     username = cipher.decrypt(ENC_USERNAME).decode()
#     password = cipher.decrypt(ENC_PASSWORD).decode()
# except InvalidToken:
#     print("::error::Fernet decryption failed (wrong key or corrupted blob).",
#           file=sys.stderr)
#     sys.exit(1)
#
# gh_env = os.environ["GITHUB_ENV"]
# for name, value in (("CENTRIFY_USERNAME", username),
#                     ("CENTRIFY_PASSWORD", password)):
#     print(f"::add-mask::{value}")
#     with open(gh_env, "a") as fh:
#         fh.write(f"{name}={value}\n")
# """
# ---------------------------------------------------------------------------

import json
import os
import sys


PLACEHOLDER_CREDS = {
    "username": "demo-service-account",
    "password": "demo-not-a-real-password",
}


def emit(name: str, value: str) -> None:
    gh_env = os.environ.get("GITHUB_ENV")
    if not gh_env:
        print(f"WARN: GITHUB_ENV not set; skipping export of {name}", file=sys.stderr)
        return
    print(f"::add-mask::{value}")
    with open(gh_env, "a") as fh:
        fh.write(f"{name}={value}\n")
    print(f"  exported {name} (masked in logs)")


def load_demo_creds() -> dict:
    raw = os.environ.get("DEMO_CENTRIFY_CREDS_JSON", "").strip()
    if not raw:
        return PLACEHOLDER_CREDS
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"::warning::DEMO_CENTRIFY_CREDS_JSON is not valid JSON ({exc}); using placeholders")
        return PLACEHOLDER_CREDS
    if not isinstance(parsed, dict) or "username" not in parsed or "password" not in parsed:
        print("::warning::DEMO_CENTRIFY_CREDS_JSON must be an object with .username and .password; using placeholders")
        return PLACEHOLDER_CREDS
    return parsed


def main() -> int:
    print("=" * 72)
    print("STAGE: Decrypt vault credentials")
    print("=" * 72)
    print()
    print("Real production path (see triple-quoted block at the top of this file):")
    print("  1. Read QA_AGENT_FERNET_DECRYPTION_KEY from an org-level GitHub secret")
    print("     scoped via 'Selected repositories' to the allowlisted repos only.")
    print("  2. Read ENC_CENTRIFY_USERNAME and ENC_CENTRIFY_PASSWORD (Fernet blobs)")
    print("     from repo-level secrets on the calling repository.")
    print("  3. Use the Fernet key to decrypt both blobs.")
    print("  4. Export CENTRIFY_USERNAME + CENTRIFY_PASSWORD to $GITHUB_ENV, masked.")
    print()
    print("Defense-in-depth: an attacker with one leaked half cannot recover the")
    print("plaintext — they need both the org-scoped key AND the repo-scoped blob.")
    print()

    creds = load_demo_creds()
    source = "DEMO_CENTRIFY_CREDS_JSON secret" if os.environ.get("DEMO_CENTRIFY_CREDS_JSON", "").strip() else "hardcoded placeholders"
    print(f"DEMO PATH: sourcing credentials from {source}.")

    emit("CENTRIFY_USERNAME", str(creds["username"]))
    emit("CENTRIFY_PASSWORD", str(creds["password"]))

    print()
    print("[OK] Decryption stage complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
