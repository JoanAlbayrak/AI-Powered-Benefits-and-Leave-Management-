# AI-Powered Benefits and Leave Management

An AI-powered Benefits and Leave Management system with three agents. Employees log in to do their own benefits enrollment and leave requests, instead of sending paper or emailed forms. The agents check what's missing and explain it. **HR reviews every case and makes every decision.**

> **Status:** both workflows run end to end on a demo web page, and all tests pass (`python3 -m unittest`).

## Team

- Joan Albayrak
- Dikshyant Giri ([@Diksh-giri](https://github.com/Diksh-giri))

## The three agents

| Agent | What it does | What it never does |
|---|---|---|
| Enrollment Agent | Walks a new hire through medical, dental, vision and retirement elections: what's done, what's missing, the deadline, how the 401(k) match works. Writes a summary for HR. | Choose plans for the employee or decide eligibility |
| Vendor Agent | After HR approves an enrollment, it checks the approved records against each vendor's confirmation, flags mismatches, and drafts follow-up messages. | Send anything to a vendor (HR sends) |
| Leave Agent | Checks a leave request for missing fields and documents, runs an FMLA pre-check, and writes a summary for HR. | Approve or deny leave |

**Workflow A (benefits):** the employee checks their enrollment → the Enrollment Agent lists what's missing → HR reviews and approves → HR prepares vendor records → HR marks them sent → the Vendor Agent checks confirmations and drafts follow-ups.

**Workflow B (leave):** the employee submits a request → the Leave Agent checks completeness → HR reviews eligibility → HR approves, denies or requests info → the employee sees the update.

## Getting started

1. Clone the repo. In GitHub Desktop: **File → Clone repository → AI-Powered-Benefits-and-Leave-Management-**.
2. In Terminal, go to the folder and install the one library:
   ```bash
   cd ~/Documents/GitHub/AI-Powered-Benefits-and-Leave-Management-
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```
3. Make your own secrets file, then open `.env` and paste **your own** API key:
   ```bash
   cp .env.example .env
   ```
   `.env` is in `.gitignore`, so it is never committed. Each teammate keeps their own key. Never share keys in git, chat, Slack or screenshots.

## Running the demo page

```bash
.venv/bin/python -m benefits_leave.web
```
Your browser opens `http://127.0.0.1:8001` with an **Employee side** and an **HR side**. The page runs only on your own computer. Press **Ctrl + C** in Terminal to stop.

**Demo people (all made up):**
- New hires: E2001 (incomplete), E2002 (complete), E2003 (part-time, needs an HR exception), E2004 (already sent to vendors, with a vendor mismatch).
- Current employees: E1001–E1005, for leave requests.

## Public demo website

Anyone can try the demo here, with no install and no login: **https://joanalbayrak.github.io/AI-Powered-Benefits-and-Leave-Management-/**

- It's the same page and the same checks and HR workflow, running in the browser (`site/demo.js` mirrors the Python code).
- **No API key is used.** The AI agents' messages are examples written from the check results. The live AI version is the laptop version above.
- Nothing is saved: reloading the page starts the demo over.
- GitHub Pages serves the `docs/` folder. After changing `benefits_leave/web_page.html` or `site/demo.js`, rebuild it and commit `docs/index.html`:
  ```bash
  python3 scripts/build_site.py
  ```
  A test checks that the website gives the same results as the Python code, and that `docs/index.html` is up to date.

## Running the tests

No API key needed. The tests use a pretend Claude:
```bash
python3 -m unittest
```

## How it stays safe

- Code does the checks (`benefits_leave/checks.py`) and runs the workflow (`benefits_leave/workflow.py`). The agents only explain the results.
- Agents have read-only tools. No tool can send, approve or change anything.
- If the AI can't run (no key, no internet), the code results still show.
- A failed HR lookup becomes "cannot determine," never zero or "not eligible."
- Text an employee writes is treated as unverified information, not instructions.
- Employees only see their own cases, without HR notes.

## Handoffs and shared state

- **Shared state** is the case store (`CaseStore` in `workflow.py`). Each enrollment or leave request is one case, with a status, the agent's output, HR's decision and a history of every step. Only code changes a case's status; agents never write to it.
- **Enrollment → HR → Vendor Agent:** when HR approves, code freezes exactly what was approved into a handoff packet (`build_vendor_handoff` in `checks.py`): vendor records, HR's note and the Enrollment Agent's summary. The Vendor Agent reads only that packet. `validate_vendor_handoff` stops the Vendor Agent if the packet is incomplete or mixes employees.
- **Leave Agent → HR:** the Leave Agent writes an HR summary into the case. HR approves, denies or requests info, and the employee sees the update.

## Project layout

```
benefits_leave/
  agents.py       the three agents (prompts, tools, structured answers)
  runner.py       the shared tool-use loop (max 6 turns per agent)
  checks.py       deterministic checks and the vendor handoff
  workflow.py     the two workflows, the HR queue and the case store
  hr_lookup.py    read-only HR lookup for the FMLA pre-check
  web.py          the demo web server (local only)
  web_page.html   the Employee and HR page
data/             made-up employees, plans, vendors and leave policy
tests/            automated tests
```

## Out of scope

- Approving or denying leave, choosing benefit plans, or deciding eligibility (HR and the employee do these).
- Sending anything to employees or vendors (agents only draft; HR sends).
- Connecting to a real HRIS, payroll or carrier system. All data is made up, in `data/`.
- Real logins (the demo lets you pick a person). Never commit real employee data.
