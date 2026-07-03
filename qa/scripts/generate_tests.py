"""Generate the Postman collection driving Newman.

Real production path: POSTs a structured prompt (OpenAPI spec + PR context)
to a corporate LLM gateway and parses a Postman v2.1 collection out of the
response. The real HTTP shape is preserved verbatim in the triple-quoted
comment block below.

Demo path: builds a deterministic Postman v2.1 collection directly from the
fetched OpenAPI spec so the pipeline is reproducible without an LLM. The
collection exercises the five interesting shapes of the sample service:
/health, /login (happy), /login (bad creds), /me (authorized), /me (missing
bearer).
"""

# ---------------------------------------------------------------------------
# REAL PRODUCTION CODE (chat-completions call, exact HTTP shape).
#
# """
# import json, os, requests
#
# GENAI_BASE_URL     = os.environ["GENAI_BASE_URL"]         # e.g. corp gateway
# GENAI_MODEL        = os.environ["GENAI_MODEL"]            # e.g. "corp-model-2026"
# GENAI_API_VERSION  = "2024-02-15-preview"
# AAD_TOKEN          = os.environ["GENAI_AAD_ACCESS_TOKEN"] # obtained upstream
#
# openapi_spec = open("qa/artifacts/openapi.json").read()
# pr_title     = os.environ.get("PR_TITLE", "")
# pr_body      = os.environ.get("PR_BODY", "")
# pr_diff      = os.environ.get("PR_DIFF", "")
#
# system_prompt = (
#     "You are a Senior QA automation engineer generating a Postman "
#     "Collection v2.1. Return ONLY valid JSON: an info object with the "
#     "v2.1 schema URL, plus an item array. For each in-scope endpoint "
#     "produce one happy-path request and one negative request. Use "
#     "{{base_url}} in every URL. Attach {{auth_header}} for protected "
#     "endpoints. Include a pm.test asserting the expected status code."
# )
# user_prompt = (
#     f"PR title: {pr_title}\n"
#     f"PR body:\n{pr_body}\n"
#     f"PR diff:\n{pr_diff}\n\n"
#     f"OpenAPI spec:\n{openapi_spec}\n\n"
#     "Return ONLY the Postman Collection JSON."
# )
#
# url = (
#     f"{GENAI_BASE_URL}/openai/deployments/{GENAI_MODEL}"
#     f"/chat/completions?api-version={GENAI_API_VERSION}"
# )
# resp = requests.post(
#     url,
#     headers={
#         "Authorization": f"Bearer {AAD_TOKEN}",
#         "Content-Type":  "application/json",
#     },
#     json={
#         "model":           GENAI_MODEL,
#         "messages": [
#             {"role": "system", "content": system_prompt},
#             {"role": "user",   "content": user_prompt},
#         ],
#         "temperature":     0.2,
#         "max_tokens":      2500,
#         "response_format": {"type": "json_object"},
#     },
#     timeout=600,
# )
# resp.raise_for_status()
# payload    = resp.json()
# raw        = payload["choices"][0]["message"]["content"]
# collection = json.loads(raw)               # LLM returned JSON per response_format
# usage      = payload.get("usage", {})      # prompt_tokens/completion_tokens/total_tokens
# """
# ---------------------------------------------------------------------------

import hashlib
import json
import os
import sys
from pathlib import Path


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _make_request(name: str, method: str, path: str, body: dict | None = None,
                  expected_status: int = 200, auth: bool = False) -> dict:
    header_block = [{"key": "Content-Type", "value": "application/json"}]
    if auth:
        header_block.append({"key": "Authorization", "value": "{{auth_header_value}}"})

    item = {
        "name": name,
        "request": {
            "method": method,
            "header": header_block,
            "url": {
                "raw": "{{base_url}}" + path,
                "host": ["{{base_url}}"],
                "path": [segment for segment in path.strip("/").split("/") if segment],
            },
        },
        "event": [{
            "listen": "test",
            "script": {
                "type": "text/javascript",
                "exec": [
                    f"pm.test('{name} returns {expected_status}', function () {{",
                    f"  pm.response.to.have.status({expected_status});",
                    "});",
                ],
            },
        }],
    }
    if body is not None:
        item["request"]["body"] = {"mode": "raw", "raw": json.dumps(body)}
    return item


def main() -> int:
    print("=" * 72)
    print("STAGE: Generate Postman collection")
    print("=" * 72)
    print()
    print("Real production path (see triple-quoted block at the top of this file):")
    print("  1. Load qa/artifacts/openapi.json (fetched from the deployed service).")
    print("  2. Assemble a system+user chat prompt with the spec + PR context.")
    print(f"  3. POST to {os.environ.get('GENAI_BASE_URL', '<GENAI_BASE_URL>')}"
          f"/openai/deployments/{os.environ.get('GENAI_MODEL', '<GENAI_MODEL>')}"
          "/chat/completions?api-version=2024-02-15-preview")
    print("     Authorization: Bearer <AAD access token>, response_format=json_object.")
    print("  4. json.loads(resp.json()['choices'][0]['message']['content']) -> collection.")
    print()
    print("DEMO PATH: building a deterministic collection directly from the spec.")
    print()

    spec_path = Path("qa/artifacts/openapi.json")
    if not spec_path.exists():
        print(f"::error::{spec_path} missing — the fetch_openapi step must run first")
        return 1

    spec_bytes = spec_path.read_bytes()
    spec = json.loads(spec_bytes)

    items = [
        _make_request("Health check", "GET", "/health", expected_status=200),
        _make_request(
            "Login (happy path)",
            "POST",
            "/login",
            body={
                "client_id": "{{test_client_id}}",
                "client_secret": "{{test_client_secret}}",
            },
            expected_status=200,
        ),
        _make_request(
            "Login (rejects bad creds)",
            "POST",
            "/login",
            body={"client_id": "wrong", "client_secret": "wrong"},
            expected_status=401,
        ),
        _make_request("Me (authenticated)", "GET", "/me",
                      expected_status=200, auth=True),
        _make_request("Me (rejects missing bearer)", "GET", "/me",
                      expected_status=401),
    ]

    collection = {
        "info": {
            "name": "Sample Secure API — Generated Regression",
            "description": (
                "Deterministic demo collection. In production this is LLM-generated "
                "per run from the fetched OpenAPI spec plus the PR context."
            ),
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "item": items,
    }

    out = Path("qa/collections/generated.postman_collection.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(collection, indent=2)
    out.write_text(payload)

    # Drift metadata — the real deployment publishes these per run so successive
    # runs can be diffed on (spec, prompt template, output collection).
    input_hash = _hash(spec_bytes)
    prompt_hash = _hash(b"demo-deterministic-builder-v1")
    collection_hash = _hash(payload.encode())

    print(f"  written: {out} ({len(payload)} bytes, {len(items)} requests)")
    print(f"  INPUT_HASH      = {input_hash[:16]}...")
    print(f"  PROMPT_HASH     = {prompt_hash[:16]}...")
    print(f"  COLLECTION_HASH = {collection_hash[:16]}...")

    gh_env = os.environ.get("GITHUB_ENV")
    if gh_env:
        model_used = os.environ.get("GENAI_MODEL", "demo-deterministic-builder")
        with open(gh_env, "a") as fh:
            fh.write(f"INPUT_HASH={input_hash}\n")
            fh.write(f"PROMPT_HASH={prompt_hash}\n")
            fh.write(f"COLLECTION_HASH={collection_hash}\n")
            fh.write(f"GENAI_MODEL_USED={model_used}\n")
            fh.write("LLM_TOTAL_TOKENS=0\n")

    print()
    print("[OK] Collection generation stage complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
