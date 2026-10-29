"""Read-only HR lookup used by the FMLA pre-check (made-up data in the demo).

Design rules (from the PRD):
- Look employees up by employee ID, never by name.
- Every number comes back with its units and an "as of" time.
- A failed lookup returns status "error" with NO balance field,
  so an error can never be mistaken for a balance of 0.
"""

import json
import re
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "fake_employees.json"
EMPLOYEE_ID_PATTERN = re.compile(r"^E\d{4}$")
NUMBER_FIELDS = ("hours_worked_12mo", "months_of_service", "leave_balance_hours")


def load_fake_hr_data():
    """Stand-in for the real HR system. Swap this out later; the tool stays the same."""
    with open(DATA_FILE) as f:
        return json.load(f)


def _error(reason, employee_id):
    return {"status": "error", "reason": reason, "employee_id": employee_id}


def lookup_employee_leave_balance(employee_id, fetch=load_fake_hr_data):
    """Return one employee's leave data, or an error. Never guesses."""
    if not isinstance(employee_id, str) or not EMPLOYEE_ID_PATTERN.match(employee_id):
        return _error("invalid_employee_id", employee_id)

    try:
        data = fetch()
    except TimeoutError:
        return _error("timeout", employee_id)
    except Exception:
        return _error("hr_system_unavailable", employee_id)

    record = data.get("employees", {}).get(employee_id)
    if record is None:
        return _error("not_found", employee_id)

    for field in NUMBER_FIELDS:
        value = record.get(field)
        # bool is a subclass of int in Python, so rule it out explicitly.
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            return _error("bad_data", employee_id)

    source = "lookup_employee_leave_balance"
    return {
        "status": "ok",
        "employee_id": employee_id,
        "as_of": data["as_of"],
        "facts": {
            "hours_worked_12mo": {"value": record["hours_worked_12mo"], "units": "hours",
                                  "source": f"{source}.hours_worked_12mo"},
            "months_of_service": {"value": record["months_of_service"], "units": "months",
                                  "source": f"{source}.months_of_service"},
            "leave_balance": {"value": record["leave_balance_hours"], "units": "hours",
                              "source": f"{source}.leave_balance_hours"},
        },
    }
