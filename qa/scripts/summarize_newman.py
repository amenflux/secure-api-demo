"""Parse Newman's JSON output into an HTML summary and a job summary block.

Fully REAL: reads reports/report.json (produced by the earlier Newman step),
writes reports/report_summary.html with a pass/fail table, and appends a
one-glance summary to $GITHUB_STEP_SUMMARY.
"""

import json
import os
import sys
from pathlib import Path


HTML_TEMPLATE = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>QA Agent Run Summary</title>
<style>
:root {{
  --fg: #1f2328; --muted: #57606a;
  --pass: #1a7f37; --fail: #cf222e;
  --border: #d0d7de; --panel: #f6f8fa;
}}
* {{ box-sizing: border-box; }}
body {{ font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
       max-width: 960px; margin: 32px auto; padding: 0 24px;
       color: var(--fg); line-height: 1.55; }}
h1 {{ margin-bottom: 4px; }}
h2 {{ border-bottom: 1px solid var(--border); padding-bottom: 6px;
     margin-top: 32px; }}
.meta {{ color: var(--muted); font-size: 0.95em; }}
.pill {{ display: inline-block; padding: 2px 10px; border-radius: 12px;
        font-weight: 600; margin-right: 8px; }}
.pill.pass {{ background: #dafbe1; color: var(--pass); }}
.pill.fail {{ background: #ffebe9; color: var(--fail); }}
.pill.total {{ background: var(--panel); color: var(--fg); }}
table {{ border-collapse: collapse; width: 100%; margin: 12px 0; }}
th, td {{ padding: 8px 12px; text-align: left;
         border-bottom: 1px solid var(--border); }}
th {{ background: var(--panel); font-weight: 600; }}
td.pass {{ color: var(--pass); font-weight: 600; }}
td.fail {{ color: var(--fail); font-weight: 600; }}
code {{ background: var(--panel); padding: 1px 6px; border-radius: 4px;
       font-size: 0.9em; }}
</style></head><body>
<h1>QA Agent — Run Summary</h1>
<p class="meta"><strong>Environment:</strong> <code>{env}</code>
   &nbsp;·&nbsp; <strong>Base URL:</strong> <code>{base}</code></p>

<h2>Result</h2>
<p>
  <span class="pill total">Total {total}</span>
  <span class="pill pass">Passed {passed}</span>
  <span class="pill fail">Failed {failed}</span>
</p>

<h2>Assertions</h2>
<table><thead><tr><th>Request</th><th>Assertion</th><th>Status</th></tr></thead>
<tbody>{rows}</tbody></table>

<h2>Run metadata</h2>
<table><tbody>
<tr><td>Model used</td><td><code>{model}</code></td></tr>
<tr><td>LLM tokens (total)</td><td><code>{tokens}</code></td></tr>
<tr><td>Collection hash</td><td><code>{coll_hash}</code></td></tr>
<tr><td>Input hash</td><td><code>{input_hash}</code></td></tr>
</tbody></table>
</body></html>"""


def main() -> int:
    print("=" * 72)
    print("STAGE: Summarize Newman results")
    print("=" * 72)
    print()

    report = Path("reports/report.json")
    if not report.exists():
        print(f"::warning::{report} not found — skipping summary")
        return 0

    data = json.loads(report.read_text())
    executions = data.get("run", {}).get("executions", [])
    stats = data.get("run", {}).get("stats", {}).get("requests", {})
    total = stats.get("total", 0)
    failed_count = stats.get("failed", 0)
    passed = total - failed_count

    rows = []
    for execution in executions:
        name = execution.get("item", {}).get("name", "?")
        assertions = execution.get("assertions", []) or []
        if not assertions:
            rows.append(
                f'<tr><td>{name}</td><td><em>no assertions recorded</em></td>'
                f'<td class="pass">-</td></tr>'
            )
            continue
        for assertion in assertions:
            failed = bool(assertion.get("error"))
            status_txt = "FAIL" if failed else "PASS"
            status_cls = "fail" if failed else "pass"
            rows.append(
                f'<tr><td>{name}</td>'
                f'<td>{assertion.get("assertion", "?")}</td>'
                f'<td class="{status_cls}">{status_txt}</td></tr>'
            )
    if not rows:
        rows.append('<tr><td colspan="3"><em>No requests executed.</em></td></tr>')

    html = HTML_TEMPLATE.format(
        env=os.environ.get("ENVIRONMENT_NAME", "dev"),
        base=os.environ.get("DEV_API_URL", "?"),
        total=total, passed=passed, failed=failed_count,
        rows="\n".join(rows),
        model=os.environ.get("GENAI_MODEL_USED", "demo-deterministic-builder"),
        tokens=os.environ.get("LLM_TOTAL_TOKENS", "0"),
        coll_hash=(os.environ.get("COLLECTION_HASH", "n/a"))[:16],
        input_hash=(os.environ.get("INPUT_HASH", "n/a"))[:16],
    )

    out = Path("reports/report_summary.html")
    out.write_text(html)
    print(f"  written: {out} ({len(html)} bytes)")

    gh_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if gh_summary:
        with open(gh_summary, "a") as fh:
            fh.write("### Newman run summary\n\n")
            fh.write(f"- Total: **{total}** · Passed: **{passed}** · Failed: **{failed_count}**\n")
            fh.write(f"- Model: `{os.environ.get('GENAI_MODEL_USED', 'demo-deterministic-builder')}`\n")
            fh.write(f"- Collection hash: `{(os.environ.get('COLLECTION_HASH', 'n/a'))[:16]}...`\n")
            fh.write(f"- Input hash: `{(os.environ.get('INPUT_HASH', 'n/a'))[:16]}...`\n")

    print()
    print(f"[OK] Summary written. Total: {total}, Passed: {passed}, Failed: {failed_count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
