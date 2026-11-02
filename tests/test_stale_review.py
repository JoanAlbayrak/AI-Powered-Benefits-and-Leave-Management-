"""HR can only approve the enrollment the employee actually has now (task 1: stale approval)."""
import unittest

from benefits_leave import checks
from benefits_leave.web import make_handler  # noqa: F401
from benefits_leave.workflow import CaseStore, StaleReviewError, WorkflowError
from tests.test_benefits_leave import FakeClient

FAMILY = {"status": "elected", "plan": "Gold HMO", "tier": "family"}


class StaleApproval(unittest.TestCase):
    def setUp(self):
        self.store = CaseStore(client=FakeClient())
        _, self.case = self.store.check_enrollment("E2002")

    def approve_fails(self, **kwargs):
        with self.assertRaises(WorkflowError) as ctx:
            self.store.hr_decide(self.case["id"], "approve", **kwargs)
        self.assertEqual(self.case["status"] in ("approved",), False)
        self.assertNotIn("handoff", self.case)
        return str(ctx.exception)

    def test_the_reported_bug_family_coverage_without_dependents(self):
        self.assertEqual(self.case["status"], "ready_for_hr_review")
        self.assertEqual(self.case["enrollment"]["missing"], [])
        self.store.set_election("E2002", "medical", FAMILY)
        # the saved review follows the data instead of keeping the old "complete" result
        self.assertEqual(self.case["status"], "incomplete")
        self.assertEqual(len(self.case["enrollment"]["missing"]), 2)
        self.assertIn("missing items", self.approve_fails())
        self.assertTrue(any("spouse" in item for item in self.case["enrollment"]["missing"]))

    def test_edit_discards_the_old_ai_summary_and_bumps_the_revision(self):
        revision = self.case["review_revision"]
        self.assertTrue(self.case["ai"])
        self.store.set_election("E2002", "dental", {"status": "waived"})
        self.assertIsNone(self.case["ai"])
        self.assertTrue(self.case["ai_stale"])
        self.assertEqual(self.case["review_revision"], revision + 1)
        self.assertTrue(any("Refreshed the saved review" in a["action"] for a in self.case["activity"]))

    def test_a_direct_data_change_is_caught_at_approval_and_refreshes_the_case(self):
        # Even a change that bypasses set_election cannot slip through.
        self.store.data["new_hires"]["E2002"]["elections"]["medical"] = dict(FAMILY)
        message = self.approve_fails()
        self.assertIn("changed since this case was reviewed", message)
        self.assertEqual(self.case["status"], "incomplete")           # refreshed
        self.assertEqual(len(self.case["enrollment"]["missing"]), 2)

    def test_hr_must_decide_on_the_version_they_opened(self):
        opened = self.case["review_revision"]
        self.store.set_election("E2002", "dental", {"status": "elected", "plan": "Plus Dental", "tier": "employee"})
        self.assertIn("changed after you opened it", self.approve_fails(expected_revision=opened))
        # opening the refreshed case and approving that revision works
        decided = self.store.hr_decide(self.case["id"], "approve", expected_revision=self.case["review_revision"])
        self.assertEqual(decided["status"], "approved")

    def test_a_stale_decision_is_a_distinct_conflict_the_page_can_reload_from(self):
        opened = self.case["review_revision"]
        self.store.set_election("E2002", "dental", {"status": "waived"})
        with self.assertRaises(StaleReviewError):
            self.store.hr_decide(self.case["id"], "approve", expected_revision=opened)
        with self.assertRaises(StaleReviewError):
            self.store.hr_verify_document(self.case["id"], "EV-E2002-01", expected_revision=opened)
        # an ordinary rule violation is NOT flagged stale: the page keeps the user's typed reason
        with self.assertRaises(WorkflowError) as ctx:
            self.store.hr_decide(self.case["id"], "deny", "")
        self.assertNotIsInstance(ctx.exception, StaleReviewError)

    def test_the_web_layer_marks_only_conflicts_as_stale(self):
        import json as _json
        from http.server import ThreadingHTTPServer
        import threading, urllib.request
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.store))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.shutdown)

        def post(body):
            req = urllib.request.Request(f"http://127.0.0.1:{server.server_port}/api/hr/decide",
                                         data=_json.dumps(body).encode(), headers={"Content-Type": "application/json"})
            return _json.loads(urllib.request.urlopen(req).read())
        opened = self.case["review_revision"]
        self.store.set_election("E2002", "dental", {"status": "waived"})
        stale = post({"case_id": self.case["id"], "decision": "approve", "review_revision": opened})
        self.assertTrue(stale["stale"])
        plain = post({"case_id": self.case["id"], "decision": "deny", "reason": ""})
        self.assertNotIn("stale", plain)

    def test_the_frozen_handoff_matches_the_reviewed_selections(self):
        self.store.set_election("E2002", "medical", {"status": "elected", "plan": "Silver PPO", "tier": "employee"})
        self.store.hr_decide(self.case["id"], "approve", expected_revision=self.case["review_revision"])
        medical = next(r for r in self.case["handoff"]["records"] if r["benefit"] == "medical")
        self.assertEqual((medical["plan"], medical["tier"]), ("Silver PPO", "employee"))
        self.assertEqual(self.case["decision"]["reviewed_revision"], self.case["review_revision"])
        self.assertEqual(self.case["review_fingerprint"], self.store._review_fingerprint("E2002"))

    def test_dependent_and_document_edits_also_refresh_the_review(self):
        self.store.set_election("E2002", "medical", FAMILY)
        self.store.add_dependent("E2002", "spouse", "Spouse of B")
        self.store.add_dependent("E2002", "child", "Child of B")
        self.assertEqual(self.case["status"], "incomplete")
        self.store.mark_document_uploaded("E2002", "spouse", "Spouse of B")
        # received is not verified: the item stays open and approval stays blocked
        self.assertIn("Upload marriage certificate for Spouse of B", self.case["enrollment"]["missing"])
        self.assertIn("missing items", self.approve_fails())

    def test_approving_an_unchanged_complete_case_still_works(self):
        decided = self.store.hr_decide(self.case["id"], "approve")
        self.assertEqual(decided["status"], "approved")
        self.assertEqual(len(decided["handoff"]["records"]), 3)

    def test_non_approval_decisions_use_the_current_revision_too(self):
        opened = self.case["review_revision"]
        self.store.set_election("E2002", "dental", {"status": "waived"})
        with self.assertRaises(WorkflowError):
            self.store.hr_decide(self.case["id"], "request_info", "Please confirm", expected_revision=opened)

    def test_decided_cases_stay_locked_to_what_was_approved(self):
        self.store.hr_decide(self.case["id"], "approve")
        before = checks.vendor_records("E2002", self.store.data)
        with self.assertRaises(WorkflowError):
            self.store.set_election("E2002", "medical", FAMILY)
        self.assertEqual(self.case["handoff"]["records"], before)


if __name__ == "__main__":
    unittest.main()
