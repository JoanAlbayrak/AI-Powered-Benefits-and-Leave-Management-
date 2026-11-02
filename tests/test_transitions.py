"""Task 3: HR document verification, pending leave documents, correction and resubmission."""
import json
import unittest

from benefits_leave.web import employee_view, handle
from benefits_leave.workflow import CaseStore, WorkflowError
from tests.test_privacy import HR_ONLY_KEYS, client, keys_of

SPOUSE_TIER = {"status": "elected", "plan": "Silver PPO", "tier": "employee_spouse"}
FULL = {"leave_type": "own_health", "start_date": "2026-11-09", "end_date": "2026-11-20", "schedule": "continuous",
        "reason": "Surgery recovery", "documents_attached": ["medical certification"]}
NO_DOC = {**FULL, "documents_attached": []}


def post(store, path, **body):
    return handle(store, path, body)


class HrVerifiesReceivedProof(unittest.TestCase):
    """E2001 elected spouse coverage and uploaded the marriage certificate: received, not yet verified."""

    def setUp(self):
        self.store = CaseStore(client=client())
        _, self.case = self.store.check_enrollment("E2001")

    def test_received_proof_keeps_the_case_incomplete_and_unapprovable(self):
        self.assertEqual(self.case["status"], "incomplete")
        self.assertIn("Upload marriage certificate for Spouse of A", self.case["enrollment"]["missing"])
        with self.assertRaises(WorkflowError):
            self.store.hr_decide(self.case["id"], "approve")

    def test_hr_verifying_it_completes_the_item_and_makes_the_case_reviewable(self):
        self.store.set_election("E2001", "dental", {"status": "waived"})
        self.store.set_election("E2001", "retirement", {"status": "elected", "percent": 4})
        self.assertEqual(self.case["status"], "incomplete")      # still blocked by the unverified certificate
        revision = self.case["review_revision"]
        self.store.hr_verify_document(self.case["id"], "EV-E2001-01", expected_revision=revision)
        record = self.store.data["evidence"]["E2001"][0]
        self.assertEqual((record["state"], record["verified_by"], record["verified_on"]),
                         ("verified", "HR specialist (demo)", self.store.data["as_of"]))
        self.assertEqual(self.case["enrollment"]["missing"], [])
        self.assertEqual(self.case["status"], "ready_for_hr_review")
        self.assertEqual(self.case["evidence"][0]["state"], "verified")
        self.assertGreater(self.case["review_revision"], revision)
        self.assertEqual(self.store.hr_decide(self.case["id"], "approve")["status"], "approved")

    def test_a_stale_hr_view_cannot_verify(self):
        stale = self.case["review_revision"]
        self.store.set_election("E2001", "dental", {"status": "waived"})
        with self.assertRaises(WorkflowError):
            self.store.hr_verify_document(self.case["id"], "EV-E2001-01", expected_revision=stale)
        self.assertEqual(self.store.data["evidence"]["E2001"][0]["state"], "received")

    def test_only_a_received_document_belonging_to_this_employee_can_be_verified(self):
        with self.assertRaises(WorkflowError):                 # another employee's evidence id
            self.store.hr_verify_document(self.case["id"], "EV-E2006-01")
        with self.assertRaises(WorkflowError):                 # not a real id
            self.store.hr_verify_document(self.case["id"], "EV-NOPE")
        self.store.hr_verify_document(self.case["id"], "EV-E2001-01")
        with self.assertRaises(WorkflowError):                 # already verified
            self.store.hr_verify_document(self.case["id"], "EV-E2001-01")

    def test_a_document_that_was_never_received_cannot_be_verified(self):
        store = CaseStore(client=client())
        store.set_election("E2005", "medical", {"status": "elected", "plan": "Silver PPO", "tier": "employee_children"})
        _, case = store.check_enrollment("E2005")
        self.assertEqual(store.data["evidence"]["E2005"], [])
        with self.assertRaises(WorkflowError):
            store.hr_verify_document(case["id"], "EV-E2005-01")

    def test_the_employee_upload_path_can_never_verify(self):
        store = CaseStore(client=client())
        store.set_election("E2005", "medical", {"status": "elected", "plan": "Silver PPO", "tier": "employee_children"})
        store.add_dependent("E2005", "child", "Kid")
        store.mark_document_uploaded("E2005", "child", "Kid")
        state = next(e for e in store.data["evidence"]["E2005"] if e["dependent"] == "Kid")
        self.assertEqual((state["state"], state["verified_by"]), ("received", None))

    def test_there_is_no_employee_route_that_verifies(self):
        for path in ("/api/employee/evidence/verify", "/api/employee/enrollment/verify",
                     "/api/employee/leave/resolve"):
            with self.assertRaises(WorkflowError):
                post(self.store, path, employee_id="E2001", case_id=self.case["id"], evidence_ref="EV-E2001-01")

    def test_a_decided_case_can_no_longer_have_documents_verified(self):
        store = CaseStore(client=client())
        _, case = store.check_enrollment("E2002")
        store.hr_decide(case["id"], "approve")
        with self.assertRaises(WorkflowError):
            store.hr_verify_document(case["id"], "EV-E2002-01")

    def test_the_verification_is_visible_to_the_employee_without_hr_internals(self):
        self.store.hr_verify_document(self.case["id"], "EV-E2001-01")
        view = post(self.store, "/api/employee/cases", employee_id="E2001")["cases"][0]
        self.assertTrue(any("Verified the marriage certificate" in a["action"] for a in view["activity"]))
        self.assertFalse({k for k in keys_of(view) if k in HR_ONLY_KEYS})


class PendingLeaveDocuments(unittest.TestCase):
    def setUp(self):
        self.store = CaseStore(client=client())
        draft = post(self.store, "/api/employee/leave/draft", employee_id="E1001", **NO_DOC)["draft"]
        _, self.case, _ = self.store.confirm_leave_draft("E1001", draft["id"], True)
        self.store.hr_decide(self.case["id"], "approved_pending_documents", "a signed doctor's note")
        self.case_id = self.case["id"]

    def test_the_conditional_approval_lists_what_is_requested(self):
        documents = [i["document"] for i in self.case["pending_documents"]]
        self.assertEqual(documents, ["medical certification", "a signed doctor's note"])
        self.assertTrue(all(i["state"] == "requested" for i in self.case["pending_documents"]))

    def test_the_full_loop_received_then_verified_then_approved(self):
        self.store.provide_leave_document("E1001", self.case_id, "medical certification")
        self.assertEqual(self.case["status"], "approved_pending_documents")      # one document still outstanding
        self.store.provide_leave_document("E1001", self.case_id, "a signed doctor's note")
        self.assertEqual(self.case["status"], "approved_documents_received")
        self.assertTrue(all(i["state"] == "received" for i in self.case["pending_documents"]))   # not verified yet
        self.assertNotEqual(self.case["status"], "approved")
        self.store.hr_resolve_pending_documents(self.case_id, "verify_documents")
        self.assertEqual(self.case["status"], "approved")
        self.assertTrue(all(i["state"] == "verified" for i in self.case["pending_documents"]))
        self.assertIn("fully approved", self.case["employee_update"])

    def test_hr_can_ask_again_and_then_withdraw(self):
        for item in ("medical certification", "a signed doctor's note"):
            self.store.provide_leave_document("E1001", self.case_id, item)
        with self.assertRaises(WorkflowError):
            self.store.hr_resolve_pending_documents(self.case_id, "request_again", "")      # reason needed
        self.store.hr_resolve_pending_documents(self.case_id, "request_again", "The note is unsigned")
        self.assertEqual(self.case["status"], "approved_pending_documents")
        self.assertTrue(all(i["state"] == "requested" for i in self.case["pending_documents"]))
        self.assertIn("unsigned", self.case["employee_update"])
        self.store.hr_resolve_pending_documents(self.case_id, "withdraw_approval", "Never received")
        self.assertEqual(self.case["status"], "denied")
        self.assertEqual([d["decision"] for d in self.case["decision_history"]], ["request_again", "withdraw_approval"])

    def test_hr_cannot_verify_what_has_not_been_received(self):
        with self.assertRaises(WorkflowError):
            self.store.hr_resolve_pending_documents(self.case_id, "verify_documents")
        self.assertEqual(self.case["status"], "approved_pending_documents")

    def test_only_a_requested_document_can_be_provided_and_only_once(self):
        with self.assertRaises(WorkflowError):
            self.store.provide_leave_document("E1001", self.case_id, "my passport")
        self.store.provide_leave_document("E1001", self.case_id, "medical certification")
        with self.assertRaises(WorkflowError):
            self.store.provide_leave_document("E1001", self.case_id, "medical certification")

    def test_another_employee_cannot_touch_this_request(self):
        with self.assertRaises(WorkflowError):
            self.store.provide_leave_document("E1002", self.case_id, "medical certification")
        with self.assertRaises(WorkflowError):
            self.store.resubmit_leave("E1002", self.case_id, FULL)

    def test_documents_cannot_be_provided_when_none_are_requested(self):
        draft = post(self.store, "/api/employee/leave/draft", employee_id="E1002", **FULL)["draft"]
        _, other, _ = self.store.confirm_leave_draft("E1002", draft["id"], True)
        with self.assertRaises(WorkflowError):
            self.store.provide_leave_document("E1002", other["id"], "medical certification")

    def test_the_employee_view_shows_request_state_but_no_hr_data(self):
        self.store.provide_leave_document("E1001", self.case_id, "medical certification")
        view = employee_view(self.case)
        self.assertEqual([i["state"] for i in view["pending_documents"]], ["received", "requested"])
        self.assertFalse({k for k in keys_of(view) if k in HR_ONLY_KEYS})
        self.assertNotIn("FMLA", json.dumps(view))

    def test_the_endpoints_run_the_same_loop(self):
        post(self.store, "/api/employee/leave/document", employee_id="E1001", case_id=self.case_id,
             document="medical certification")
        post(self.store, "/api/employee/leave/document", employee_id="E1001", case_id=self.case_id,
             document="a signed doctor's note")
        out = post(self.store, "/api/hr/leave/resolve", case_id=self.case_id, resolution="verify_documents")
        self.assertEqual(out["case"]["status"], "approved")


class CorrectionAndResubmission(unittest.TestCase):
    def setUp(self):
        self.store = CaseStore(client=client())

    def test_leave_is_corrected_on_the_same_case_and_returns_to_hr(self):
        draft = post(self.store, "/api/employee/leave/draft", employee_id="E1001", **NO_DOC)["draft"]
        _, case, _ = self.store.confirm_leave_draft("E1001", draft["id"], True)
        self.store.hr_decide(case["id"], "request_info", "Please add the medical certification")
        self.assertEqual(case["status"], "info_requested")
        with self.assertRaises(WorkflowError):                  # HR can't decide while it waits on the employee
            self.store.hr_decide(case["id"], "approve", "anyway")
        cases_before = len(self.store.cases)
        result, same = self.store.resubmit_leave("E1001", case["id"], FULL)
        self.assertIs(same, case)
        self.assertEqual(len(self.store.cases), cases_before)   # no new case
        self.assertEqual(case["status"], "ready_for_hr_review")
        self.assertEqual(case["resubmissions"], 1)
        self.assertTrue(result["check"]["complete"])
        self.assertEqual(case["decision_history"][0]["decision"], "request_info")
        self.assertNotIn("decision", case)                      # the old decision no longer stands
        self.assertEqual(self.store.hr_decide(case["id"], "approve")["status"], "approved")

    def test_resubmission_needs_a_request_hr_actually_sent_back(self):
        draft = post(self.store, "/api/employee/leave/draft", employee_id="E1001", **FULL)["draft"]
        _, case, _ = self.store.confirm_leave_draft("E1001", draft["id"], True)
        with self.assertRaises(WorkflowError):
            self.store.resubmit_leave("E1001", case["id"], FULL)

    def test_resubmission_still_needs_valid_dates_and_schedule(self):
        draft = post(self.store, "/api/employee/leave/draft", employee_id="E1001", **NO_DOC)["draft"]
        _, case, _ = self.store.confirm_leave_draft("E1001", draft["id"], True)
        self.store.hr_decide(case["id"], "request_info", "Fix the dates")
        with self.assertRaises(WorkflowError):
            self.store.resubmit_leave("E1001", case["id"], {**FULL, "end_date": "2026-11-01"})
        self.assertEqual(case["status"], "info_requested")      # a failed attempt changes nothing

    def test_the_resubmit_endpoint_returns_only_employee_data(self):
        draft = post(self.store, "/api/employee/leave/draft", employee_id="E1003", **FULL)["draft"]
        _, case, _ = self.store.confirm_leave_draft("E1003", draft["id"], True)
        self.store.hr_decide(case["id"], "request_info", "Please confirm the dates")
        out = post(self.store, "/api/employee/leave/resubmit", employee_id="E1003", case_id=case["id"], **FULL)
        self.assertFalse({k for k in keys_of(out) if k in HR_ONLY_KEYS})
        self.assertEqual(out["case"]["status"], "ready_for_hr_review")

    def test_enrollment_edits_wait_for_the_employees_resubmission(self):
        _, case = self.store.check_enrollment("E2001")
        self.store.hr_decide(case["id"], "request_info", "Please finish dental and retirement")
        self.store.set_election("E2001", "dental", {"status": "waived"})
        self.assertEqual(case["status"], "info_requested")      # an edit alone doesn't re-queue it for HR
        self.store.set_election("E2001", "retirement", {"status": "elected", "percent": 4})
        self.store.hr_verify_document(case["id"], "EV-E2001-01")
        self.assertEqual(case["status"], "info_requested")
        _, same = self.store.check_enrollment("E2001")          # the resubmission
        self.assertIs(same, case)
        self.assertEqual(case["status"], "ready_for_hr_review")
        self.assertEqual(case["resubmissions"], 1)
        self.assertIn("back with HR", case["employee_update"])
        self.assertEqual(case["decision_history"][0]["decision"], "request_info")
        self.assertEqual(self.store.hr_decide(case["id"], "approve")["status"], "approved")

    def test_an_unfinished_enrollment_resubmission_goes_back_incomplete(self):
        _, case = self.store.check_enrollment("E2001")
        self.store.hr_decide(case["id"], "request_info", "Please finish")
        self.store.check_enrollment("E2001")                    # resubmits without fixing anything
        self.assertEqual(case["status"], "incomplete")
        with self.assertRaises(WorkflowError):
            self.store.hr_decide(case["id"], "approve")


if __name__ == "__main__":
    unittest.main()
