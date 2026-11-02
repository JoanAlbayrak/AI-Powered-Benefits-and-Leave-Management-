"""Demo web page for the Benefits & Leave agents. Runs only on your laptop.

    .venv/bin/python -m benefits_leave.web

Opens http://127.0.0.1:8001 with two sides: Employee and HR. Press Ctrl + C to stop.
"""

import json
import mimetypes
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from benefits_leave.workflow import LEAVE_SCHEDULES, CaseStore, WorkflowError
from benefits_leave import checks, runner
from benefits_leave.hr_lookup import load_fake_hr_data, lookup_employee_leave_balance

PAGE = (Path(__file__).resolve().parent / "web_page.html").read_bytes()
FRONTEND = Path(__file__).resolve().parent / "frontend"


def frontend_asset(request_path):
    """Serve only frontend files; never expose repository or employee data files."""
    path = unquote(urlsplit(request_path).path)
    if path in ("/", "/index.html"):
        path = "/assets/index.html"
    if not path.startswith("/assets/"):
        return None
    relative = path.removeprefix("/assets/")
    candidate = (FRONTEND / relative).resolve()
    if not candidate.is_relative_to(FRONTEND.resolve()) or not candidate.is_file():
        return None
    if candidate.suffix not in (".html", ".css", ".js", ".svg", ".png", ".ico"):
        return None
    content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
    if candidate.suffix == ".js":
        content_type = "text/javascript"
    if candidate.suffix in (".html", ".css", ".js", ".svg"):
        content_type += "; charset=utf-8"
    return content_type, candidate.read_bytes()


def people(store):
    new_hires = [{"id": eid, "name": h["name"], "kind": "new hire"} for eid, h in store.data["new_hires"].items()]
    current = [{"id": eid, "name": e["name"], "kind": "current employee"}
               for eid, e in load_fake_hr_data()["employees"].items()]
    return new_hires + current


def employee_view(case):
    """What an employee may see about their own case: no HR notes or internal flags."""
    view = {"id": case["id"], "kind": case["kind"], "status": case["status"],
            "employee_update": case["employee_update"],
            "activity": [{k: v for k, v in a.items() if k != "visibility"}
                         for a in case.get("activity", []) if a["visibility"] == "employee"]}
    if case["kind"] == "leave":
        check = case["check"]
        view["leave_type"] = check["leave_type_label"]
        view["dates"] = [case["request"].get("start_date"), case["request"].get("end_date")]
        view["schedule"] = case["request"].get("schedule")
        view["missing"] = check["missing_fields"] + [f"Upload: {d}" for d in check["missing_documents"]]
        view["guidance"] = (case.get("ai") or {}).get("employee_message")
        view["ai_error"] = case.get("ai_error")
    else:
        view["guidance"] = (case.get("ai") or {}).get("employee_message")
        view["ai_error"] = case.get("ai_error")
    return view


def draft_view(draft):
    """The employee's own draft. It never carries the FMLA pre-check."""
    return {k: draft.get(k) for k in ("id", "status", "request", "leave_type_label", "missing_fields",
                                      "missing_documents", "ready_to_confirm", "clarifications", "case_id")}


def _employee_turn(turn):
    return {k: v for k, v in turn.items() if k != "dropped_refs"}


def employee_selections(store, employee_id):
    """Each benefit's current election, for display or as the starting point for an edit.

    Shared by the read-only overview and every mutating election endpoint, so there's one
    place that defines what a 'selection' looks like.
    """
    hire = store.data["new_hires"].get(employee_id)
    if hire is None:
        return []
    selections = []
    for benefit in (*store.data["rules"]["benefit_types"], "retirement"):
        election = hire["elections"].get(benefit, {"status": "not_started"})
        selection = {"benefit": benefit, "status": election["status"]}
        if benefit == "retirement":
            selection["percent"] = election.get("percent")
        else:
            selection.update(plan=election.get("plan"), tier=election.get("tier"))
            selection["cost_per_paycheck"] = store.data["plans"][benefit].get(election.get("plan"), {}).get(election.get("tier"))
        selections.append(selection)
    return selections


def employee_dependents(store, employee_id):
    """Each dependent with its document state, regardless of which tier is currently elected.

    `checks.evidence_status` is tier-gated (only reports what the *current* election needs);
    this is the raw view, so the UI can show upload state for a dependent added before a
    dependent-covering tier is chosen.
    """
    hire = store.data["new_hires"].get(employee_id)
    if hire is None:
        return []
    records = checks.evidence_for(employee_id, store.data)
    out = []
    for dependent in hire["dependents"]:
        requirement = store.data["rules"]["dependent_proof"][dependent["relationship"]]
        match = next((r for r in records if r["requirement"] == requirement and r["dependent"] == dependent["name"]), None)
        out.append({**dependent, "requirement": requirement, "document_state": (match or {}).get("state", "absent")})
    return out


def employee_leave_balance(store, employee_id):
    """Categorized leave balances (pto/sick/personal), or a graceful 'cannot determine'.

    Never fabricates a number -- mirrors the FMLA pre-check's own honesty rule.
    """
    lookup = store.lookup or lookup_employee_leave_balance
    result = lookup(employee_id)
    if result["status"] != "ok":
        return {"status": "cannot_determine", "reason": result.get("reason")}
    return {"status": "ok", "balances": result["facts"]["leave_balances"]["value"], "as_of": result["as_of"]}


def employee_overview(store, employee_id):
    """Read-only UI model: existing checks, no agent calls or case creation.

    The demo selects identity in the browser. This projection removes HR-only
    fields; it is not a replacement for production authentication.
    """
    person = next((p for p in people(store) if p["id"] == employee_id), None)
    if person is None:
        raise WorkflowError("Employee not found")
    enrollment = None
    is_new_hire = person["kind"] == "new hire"
    if is_new_hire:
        result = checks.enrollment_status(employee_id, store.data)
        # Keep eligibility flags and internal completion classifications HR-only.
        enrollment = {k: result[k] for k in ("name", "deadline", "days_left", "done", "missing", "notes", "as_of")}
    hire = store.data["new_hires"].get(employee_id)
    return {"employee": person, "enrollment": enrollment,
            "selections": employee_selections(store, employee_id),
            "dependents": employee_dependents(store, employee_id),
            "enrollment_locked": store.enrollment_locked(employee_id) if is_new_hire else None,
            "cost_summary": store.enrollment_cost_summary(employee_id) if is_new_hire else None,
            "plan_options": checks.plan_options(store.data) if is_new_hire else None,
            "consider_results": store.consider_results.get(employee_id, {}),
            "evidence": checks.evidence_status(employee_id, store.data) if enrollment else [],
            "help_thread": [_employee_turn(t) for t in store.help_threads.get(employee_id, [])],
            "leave_drafts": [draft_view(d) for d in store.drafts.values() if d["employee_id"] == employee_id],
            "leave_schedules": [{"id": k, "label": v} for k, v in LEAVE_SCHEDULES.items()],
            "cases": [employee_view(c) for c in store.employee_cases(employee_id)],
            "leave_balance": employee_leave_balance(store, employee_id) if not is_new_hire else None,
            "intake_result": store.intake_results.get(employee_id),
            "as_of": store.data["as_of"],
            "retirement_match": store.data["retirement_plan"]["match_rule"],
            "leave_types": [{"id": key, "label": value["label"], "required_documents": value["required_documents"]}
                            for key, value in store.data["leave_policy"]["leave_types"].items()]}


def handle(store, path, body):
    eid = body.get("employee_id", "")
    if path == "/api/people":
        return {"people": people(store)}
    if path == "/api/ai/status":
        return runner.readiness()     # local configuration only: no model call, never the key
    if path == "/api/employee/overview":
        return employee_overview(store, eid)
    if path == "/api/employee/enrollment":
        result, case = store.check_enrollment(eid)
        s = result["status"]
        return {"case": employee_view(case),
                "enrollment": {k: s[k] for k in ("name", "deadline", "days_left", "enrollment_state",
                                                 "done", "missing", "notes")},
                "message": (result["ai"] or {}).get("employee_message"), "ai_error": result["ai_error"]}
    if path == "/api/employee/enrollment/help":
        turn = store.enrollment_help(eid, body.get("question", ""))
        return {"turn": _employee_turn(turn),
                "thread": [_employee_turn(t) for t in store.help_threads.get(eid, [])]}
    if path == "/api/employee/enrollment/elect":
        election_fields = {k: body.get(k) for k in ("status", "plan", "tier", "percent")}
        status = store.set_election(eid, body.get("benefit", ""), election_fields)
        return {"enrollment": {k: status[k] for k in ("done", "missing", "hr_flags", "notes")},
                "selections": employee_selections(store, eid), "cost_summary": store.enrollment_cost_summary(eid)}
    if path == "/api/employee/enrollment/consider":
        election_fields = {k: body.get(k) for k in ("status", "plan", "tier", "percent")}
        return store.consider_election(eid, body.get("benefit", ""), election_fields)
    if path == "/api/employee/enrollment/dependent/add":
        store.add_dependent(eid, body.get("relationship", ""), body.get("name", ""))
        return {"dependents": employee_dependents(store, eid), "selections": employee_selections(store, eid)}
    if path == "/api/employee/enrollment/dependent/upload":
        store.mark_document_uploaded(eid, body.get("relationship", ""), body.get("name", ""))
        return {"dependents": employee_dependents(store, eid), "selections": employee_selections(store, eid)}
    if path == "/api/employee/leave/intake":
        return store.intake_leave(eid, body.get("description", ""))
    if path == "/api/employee/leave":
        request = {k: body.get(k) for k in ("employee_id", "leave_type", "start_date", "end_date", "reason")}
        request["documents_attached"] = body.get("documents_attached") or []
        result, case = store.submit_leave(request)
        check = result["check"]
        return {"case": employee_view(case),
                "missing": check["missing_fields"] + [f"Upload: {d}" for d in check["missing_documents"]],
                "message": (result["ai"] or {}).get("employee_message"), "ai_error": result["ai_error"]}
    if path == "/api/employee/leave/draft":
        fields = {k: body.get(k) for k in ("leave_type", "start_date", "end_date", "schedule", "reason",
                                           "documents_attached")}
        draft = store.save_leave_draft(eid, fields)
        return {"draft": draft_view(draft)}
    if path == "/api/employee/leave/confirm":
        _, case, draft = store.confirm_leave_draft(eid, body.get("draft_id"), body.get("confirmed"))
        return {"case": employee_view(case), "draft": draft_view(draft)}
    if path == "/api/employee/cases":
        return {"cases": [employee_view(c) for c in store.employee_cases(eid)]}
    if path == "/api/hr/queue":
        return {"cases": store.hr_queue()}
    if path == "/api/hr/decide":
        return {"case": store.hr_decide(body.get("case_id"), body.get("decision"), body.get("reason", ""))}
    if path == "/api/hr/vendor/prepare":
        return {"case": store.prepare_vendor_records(body.get("case_id"))}
    if path == "/api/hr/vendor/sent":
        return {"case": store.mark_sent(body.get("case_id"))}
    if path == "/api/hr/vendor/check":
        return {"case": store.check_vendor_confirmations(body.get("case_id"))}
    raise WorkflowError("Unknown action")


def make_handler(store):
    lock = threading.Lock()  # one action at a time on the shared case store

    class Handler(BaseHTTPRequestHandler):
        def _send(self, status, content_type, data):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if urlsplit(self.path).path == "/legacy":
                self._send(200, "text/html; charset=utf-8", PAGE)
            else:
                asset = frontend_asset(self.path)
                if asset is None:
                    self._send(404, "text/plain; charset=utf-8", b"Not found")
                else:
                    self._send(200, *asset)

        def do_POST(self):
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length) or b"{}")
                with lock:
                    out = handle(store, self.path, body)
            except WorkflowError as exc:
                out = {"error": str(exc)}
            except (ValueError, json.JSONDecodeError):
                out = {"error": "Bad request."}
            self._send(200, "application/json", json.dumps(out).encode())

        def log_message(self, *args):
            pass

    return Handler


def main(port=8001):
    store = CaseStore()
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(store))
    url = f"http://127.0.0.1:{port}"
    print(f"Benefits & Leave agents running at {url}")
    ai = runner.readiness()
    print(f"AI: {'configured' if ai['ready'] else 'not ready'} ({ai['model']})"
          + "".join(f"\n  ! {p}" for p in ai["problems"]))
    print("Press Ctrl + C to stop.")
    threading.Timer(1.0, webbrowser.open, args=[url]).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 8001)
