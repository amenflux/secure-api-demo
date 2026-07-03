"""Push the generated collection to the team's Postman workspace.

Real production path (upsert-by-name) is preserved verbatim in the triple-
quoted comment block. The demo path logs what would happen and exits 0 — a
real Postman workspace and API key are not shipped with a public demo.
"""

# ---------------------------------------------------------------------------
# REAL PRODUCTION CODE (Postman API upsert-by-name).
#
# """
# import json, os, sys, requests
#
# API_KEY      = os.environ["POSTMAN_API_KEY"]          # from team bundle
# WORKSPACE_ID = os.environ["POSTMAN_WORKSPACE_ID"]     # from team bundle
# COLLECTION   = json.loads(open("qa/collections/generated.postman_collection.json").read())
# NAME         = COLLECTION["info"]["name"]
# BASE         = "https://api.getpostman.com"
#
# # 1. List collections in the workspace, look for one with the same name.
# lst = requests.get(
#     f"{BASE}/collections",
#     params={"workspace": WORKSPACE_ID},
#     headers={"X-API-Key": API_KEY},
#     timeout=30,
# )
# lst.raise_for_status()
# existing = next(
#     (c for c in lst.json().get("collections", []) if c.get("name") == NAME),
#     None,
# )
#
# body = {"collection": COLLECTION}
#
# # 2. PUT to update in place, POST to create.
# if existing:
#     resp = requests.put(
#         f"{BASE}/collections/{existing['uid']}",
#         headers={"X-API-Key": API_KEY, "Content-Type": "application/json"},
#         json=body,
#         timeout=60,
#     )
# else:
#     resp = requests.post(
#         f"{BASE}/collections",
#         params={"workspace": WORKSPACE_ID},
#         headers={"X-API-Key": API_KEY, "Content-Type": "application/json"},
#         json=body,
#         timeout=60,
#     )
# resp.raise_for_status()
# uid     = resp.json()["collection"]["uid"]
# web_url = f"https://go.postman.co/workspaces/{WORKSPACE_ID}/collections/{uid}"
# print(f"Postman upsert OK: {uid}\n  Open: {web_url}")
# """
# ---------------------------------------------------------------------------

import os
import sys
from pathlib import Path


def main() -> int:
    print("=" * 72)
    print("STAGE: Push generated collection to Postman workspace")
    print("=" * 72)
    print()
    print("Real production path (see triple-quoted block at the top of this file):")
    print("  1. GET  https://api.getpostman.com/collections?workspace={POSTMAN_WORKSPACE_ID}")
    print("         header: X-API-Key: {POSTMAN_API_KEY}")
    print("  2. PUT  https://api.getpostman.com/collections/{uid}   (if it exists)")
    print("     POST https://api.getpostman.com/collections?workspace=... (otherwise)")
    print("     body: {\"collection\": <the generated collection JSON>}")
    print()

    api_key = os.environ.get("POSTMAN_API_KEY", "").strip()
    workspace = os.environ.get("POSTMAN_WORKSPACE_ID", "").strip()
    coll = Path("qa/collections/generated.postman_collection.json")

    if not api_key or api_key.startswith("demo-"):
        print("DEMO PATH: POSTMAN_API_KEY is a placeholder — skipping the real upsert.")
        print(f"  would upload: {coll} ({coll.stat().st_size if coll.exists() else 0} bytes)")
        print(f"  target workspace: {workspace or '(unset)'}")
        print()
        print("[OK] Postman sync stage complete (demo skip).")
        return 0

    if not coll.exists():
        print(f"::warning::{coll} missing — nothing to upload")
        return 0

    print("Real API key detected but the demo intentionally does not perform the")
    print("upsert (the public demo repo has no team workspace to write to).")
    print(f"  would upload: {coll} ({coll.stat().st_size} bytes) to workspace {workspace}")
    print()
    print("[OK] Postman sync stage complete (demo skip).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
