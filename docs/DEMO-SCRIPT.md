# Live demo script and rehearsal checklist (T09)

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
| 1:00–2:00 | Employee **E2001 → My benefits**. Point at *Your documents* (marriage certificate: received, awaiting HR check). Click the suggestion "I already uploaded my document…" and **Ask the Enrollment Agent**. | The agent looked up the document record and the dependent-proof policy before answering. It cites `EV-E2001-01` and `DEMO-ENR-DEPENDENT-PROOF@v1`. Received ≠ verified, so the item stays open. Nothing about the case changed. |
| 2:00–2:30 | Optional contrast: **E2005** asks the same thing (no record → one targeted question); **E2006** (verified). | Same question, three grounded answers. |
| 2:30–4:00 | **HR preview → C1 (E2004) → Check confirmations.** Scroll to *Specialist consultation*, *Follow-up drafts*, *Agent activity*. | Carrier says family; HR approved employee-only. The Vendor Agent asked the Enrollment Agent, through workflow code, what HR approved. The specialist read only the frozen snapshot `C1:approved:1`, the dependent records and policy: no dependents or proof on record, $230 vs $78. The draft to Acme Health cites that evidence. One consultation per run, no callbacks, HR sends. |
| 4:00–5:00 | Employee **E1001 → Leave requests.** Choose own health + start date only → **Check draft**. Then add end date and schedule → **Check draft** → tick confirm → **Submit to HR**. | Draft is not a case. The Leave Agent asks one question and never promises eligibility. Only the employee's confirmation creates the HR case. |
| 5:00–5:45 | **HR preview →** the new leave case. Show the FMLA pre-check (HR only), request details, activity. **Request information** with a reason. Switch back to E1001 to see the update. | Pre-check is not a decision; unknown facts stay "cannot determine"; failing FMLA basics doesn't deny state or company leave. |
| 5:45–6:30 | Architecture | Three scoped agents; code owns checks, state, routing and budgets; the consultation contract; employee/HR projections. |
| 6:30–7:00 | Limits and next | Fictional data, in-memory cases, demo identities, no real uploads or carrier connections. Next: persistence, real auth, document verification flow, more consultation types. |

Backup: the E2002 path (check → approve → prepare → simulated sending → check confirmations) still works, and `/legacy` keeps the original workflow page.

## If live AI fails on stage

The checks, cases, HR decisions, record facts and rule-based vendor templates still work, and the UI labels the AI as unavailable. Say so plainly. Do not present the fallback text as live agent output, and do not claim the consultation ran. A consultation that fails shows as **Unavailable** with the reason.

## Rehearsal log (fill in; never record the key)

| Run | Date/time | Model / effort | Readiness --live | Enrollment Q&A | C1 consultation answered | Leave draft → HR | Slowest step (s) | Notes |
|---|---|---|---|---|---|---|---|---|
| 1 | | | | | | | | |
| 2 | | | | | | | | |

T09 is complete when two clean-start runs succeed with the real key, or the exact failing requirement is recorded above.
