"""The public website must give the same results as the Python system.

Runs the same cases through benefits_leave (Python) and site/demo.js (the
website's JavaScript) and compares them. Needs Node.js; skipped without it.
"""

import json
import shutil
import subprocess
import unittest
from pathlib import Path

from benefits_leave import checks
from benefits_leave.hr_lookup import load_fake_hr_data
from benefits_leave.workflow import CaseStore, WorkflowError
from scripts import build_site

ROOT = Path(__file__).resolve().parent.parent
NODE = shutil.which("node")

LEAVE_REQUESTS = [
    {"employee_id": "E1001", "leave_type": "own_health", "start_date": "2026-11-01", "end_date": "2026-12-01",
     "documents_attached": ["medical certification"]},
    {"employee_id": "E1003", "leave_type": "family_care", "start_date": "2026-11-01", "end_date": "2026-12-01",
     "documents_attached": []},
    {"employee_id": "E1002", "leave_type": "", "start_date": "2026-12-01", "end_date": "2026-11-01"},
    {"employee_id": "E1004", "leave_type": "bonding", "start_date": "2026-11-01", "end_date": "2026-11-20"},
    {"employee_id": "E1005", "leave_type": "personal", "start_date": "2026-11-01", "end_date": "2026-11-02"},
    {"employee_id": "bob", "leave_type": "vacation", "start_date": "2026-11-01", "end_date": "2026-11-02"},
]

# HR-side steps run through both systems: [action, case_id or employee_id, extra]
STEPS = [
    ["enroll", "E2001"], ["enroll", "E2002"], ["enroll", "E2003"],
    ["decide", "C2", "approve", ""],                      # blocked: items missing
    ["decide", "C4", "approve", ""],                      # blocked: HR flag needs a reason
    ["decide", "C4", "approve", "Variable-hour policy"],
    ["decide", "C3", "approve", ""],
    ["prepare", "C3"], ["sent", "C3"], ["check", "C3"],
    ["check", "C1"],
    ["enroll", "E2002"],                                # reuse decided case without reopening
    ["leave", 0], ["decide", "C5", "approve", ""],
    ["leave", 1], ["decide", "C6", "approve", ""], ["decide", "C6", "request_info", "Please upload the certification"],
    ["decide", "C6", "deny", "x"],                        # blocked: already decided
    ["leave", 1], ["decide", "C7", "approve", "Certification confirmed by phone"],   # incomplete, with a reason
]

JS_RUNNER = """
const Demo = require(process.argv[1]);
const input = JSON.parse(require("fs").readFileSync(0, "utf8"));
const { benefits, hr, leaveRequests, steps } = input;
const out = {};
out.enrollment = Object.keys(benefits.new_hires).concat(["E9999"]).map((id) => Demo.enrollmentStatus(id, benefits));
out.handoffs = Object.keys(benefits.new_hires).map((id) => Demo.buildVendorHandoff("C9", id, benefits, "test"));
out.reconcile = out.handoffs.map((h) => Demo.reconcileVendorConfirmations(h, benefits));
out.leave = leaveRequests.map((r) => Demo.leaveRequestCheck(r, benefits, hr));
const store = new Demo.CaseStore(benefits, hr);
out.steps = steps.map(([action, a, b, c]) => {
  try {
    if (action === "enroll") return store.checkEnrollment(a)[1].status;
    if (action === "leave") return store.submitLeave(leaveRequests[a])[1].status;
    if (action === "decide") return store.hrDecide(a, b, c).status;
    if (action === "prepare") return store.prepareVendorRecords(a).status;
    if (action === "sent") return store.markSent(a).status;
    if (action === "check") return store.checkVendorConfirmations(a).status;
  } catch (e) { return "error: " + e.message; }
});
out.history = store.hrQueue().map((c) => c.history);
console.log(JSON.stringify(out));
"""


def run_python():
    benefits, hr = checks.load_data(), load_fake_hr_data()
    lookup = lambda eid: checks.lookup_employee_leave_balance(eid, fetch=lambda: hr)  # noqa: E731
    out = {
        "enrollment": [checks.enrollment_status(i, benefits) for i in list(benefits["new_hires"]) + ["E9999"]],
        "handoffs": [checks.build_vendor_handoff("C9", i, benefits, "test") for i in benefits["new_hires"]],
    }
    out["reconcile"] = [checks.reconcile_vendor_confirmations(h, benefits) for h in out["handoffs"]]
    out["leave"] = [checks.leave_request_check(r, benefits, lookup=lookup) for r in LEAVE_REQUESTS]
    store = CaseStore(data=benefits, client=_NoAI(), lookup=lookup)
    steps = []
    for action, a, *rest in STEPS:
        try:
            if action == "enroll":
                steps.append(store.check_enrollment(a)[1]["status"])
            elif action == "leave":
                steps.append(store.submit_leave(dict(LEAVE_REQUESTS[a]))[1]["status"])
            elif action == "decide":
                steps.append(store.hr_decide(a, rest[0], rest[1])["status"])
            elif action == "prepare":
                steps.append(store.prepare_vendor_records(a)["status"])
            elif action == "sent":
                steps.append(store.mark_sent(a)["status"])
            elif action == "check":
                steps.append(store.check_vendor_confirmations(a)["status"])
        except WorkflowError as exc:
            steps.append(f"error: {exc}")
    out["steps"] = steps
    out["history"] = [c["history"] for c in store.hr_queue()]
    return out


class _NoAI:
    """A client that always fails, so Python runs on code results only (like the website)."""

    def __init__(self):
        self.beta = self

    @property
    def messages(self):
        return self

    def create(self, **kwargs):
        raise ConnectionError("no AI in this test")


@unittest.skipUnless(NODE, "Node.js is not installed")
class WebsiteMatchesPython(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        payload = json.dumps({"benefits": checks.load_data(), "hr": load_fake_hr_data(),
                              "leaveRequests": LEAVE_REQUESTS, "steps": STEPS})
        proc = subprocess.run([NODE, "-e", JS_RUNNER, str(ROOT / "site" / "demo.js")], input=payload,
                              capture_output=True, text=True, check=True)
        cls.js = json.loads(proc.stdout)
        cls.py = json.loads(json.dumps(run_python()))

    def test_enrollment_checks_match(self):
        self.assertEqual(self.js["enrollment"], self.py["enrollment"])

    def test_vendor_handoffs_and_reconciliation_match(self):
        self.assertEqual(self.js["handoffs"], self.py["handoffs"])
        self.assertEqual(self.js["reconcile"], self.py["reconcile"])

    def test_leave_checks_match(self):
        self.assertEqual(self.js["leave"], self.py["leave"])

    def test_workflow_steps_and_guards_match(self):
        self.assertEqual(self.js["steps"], self.py["steps"])
        self.assertEqual(self.js["history"], self.py["history"])


class WebsiteIsBuilt(unittest.TestCase):
    def test_docs_page_is_up_to_date(self):
        built = (ROOT / "docs" / "index.html").read_text()
        build_site.build()
        self.assertEqual((ROOT / "docs" / "index.html").read_text(), built,
                         "docs/index.html was out of date: run python3 scripts/build_site.py and commit it")

    def test_website_has_no_api_key_or_server_calls(self):
        page = (ROOT / "docs" / "index.html").read_text()
        self.assertNotIn("sk-ant", page)
        self.assertNotIn("fetch(", page)
        self.assertNotIn("ANTHROPIC_API_KEY", page)
