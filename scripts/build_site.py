"""Build the public demo website (docs/index.html) from the laptop page.

    python3 scripts/build_site.py

The website uses the same page as `python -m benefits_leave.web`, but instead of
calling the local server it answers in the browser with site/demo.js (the same
checks and workflow, written in JavaScript). No server and no API key: the AI
messages are examples written from the check results. GitHub Pages serves the
docs/ folder.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "benefits_leave" / "web_page.html"
DEMO_JS = ROOT / "site" / "demo.js"
OUT = ROOT / "docs" / "index.html"

SERVER_API = """async function api(path, body) {
  const res = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" },
                                  body: JSON.stringify(body || {}) });
  return res.json();
}"""

BROWSER_API = """const demoHandle = Demo.makeHandler(new Demo.CaseStore(BENEFITS_DATA, HR_DATA));
async function api(path, body) {
  await new Promise((r) => setTimeout(r, 400));   // a short pause so each step is visible
  return demoHandle(path, body);
}"""

BANNER = """  <div class="card" style="background:#fff4dc;border-color:#f0dca8">
    <b>Demo mode.</b> All people, plans and vendors are made up, and nothing is saved: reload the page to start over.
    The checks and the HR workflow are real. The AI agents' messages are examples written from the check results;
    the live version calls Claude and runs on the project owner's laptop.
    <a href="https://github.com/JoanAlbayrak/AI-Powered-Benefits-and-Leave-Management-">See the code on GitHub</a>.
  </div>
"""


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise SystemExit(f"build_site: expected exactly one match for:\n{old[:80]}")
    return text.replace(old, new)


def build():
    page = PAGE.read_text()
    benefits = json.loads((ROOT / "data" / "benefits_demo.json").read_text())
    hr = json.loads((ROOT / "data" / "fake_employees.json").read_text())
    data_js = f"const BENEFITS_DATA = {json.dumps(benefits)};\nconst HR_DATA = {json.dumps(hr)};\n"

    page = replace_once(page, SERVER_API, BROWSER_API)
    page = replace_once(page, "<script>\nconst $ =",
                        f"<script>\n{data_js}</script>\n<script>\n{DEMO_JS.read_text()}</script>\n<script>\nconst $ =")
    page = replace_once(page, '  <div class="tabs">', BANNER + '  <div class="tabs">')
    page = page.replace(" (10–30 seconds)", "")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(page)
    return OUT


if __name__ == "__main__":
    print(f"Built {build().relative_to(ROOT)}")
