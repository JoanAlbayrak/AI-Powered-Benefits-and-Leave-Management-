# Live demo script and rehearsal checklist (T09)

**2 November handoff note:** the rehearsal records below predate the latest interactive extension. Follow [Joan handoff](JOAN-HANDOFF.md) for its blockers and repeat the expanded journey after fixes. Earlier live success does not verify the new election-editing or conditional-approval paths.

About seven minutes. All people and records are fictional. Never show the `.env` file or the key.

## Before the presentation

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp -n .env.example .env            # then put your Anthropic key in .env
.venv/bin/python -m benefits_leave.readiness --live
.venv/bin/python -m unittest
node --test tests/frontend.test.mjs
.venv/bin/python -m benefits_leave.web
```

The readiness check prints the model, effort, timeout and retries, and makes **one** small structured call. It never prints the key. If it fails, it names the problem (key, model availability, connection). Optional `.env` settings: `ANTHROPIC_MODEL` (default `claude-opus-5-5`), `ANTHROPIC_EFFORT` (`low`/`medium`/`high`/`none`, default `medium`), `ANTHROPIC_TIMEOUT_SECONDS` (60), `ANTHROPIC_MAX_RETRIES` (2). If answers feel slow on stage, try `ANTHROPIC_EFFORT=low` and rerun the readiness check.

The badge at the top of the app reads **AI unavailable**, **AI configured · not run yet**, **Live AI · model** (after a successful call) or **last call failed**. Restart the server before each rehearsal: cases live in memory.

## Route

| Time | Show | Say |
|---|---|---|
| 0:00–1:00 | Problem | Paper/email benefits and leave forms cause missing items, repeated follow-up and carrier mistakes. Computer checks, AI explains, people decide. |
| 1:00–2:00 | Employee **E2001 · Priya Nair → My benefits**. Point at *Your documents* (marriage certificate: received, awaiting HR check). Click the suggestion "I already uploaded my document…" and **Ask the Enrollment Agent**. | The agent looked up the document record and the dependent-proof policy before answering. It cites `EV-E2001-01` and `DEMO-ENR-DEPENDENT-PROOF@v1`. Received ≠ verified, so the item stays open. Nothing about the case changed. |
| 2:00–2:30 | Optional contrast: **E2005 · Hana Petrov** asks the same thing (no record → one targeted question); **E2006 · Omar Haddad** (verified). | Same question, three grounded answers. |
| 2:30–4:00 | **HR preview → C1 (E2004 · Daniel Okafor) → Check confirmations.** Scroll to *Specialist consultation*, *Follow-up drafts*, *Agent activity*. | Carrier says family; HR approved employee-only. The Vendor Agent asked the Enrollment Agent, through workflow code, what HR approved. The specialist read only the frozen snapshot `C1:approved:1`, the dependent records and policy: no dependents or proof on record, $230 vs $78. The draft to Acme Health cites that evidence. One consultation per run, no callbacks, HR sends. |
| 4:00–5:00 | Employee **E1001 · Elena Rossi → Leave requests.** Choose own health + start date only → **Check draft**. Then add end date and schedule → **Check draft** → tick confirm → **Submit to HR**. | Draft is not a case. The Leave Agent asks one question and never promises eligibility. Only the employee's confirmation creates the HR case. |
| 5:00–5:45 | **HR preview →** the new leave case. Show the FMLA pre-check (HR only), request details, activity. **Request information** with a reason. Switch back to E1001 to see the update. | Pre-check is not a decision; unknown facts stay "cannot determine"; failing FMLA basics doesn't deny state or company leave. |
| 5:45–6:30 | Architecture | Three scoped agents; code owns checks, state, routing and budgets; the consultation contract; employee/HR projections. |
| 6:30–7:00 | Limits and next | Fictional data, in-memory cases, demo identities, no real uploads or carrier connections. Next: persistence, real auth, reviewer identity and history on verification, more consultation types. |

**Optional documents and corrections segment (about 1 minute, offline-verified; rehearse live before presenting it):** Employee **E2001 → My benefits**: the marriage certificate is *received*, not verified, so the item stays open. **HR preview → E2001's case → Dependent documents → Mark verified** (HR, not the employee, verifies; the page records who and when). For leave: in HR choose **Approve, pending a document** with a reason; the employee marks the document as provided (it becomes *received*, not verified); HR then verifies and completes the approval, asks again, or withdraws it. After **Request information**, the employee corrects the **same** request and it returns to HR. If HR opens a case and the employee changes it first, HR's approval is refused and the page reloads the latest version.

Backup: the E2002 · Marcus Alvarez path (check → approve → prepare → simulated sending → check confirmations) still works, and `/legacy` keeps the original workflow page.

## If live AI fails on stage

The checks, cases, HR decisions, record facts and rule-based vendor templates still work, and the UI labels the AI as unavailable. Say so plainly. Do not present the fallback text as live agent output, and do not claim the consultation ran. A consultation that fails shows as **Unavailable** with the reason.

## Rehearsal log (fill in; never record the key)

| Run | Date/time | Model / effort | Readiness --live | Enrollment Q&A | C1 consultation answered | Leave draft → HR | Slowest step (s) | Notes |
|---|---|---|---|---|---|---|---|---|
| 1 | 2026-11-01 ~22:40 | claude-opus-5-5 / medium | Passed (2.9s) | Passed (E2004 · Daniel Okafor) | Passed, 2 model calls, Acme Health flagged | Passed (E1001 · Elena Rossi, 2 clarifications → HR approved) | ~10s (consultation) | Clean start on a fresh server process; full route walked end to end, no errors. |
| 2 | 2026-11-01 ~22:55 | claude-opus-5-5 / medium | Passed (2.1s) | Passed (E2002 · Marcus Alvarez enrollment check, case created) | Not exercised this run | Not exercised this run | ~8s (enrollment check) | Second independent clean-start process (new port, empty case store) to confirm reproducibility. |
| 3 | 2026-11-01 ~23:20 | claude-opus-5-5 / medium | n/a (server already restarted post-rename) | Passed (E2001 · Priya Nair; agent addressed her by first name) | Passed (E2004 · Daniel Okafor, 2 model calls, Acme Health flagged, draft cites CONSULT-C1-1) | Passed (E1001 · Elena Rossi, 2 clarifications → confirmed → HR approved) | ~10s (consultation) | **Full run-of-show, fresh server on port 8001 (default demo port), after the realistic-name update.** No console errors. This is the presentation-ready state. |
| 4 | 2026-11-02 | Scripted pretend model (**not live**) | n/a | Scripted answers | Scripted specialist | Scripted | n/a | **Browser rehearsal of the interactive extension, 37/37 checks, no console errors**, including a model that always fails. This proves the page, endpoints and workflow fit together; it does **not** show live-model behavior. The new paths still need a live rehearsal with a working key. |

T09 is complete: three clean-start runs succeeded with the real key (above), the last one the exact route to present tomorrow with the current (realistic-name) data. Restart the server one more time just before presenting to reset the case store to empty.
