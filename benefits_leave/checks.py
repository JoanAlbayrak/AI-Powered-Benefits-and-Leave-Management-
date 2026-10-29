"""Deterministic checks. Plain code, not AI.

Everything that must always be right (what's missing, deadlines, eligibility,
vendor records, discrepancies, leave documents) is computed here. The agents
explain these results; they never decide them.
"""

import json
from datetime import date, timedelta
from pathlib import Path

from benefits_leave.hr_lookup import lookup_employee_leave_balance

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "benefits_demo.json"
RETIREMENT = "retirement"


def load_data(path=DATA_FILE):
    return json.loads(Path(path).read_text())


def _as_of(data):
    return date.fromisoformat(data["as_of"])


def _coverage_start(start_date):
    """Coverage starts on the first of the month after the start date."""
    first_next = (start_date.replace(day=1) + timedelta(days=32)).replace(day=1)
    return first_next


# --- Workflow A: new-hire enrollment ---------------------------------------------------

def enrollment_status(employee_id, data=None):
    """What's done, what's missing, the deadline, and anything HR must look at."""
    data = data or load_data()
    hire = data["new_hires"].get(employee_id)
    if hire is None:
        return {"status": "error", "reason": "not_found", "employee_id": employee_id}

    rules = data["rules"]
    start = date.fromisoformat(hire["start_date"])
    deadline = start + timedelta(days=rules["enrollment_window_days"])
    days_left = (deadline - _as_of(data)).days
    elections = hire["elections"]
    missing, hr_flags, notes, done = [], [], [], []

    for benefit in rules["benefit_types"]:
        election = elections.get(benefit, {"status": "not_started"})
        if election["status"] == "not_started":
            missing.append(f"Choose a {benefit} plan or waive {benefit} coverage")
            continue
        if election["status"] == "waived":
            done.append(f"{benefit.capitalize()}: waived")
            continue
        plan, tier = election.get("plan"), election.get("tier")
        cost = data["plans"][benefit].get(plan, {}).get(tier)
        if cost is None:
            hr_flags.append(f"{benefit.capitalize()}: plan or coverage tier not recognized ({plan}, {tier})")
            continue
        done.append(f"{benefit.capitalize()}: {plan}, {tier.replace('_', ' + ')} tier, ${cost:.2f} per paycheck")
        if hire["weekly_hours"] < rules["benefits_eligible_min_weekly_hours"]:
            hr_flags.append(
                f"{benefit.capitalize()} elected, but {hire['weekly_hours']} hours/week is under the "
                f"{rules['benefits_eligible_min_weekly_hours']}-hour benefits eligibility rule"
            )
        for relationship in rules["tier_dependents"][tier]:
            people = [d for d in hire["dependents"] if d["relationship"] == relationship]
            proof = rules["dependent_proof"][relationship]
            if not people:
                missing.append(f"Add your {relationship} as a dependent for the {tier.replace('_', ' + ')} tier")
            for person in people:
                if not person["proof_received"]:
                    item = f"Upload {proof} for {person['name']}"
                    if item not in missing:
                        missing.append(item)

    plan = data["retirement_plan"]
    retirement = elections.get(RETIREMENT, {"status": "not_started"})
    if retirement["status"] == "not_started":
        missing.append("Choose a retirement contribution (or choose 0% to decline)")
    else:
        percent = retirement.get("percent", 0)
        done.append(f"Retirement: {percent}% contribution")
        if percent < plan["match_up_to_percent"]:
            notes.append(
                f"Your {percent}% contribution is below the {plan['match_up_to_percent']}% the employer "
                f"matches. ({plan['match_rule']}.)"
            )

    if days_left < 0:
        hr_flags.append(f"Enrollment deadline passed on {deadline.isoformat()}")
    elif missing and days_left <= 7:
        hr_flags.append(f"Deadline in {days_left} days with items still missing")

    if missing:
        state = "incomplete"
    elif hr_flags:
        state = "needs_hr_exception"
    else:
        state = "complete"

    return {
        "status": "ok",
        "employee_id": employee_id,
        "name": hire["name"],
        "start_date": hire["start_date"],
        "deadline": deadline.isoformat(),
        "days_left": days_left,
        "enrollment_state": state,
        "done": done,
        "missing": missing,
        "hr_flags": hr_flags,
        "notes": notes,
        "as_of": data["as_of"],
    }


def plan_options(data=None):
    data = data or load_data()
    return {"plans": data["plans"], "retirement_plan": data["retirement_plan"],
            "enrollment_window_days": data["rules"]["enrollment_window_days"]}


# --- Workflow A: vendor records and follow-up ------------------------------------------

def vendor_records(employee_id, data=None):
    """Vendor-ready records for an APPROVED enrollment. Nothing is sent from here."""
    data = data or load_data()
    hire = data["new_hires"][employee_id]
    coverage_start = _coverage_start(date.fromisoformat(hire["start_date"])).isoformat()
    records = []
    for benefit in data["rules"]["benefit_types"]:
        election = hire["elections"].get(benefit, {})
        if election.get("status") != "elected":
            continue
        dependents = [d["name"] for d in hire["dependents"]
                      if d["relationship"] in data["rules"]["tier_dependents"][election["tier"]]]
        records.append({
            "vendor": data["vendors"][benefit], "benefit": benefit, "employee_id": employee_id,
            "employee_name": hire["name"], "plan": election["plan"], "tier": election["tier"],
            "coverage_start": coverage_start, "dependents": dependents,
            "employee_cost_per_paycheck": data["plans"][benefit][election["plan"]][election["tier"]],
        })
    retirement = hire["elections"].get(RETIREMENT, {})
    if retirement.get("status") == "elected":
        records.append({
            "vendor": data["vendors"][RETIREMENT], "benefit": RETIREMENT, "employee_id": employee_id,
            "employee_name": hire["name"], "contribution_percent": retirement["percent"],
            "first_payroll_after": hire["start_date"],
        })
    return records


HANDOFF_FIELDS = ("case_id", "employee_id", "employee_name", "approved_as_of", "hr_reason",
                  "enrollment_summary", "records")


def build_vendor_handoff(case_id, employee_id, data=None, hr_reason="", enrollment_summary=None):
    """The handoff from the enrollment side to the Vendor Agent, frozen at HR approval.

    The Vendor Agent works only from this packet, so vendors get exactly what HR
    approved, even if the employee's data changes afterwards.
    """
    data = data or load_data()
    return {
        "case_id": case_id,
        "employee_id": employee_id,
        "employee_name": data["new_hires"][employee_id]["name"],
        "approved_as_of": data["as_of"],
        "hr_reason": hr_reason,
        "enrollment_summary": enrollment_summary,   # the Enrollment Agent's HR summary (may be None)
        "records": vendor_records(employee_id, data),
    }


def validate_vendor_handoff(handoff):
    """Problems with a handoff packet. An empty list means it's safe to use."""
    if not isinstance(handoff, dict):
        return ["The handoff is missing"]
    problems = [f"Missing field: {f}" for f in HANDOFF_FIELDS if f not in handoff]
    records = handoff.get("records")
    if not records:
        problems.append("The handoff has no vendor records")
    for record in records or []:
        if record.get("employee_id") != handoff.get("employee_id"):
            problems.append(f"A {record.get('benefit')} record belongs to a different employee")
        if not record.get("vendor") or not record.get("benefit"):
            problems.append("A vendor record is missing its vendor or benefit")
    return problems


def reconcile_vendor_confirmations(handoff, data=None):
    """Compare what we sent (the approved handoff) with what each vendor confirmed."""
    data = data or load_data()
    confirmations = data["vendor_confirmations"].get(handoff["employee_id"], {})
    results = []
    for record in handoff["records"]:
        benefit = record["benefit"]
        conf = confirmations.get(benefit)
        if conf is None or conf.get("status") == "missing":
            results.append({"benefit": benefit, "vendor": record["vendor"], "result": "no_confirmation",
                            "detail": "No confirmation received from the vendor yet"})
        elif conf["status"] == "pending":
            results.append({"benefit": benefit, "vendor": record["vendor"], "result": "pending",
                            "detail": "Vendor has not finished processing"})
        else:
            problems = []
            for field in ("plan", "tier", "contribution_percent"):
                key = "percent" if field == "contribution_percent" else field
                if field in record and conf.get(key) != record[field]:
                    problems.append(f"{field.replace('_', ' ')}: we sent {record[field]}, vendor shows {conf.get(key)}")
            results.append({"benefit": benefit, "vendor": record["vendor"],
                            "result": "discrepancy" if problems else "confirmed",
                            "detail": "; ".join(problems) if problems else "Matches what was sent"})
    return results


# --- Workflow B: leave request ---------------------------------------------------------

def leave_request_check(request, data=None, lookup=lookup_employee_leave_balance):
    """Completeness and an FMLA pre-check. Never a decision: HR decides."""
    data = data or load_data()
    types = data["leave_policy"]["leave_types"]
    missing = []
    for field, label in (("leave_type", "leave type"), ("start_date", "start date"), ("end_date", "end date")):
        if not request.get(field):
            missing.append(f"Add the {label}")
    leave_type = request.get("leave_type")
    if leave_type and leave_type not in types:
        missing.append("Choose a valid leave type")
        leave_type = None
    if request.get("start_date") and request.get("end_date") and request["end_date"] < request["start_date"]:
        missing.append("The end date is before the start date")

    required_docs = types[leave_type]["required_documents"] if leave_type else []
    attached = set(request.get("documents_attached", []))
    missing_docs = [doc for doc in required_docs if doc not in attached]

    lookup_result = lookup(request.get("employee_id"))
    if lookup_result["status"] != "ok":
        fmla = {"status": "cannot_determine", "reason": lookup_result["reason"],
                "detail": "Eligibility facts could not be retrieved. HR must check the HR system."}
    else:
        facts = lookup_result["facts"]
        months = facts["months_of_service"]["value"]
        hours = facts["hours_worked_12mo"]["value"]
        meets = months >= 12 and hours >= 1250
        fmla = {
            "status": "meets_basics" if meets else "does_not_meet_basics",
            "months_of_service": months, "hours_worked_12mo": hours, "as_of": lookup_result["as_of"],
            "detail": (f"{months} months of service and {hours} hours in the last 12 months. "
                       + ("Meets the FMLA service and hours basics." if meets else
                          "Does not meet the FMLA basics; HR should check state leave and company policy.")),
        }

    return {
        "employee_id": request.get("employee_id"),
        "leave_type_label": types[leave_type]["label"] if leave_type else None,
        "missing_fields": missing,
        "missing_documents": missing_docs,
        "complete": not missing and not missing_docs,
        "fmla_precheck": fmla,
    }
