# secure-api-demo

A public replica of a CI/CD pattern I built for Procter & Gamble's Automation
team: on every push to a product repo, spin up the service, generate an API
regression suite from its live OpenAPI spec, run it with Newman against the
running container, and publish a pass/fail summary + HTML report as workflow
artifacts.

The corporate original wires this same shape into an LLM gateway, a vault, an
email dispatcher, and a Postman workspace. **Product names, secret names,
LLM model names, and internal tool identifiers from that original are
confidential and are not reproduced here.** In this repo:

- Every mocked external call has the **real production HTTP code preserved
  verbatim** as a triple-quoted comment block at the top of the function.
  Anyone reading the source can see exactly what the real integration looks
  like: endpoints, headers, request/response shapes, parsing.
- Underneath each of those blocks is a **working demo path** that either reads
  a GitHub secret (see below) or falls back to a hardcoded placeholder. The
  pipeline runs end-to-end with zero secrets configured.
- Everything that **can** be real, **is** real: Docker Compose builds and
  starts the FastAPI app, Newman actually runs against `http://localhost:8000`,
  Newman's JSON output is really parsed into the HTML summary.

## Architecture

```
GitHub Actions
   │
   ▼
docker compose up --build -d          ← FastAPI container, listens on :8000
   │
   ▼
decrypt_secrets.py                    (Fernet decrypt / demo placeholder)
fetch_team_bundle.py                  (Centrify vault / demo placeholder)
prepare_auth_header.py                (5 strategies incl. real service-creds login)
fetch_openapi.py                      (REAL GET /openapi.json)
fetch_platform_bundle.py              (Centrify vault / demo placeholder)
generate_tests.py                     (LLM chat-completions / deterministic builder)
   │
   ▼
newman run generated.postman_collection.json   ← REAL, against localhost:8000
   │
   ▼
summarize_newman.py                   (REAL, parses Newman JSON → HTML)
upload_to_postman.py                  (Postman API upsert / demo skip)
send_email.py                         (Logic App webhook / demo skip)
   │
   ▼
upload-artifact                       (reports/, collections/, artifacts/)
```

## Optional GitHub secrets

The demo runs to completion with **none** of these configured. Set them if you
want to substitute your own values for the placeholders.

| Secret | Purpose |
|---|---|
| `DEMO_CENTRIFY_CREDS_JSON` | JSON object `{"username": "...", "password": "..."}` that replaces the placeholder plaintext in `decrypt_secrets.py`. |
| `DEMO_TEAM_BUNDLE_JSON` | JSON object that overlays the default team bundle in `fetch_team_bundle.py` (any subset of `DEV_API_URL`, `LOGIN_PATH`, `TEST_SP_CLIENT_ID`, `TEST_SP_CLIENT_SECRET`, `POSTMAN_API_KEY`, `POSTMAN_WORKSPACE_ID`, etc.). |
| `DEMO_PLATFORM_BUNDLE_JSON` | JSON object that overlays the default platform bundle in `fetch_platform_bundle.py` (`GENAI_BASE_URL`, `GENAI_MODEL`, `LOGIC_APP_EMAIL_WEBHOOK_URL`, etc.). |

None of these unlock a real corporate integration — the real production paths
in the scripts stay commented out. The only effect of setting them is to
change the values the demo path exports to `$GITHUB_ENV`.

## How to inspect a run

Every past run of this pipeline is public. Anyone can read the full log and
download the artifacts without a GitHub account.

1. Open the **Actions** tab.
2. Select the workflow **"QA Agent — Caller"** in the left sidebar.
3. Click the most recent green run at the top of the list.
4. Read any step to see its full log — including the 15-second DEMO banner,
   the real Docker Compose build + startup, the real Newman execution against
   `http://localhost:8000`, and the summary output.
5. Scroll to the **Artifacts** panel at the bottom to download the produced
   files: `reports/report.json`, `reports/report.html`,
   `reports/report_summary.html`,
   `qa/collections/generated.postman_collection.json`,
   `qa/artifacts/openapi.json`.

Triggering a fresh run manually requires write access to this repository,
which by GitHub's security policy is limited to me. If you would like to see
a fresh execution, open an issue or reach out and I will kick one off.

## What you'll see in the workflow log

- The **DEMO REPOSITORY** banner in the very first step, held for 15 seconds
  so it's impossible to miss.
- Every stage prints a `STAGE:` banner explaining what it's doing.
- For each stubbed external call, the log names the real production endpoint
  the call would target and states that the demo path is running instead.
  The full real HTTP shape lives in the Python source, above the demo path.
- The Docker Compose build + service startup are live.
- Newman's `cli` reporter prints the run inline. The `html` and `json`
  reporters land in `reports/`.
- Sensitive values written to `$GITHUB_ENV` are masked via `::add-mask::`
  before they land there.

## Repository layout

```
secure-api-demo/
├── app/
│   ├── main.py                     FastAPI /login + /me + /health
│   └── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── qa/
│   ├── scripts/
│   │   ├── decrypt_secrets.py          Fernet decrypt (real shape / demo path)
│   │   ├── fetch_team_bundle.py        Centrify vault fetch (real shape / demo)
│   │   ├── fetch_platform_bundle.py    Centrify platform bundle (real / demo)
│   │   ├── prepare_auth_header.py      5 strategies, service-creds is REAL
│   │   ├── fetch_openapi.py            REAL GET /openapi.json
│   │   ├── generate_tests.py           LLM chat-completions shape / deterministic
│   │   ├── summarize_newman.py         REAL Newman JSON → HTML
│   │   ├── upload_to_postman.py        Postman API upsert (real shape / demo)
│   │   └── send_email.py               Logic App webhook (real shape / demo)
│   ├── collections/                Generated collections land here at run time
│   ├── artifacts/                  Fetched OpenAPI spec lands here
│   ├── requirements.txt            requests + cryptography
│   └── package.json                Newman + reporter
└── .github/workflows/
    ├── qa-agent-caller.yml         workflow_dispatch entry point
    └── qa-agent-reusable.yml       workflow_call pipeline
```

## Design notes

- The pattern splits caller from reusable so the same reusable can be pinned
  by semver from many product repos. In production the reusable lives in a
  separate central repo; here both live in the same repo so the wiring is
  fully inspectable.
- Sensitive values are masked before they hit `$GITHUB_ENV`. Non-sensitive
  values (URLs, header names, workspace identifiers) are logged in clear so
  you can see what the run is targeting.
- The generated Postman collection is deterministic in demo mode, so
  successive runs produce byte-identical output — the `COLLECTION_HASH`
  emitted to `$GITHUB_ENV` is stable across runs.
- Artifacts are uploaded on `always()` so a failed Newman run still leaves
  the report behind.
