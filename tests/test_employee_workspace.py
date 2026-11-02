"""The interface read model must not trigger agents, mutate cases, or expose HR flags."""
import copy
import json
import unittest
from unittest.mock import patch

from benefits_leave.web import employee_overview, handle
from benefits_leave.workflow import CaseStore, WorkflowError
from tests.test_benefits_leave import FakeClient, BrokenClient


class ReadOnlyWorkspace(unittest.TestCase):
    def setUp(self):
        self.store = CaseStore()

    def test_overview_does_not_run_agent_or_create_case(self):
        before = copy.deepcopy(self.store.cases)
        with patch('benefits_leave.agents.run_enrollment_agent') as agent:
            result = handle(self.store, '/api/employee/overview', {'employee_id': 'E2001'})
        agent.assert_not_called()
        self.assertEqual(self.store.cases, before)
        self.assertTrue(result['enrollment']['missing'])
        self.assertEqual(len(result['selections']), 4)

    def test_employee_projection_omits_hr_flags_and_other_cases(self):
        result = employee_overview(self.store, 'E2003')
        self.assertNotIn('hr_flags', json.dumps(result))
        self.assertNotIn('needs_hr_exception', json.dumps(result))
        self.assertEqual(result['cases'], [])
        self.assertEqual(result['employee']['id'], 'E2003')

    def test_seeded_case_is_visible_only_to_its_employee(self):
        owner = employee_overview(self.store, 'E2004')
        self.assertEqual(len(owner['cases']), 1)
        self.assertNotIn('handoff', owner['cases'][0])
        self.assertNotIn('history', owner['cases'][0])
        self.assertEqual(employee_overview(self.store, 'E2001')['cases'], [])

    def test_current_employee_gets_leave_options_without_hr_lookup_facts(self):
        result = employee_overview(self.store, 'E1001')
        self.assertIsNone(result['enrollment'])
        self.assertEqual(result['selections'], [])
        self.assertEqual(len(result['leave_types']), 4)
        self.assertNotIn('hours_worked_12mo', json.dumps(result))

    def test_unknown_employee_does_not_fall_back_to_another_person(self):
        with self.assertRaises(WorkflowError):
            employee_overview(self.store, 'E9999')

    def test_saved_guidance_is_employee_safe_and_survives_workspace_refresh(self):
        self.store.client = FakeClient()
        out = handle(self.store, '/api/employee/enrollment', {'employee_id': 'E2003'})
        case = employee_overview(self.store, 'E2003')['cases'][0]
        self.assertEqual(case['guidance'], out['message'])
        for private in ('ai', 'enrollment', 'hr_flags', 'history', 'handoff'):
            self.assertNotIn(private, case)
        self.assertEqual(employee_overview(self.store, 'E2002')['cases'], [])

    def test_unavailable_ai_does_not_hide_or_prevent_hr_review_of_complete_enrollment(self):
        self.store.client = BrokenClient()
        out = handle(self.store, '/api/employee/enrollment', {'employee_id': 'E2002'})
        case = employee_overview(self.store, 'E2002')['cases'][0]
        self.assertIsNone(case['guidance'])
        self.assertIn('API key', case['ai_error'])
        self.assertEqual(case['status'], 'ready_for_hr_review')
        handle(self.store, '/api/hr/decide', {'case_id': out['case']['id'], 'decision': 'approve'})
        handle(self.store, '/api/hr/vendor/prepare', {'case_id': out['case']['id']})
        handle(self.store, '/api/hr/vendor/sent', {'case_id': out['case']['id']})
        result = handle(self.store, '/api/hr/vendor/check', {'case_id': out['case']['id']})
        self.assertEqual(result['case']['status'], 'vendor_follow_up')
        self.assertTrue(result['case']['vendor']['ai_error'])
        self.assertTrue(result['case']['vendor']['follow_ups'])



if __name__ == "__main__":
    unittest.main()
