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

from benefits_leave.workflow import CaseStore, WorkflowError
from benefits_leave import checks
from benefits_leave.hr_lookup import load_fake_hr_data

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
            "employee_update": case["employee_update"]}
    if case["kind"] == "leave":
        view["leave_type"] = case["check"]["leave_type_label"]
        view["dates"] = [case["request"].get("start_date"), case["request"].get("end_date")]
    return view


def employee_overview(store, employee_id):
    """Read-only UI model: existing checks, no agent calls or case creation.

    The demo selects identity in the browser. This projection removes HR-only
    fields; it is not a replacement for production authentication.
    """
    person = next((p for p in people(store) if p["id"] == employee_id), None)
    if person is None:
        raise WorkflowError("Employee not found")
    enrollment = None
    selections = []
    if person["kind"] == "new hire":
        result = checks.enrollment_status(employee_id, store.data)
        # Keep eligibility flags and internal completion classifications HR-only.
        enrollment = {k: result[k] for k in ("name", "deadline", "days_left", "done", "missing", "notes", "as_of")}
        hire = store.data["new_hires"][employee_id]
        for benefit in (*store.data["rules"]["benefit_types"], "retirement"):
            election = hire["elections"].get(benefit, {"status": "not_started"})
            selection = {"benefit": benefit, "status": election["status"]}
            if benefit == "retirement":
                selection["percent"] = election.get("percent")
            else:
                selection.update(plan=election.get("plan"), tier=election.get("tier"))
                selection["cost_per_paycheck"] = store.data["plans"][benefit].get(election.get("plan"), {}).get(election.get("tier"))
            selections.append(selection)
    return {"employee": person, "enrollment": enrollment, "selections": selections,
            "cases": [employee_view(c) for c in store.employee_cases(employee_id)],
            "as_of": store.data["as_of"],
            "retirement_match": store.data["retirement_plan"]["match_rule"],
            "leave_types": [{"id": key, "label": value["label"], "required_documents": value["required_documents"]}
                            for key, value in store.data["leave_policy"]["leave_types"].items()]}


def handle(store, path, body):
    eid = body.get("employee_id", "")
    if path == "/api/people":
        return {"people": people(store)}
    if path == "/api/employee/overview":
        return employee_overview(store, eid)
    if path == "/api/employee/enrollment":
        result, case = store.check_enrollment(eid)
        s = result["status"]
        return {"case": employee_view(case),
                "enrollment": {k: s[k] for k in ("name", "deadline", "days_left", "enrollment_state",
                                                 "done", "missing", "notes")},
                "message": (result["ai"] or {}).get("employee_message"), "ai_error": result["ai_error"]}
    if path == "/api/employee/leave":
        request = {k: body.get(k) for k in ("employee_id", "leave_type", "start_date", "end_date", "reason")}
        request["documents_attached"] = body.get("documents_attached") or []
        result, case = store.submit_leave(request)
        check = result["check"]
        return {"case": employee_view(case),
                "missing": check["missing_fields"] + [f"Upload: {d}" for d in check["missing_documents"]],
                "message": (result["ai"] or {}).get("employee_message"), "ai_error": result["ai_error"]}
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
    print("Press Ctrl + C to stop.")
    threading.Timer(1.0, webbrowser.open, args=[url]).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 8001)
