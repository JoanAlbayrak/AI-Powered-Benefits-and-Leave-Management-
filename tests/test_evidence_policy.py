"""T03: scoped fictional evidence, versioned demo policy and approved snapshot references."""

import copy
import unittest

from benefits_leave import checks
from benefits_leave.web import handle
from benefits_leave.workflow import CaseStore
from tests.test_benefits_leave import FakeClient


class Evidence(unittest.TestCase):
    def test_three_states_are_distinct(self):
        states = {eid: [e["state"] for e in checks.evidence_status(eid)] for eid in ("E2001", "E2005", "E2006")}
        self.assertEqual(states, {"E2001": ["received"], "E2005": ["absent"], "E2006": ["verified", "verified"]})

    def test_received_evidence_does_not_complete_the_item(self):
        self.assertIn("Upload marriage certificate for Spouse of A", checks.enrollment_status("E2001")["missing"])
        self.assertFalse(checks.evidence_status("E2001")[0]["counts_as_complete"])

    def test_fixture_verification_matches_hr_record(self):
        data = checks.load_data()
        for eid, hire in data["new_hires"].items():
            verified = {(e["requirement"], e["dependent"]) for e in checks.evidence_for(eid, data) if e["state"] == "verified"}
            for dep in hire["dependents"]:
                proof = data["rules"]["dependent_proof"][dep["relationship"]]
                self.assertEqual(dep["proof_received"], (proof, dep["name"]) in verified, (eid, dep["name"]))

    def test_evidence_is_scoped_to_one_employee(self):
        data = checks.load_data()
        data["evidence"]["E2005"] = [dict(data["evidence"]["E2006"][0])]   # someone else's record misfiled
        self.assertEqual(checks.evidence_for("E2005", data), [])
        self.assertEqual(checks.evidence_status("E2005", data)[0]["state"], "absent")

    def test_unverified_claim_in_metadata_cannot_override_hr_record(self):
        data = checks.load_data()
        data["evidence"]["E2005"] = [{"id": "X", "employee_id": "E2005", "requirement": "birth certificate",
                                      "dependent": "Child of E", "state": "verified"}]
        self.assertEqual(checks.evidence_status("E2005", data)[0]["state"], "received")

    def test_employee_overview_and_case_carry_evidence(self):
        store = CaseStore(client=FakeClient())
        overview = handle(store, "/api/employee/overview", {"employee_id": "E2001"})
        self.assertEqual(overview["evidence"][0]["state"], "received")
        _, case = store.check_enrollment("E2005")
        self.assertEqual(case["evidence"][0]["state"], "absent")
        self.assertEqual(handle(store, "/api/employee/overview", {"employee_id": "E1001"})["evidence"], [])


class Policy(unittest.TestCase):
    def test_entries_are_versioned_sourced_and_area_scoped(self):
        vendor = checks.policy_entries("vendor")
        self.assertIn("DEMO-VENDOR-SOURCE-OF-TRUTH@v1", {e["ref"] for e in vendor})
        self.assertNotIn("DEMO-LEAVE-FMLA-BASICS@v1", {e["ref"] for e in vendor})
        for entry in checks.policy_entries("enrollment") + checks.policy_entries("leave"):
            self.assertTrue(entry["source"] and entry["effective_from"] and entry["version"])

    def test_missing_policy_library_is_empty_not_invented(self):
        data = checks.load_data()
        del data["policy_library"]
        self.assertEqual(checks.policy_entries("leave", data), [])


class Snapshots(unittest.TestCase):
    def test_handoff_has_stable_reference_and_record_refs(self):
        handoff = checks.build_vendor_handoff("C7", "E2004")
        self.assertEqual(handoff["snapshot_ref"], "C7:approved:1")
        record = checks.approved_snapshot_record(handoff, "medical")
        self.assertEqual(record["ref"], "C7:approved:1/records/medical")
        self.assertEqual(record["record"]["tier"], "employee")
        self.assertIsNone(checks.approved_snapshot_record(handoff, "life"))

    def test_snapshot_record_ignores_later_election_edits(self):
        data = checks.load_data()
        handoff = checks.build_vendor_handoff("C7", "E2004", data)
        data["new_hires"]["E2004"]["elections"]["medical"]["tier"] = "family"
        self.assertEqual(checks.approved_snapshot_record(handoff, "medical")["record"]["tier"], "employee")
        copy.deepcopy(handoff)


if __name__ == "__main__":
    unittest.main()
