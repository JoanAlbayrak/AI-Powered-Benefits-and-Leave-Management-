# Functional test guide

Run through the whole application yourself and check what it does. All people, plans, carriers and dates are **fictional**. Nothing is sent anywhere: carrier steps are simulated, document "uploads" are labels only, and the app runs only on your own computer.

The numbers in this guide were checked against the code. The `tests/test_demo_scenarios.py` tests fail if a person stops behaving as described here.

## 1. Start, reset and edit

```sh
cd ~/Documents/GitHub/AI-Powered-Benefits-and-Leave-Management-
.venv/bin/python -m benefits_leave.web
```

Open **http://127.0.0.1:8001**. Press **control + C** in Terminal to stop.

- **Reset demo data** (button at the top of every page): forgets every case, draft, edit and chat, and **re-reads the data files**. Use it before each test so you start clean. Cases also reset when the server restarts.
- **Edit the data, then reset.** Change `data/benefits_demo.json` (new hires, plans, carriers, policy text) or `data/fake_employees.json` (current employees and leave balances), save, and press **Reset demo data**. No restart needed. A typo in the JSON shows as an error; fix it and reset again.
- **The demo clock** is `as_of` in `data/benefits_demo.json` (currently **2026-10-26**). Deadlines and "days left" count from it. Change it to see deadlines pass.
- **Add new people instead of changing the originals.** E2001–E2006 and E1001–E1005 back the automated tests and earlier rehearsals. New IDs are safe. After editing, run `python3 -m unittest` to see whether a change broke an expectation.
- **AI badge** (top bar): *AI unavailable* means no working key or AI is turned off; the checks, cases and HR actions still work and say so. *AI configured* means a key is set; *Live AI* appears after a successful call. AI wording differs between runs; the checklists and statuses do not.

## 2. The people

### New hires (benefits enrollment). Pick them in **Employee preview → Demo profile**

The demo clock is 2026-10-26. The enrollment window is 30 days from the start date.

| ID | Person | Scenario | What you should see |
|---|---|---|---|
| E2001 | Priya Nair | Spouse coverage; marriage certificate **received**, not verified; dental and retirement not chosen | 3 items to do; 23 days left; certificate shown as *received, awaiting HR* (not verified) |
| E2002 | Marcus Alvarez | Complete and ready; **4 days left** | Goes straight to HR review; backup demo path |
| E2003 | Sofia Lindqvist | 20 hours a week (under the 30-hour rule); complete otherwise | Employee sees a normal checklist; **HR** sees an eligibility flag and must give a reason to approve |
| E2004 | Daniel Okafor | **Already approved and sent** (case C1); carrier shows the wrong tier and one pending | HR: Check confirmations → discrepancy, pending, 2 confirmed; specialist consultation; drafts |
| E2005 | Hana Petrov | Child covered; **no birth certificate on record** | 1 item to do; "Not on record" |
| E2006 | Omar Haddad | Family; proofs **verified**; retirement not chosen; carrier asks for a document | 1 item to do (retirement) |
| **E2007** | **Aisha Rahman** | **Complete, 4 elections, every carrier confirms** | The happy path from check to "confirmed by every vendor" |
| **E2008** | **Tomás Ferreira** | **Family**: spouse verified, child 1 received, child 2 absent; retirement 3% | 2 items to do; three document states; $371.00 you pay vs $873.00 company per paycheck; 401(k) below-match note |
| **E2009** | **Chloe Washington** | **24 hours a week**; waives dental and vision; 0% retirement | HR flag (24 hours under 30); approval needs a reason |
| **E2010** | **Jamal Whitfield** | **Missed the window** (deadline 2026-10-22, 4 days ago); dental and retirement open | HR flag "Enrollment deadline passed"; 2 items to do; cannot be approved until finished |
| **E2011** | **Elif Demir** | **Starts today**, nothing chosen | 4 items to do; 30 days left; cost $0.00 until they elect |
| **E2012** | **Rosa Delgado** | **Complete**; spouse covered and verified; after approval the carriers disagree | HR check: medical confirmed, dental **no confirmation**, vision **discrepancy** (tier), retirement **discrepancy** (5% vs 4%); 3 follow-up drafts |

### Current employees (leave of absence)

| ID | Person | Service / hours | Balances (PTO / sick / personal) | What you should see |
|---|---|---|---|---|
| E1001 | Elena Rossi | 38 months / 1,850 | 96 / 40 / 16 | Meets the FMLA basics |
| E1002 | Liam Park | 14 months / 1,310 | **0 / 0 / 0** | Meets the basics; balances are a **real zero** |
| E1003 | Nadia Castillo | 7 months / 900 | 24 / 16 / 8 | **Does not meet** the basics (HR-only note) |
| E1004 | Victor Dlamini | bad record | sick hours are text ("forty") | **Cannot determine**, never "not eligible" |
| E1005 | Freya Bergman | no balance record | none | **Cannot determine** |
| **E1006** | **Hannah Okoye** | 62 months / 2,010 | 120 / 56 / 24 | Clearly meets the basics |
| **E1007** | **Mateo Silva** | **11 months** / **1,180** | 40 / 24 / 8 | Does not meet either test; note says HR also checks state leave and company policy |
| **E1008** | **Grace Nakamura** | 30 months / **1,240** | 72 / 32 / 16 | Misses only the hours test, by 10 hours |
| **E1009** | **Ibrahim Yusuf** | 45 months / 1,700 | **0 / 80 / 12** | PTO is a real zero; sick has 80 hours |

## 3. Test script

Tick **Pass** or **Fail** for each. Press **Reset demo data** before each test unless it says otherwise. "Employee" means *Employee preview*; "HR" means *HR preview*.

### Enrollment

**T1. Happy path to confirmed coverage (E2007).**
1. Employee → My benefits → pick **E2007**. You see four elections and *18 days remaining*.
2. Click **Check enrollment and create case**. A case appears with status *Ready for HR review*.
3. HR → Review queue → open the case. Decision → **Approve** → **Record HR decision**. Status becomes *Approved*; a **Frozen approved handoff** table lists 4 records.
4. Click **Prepare vendor records**, then tick the confirmation box and **Record simulated sending**, then **Check confirmations**.
5. **Expect:** every result *Confirmed*; status *Confirmed by vendors*. Employee → My requests shows "complete and confirmed by every vendor".
- [ ] Pass [ ] Fail

**T2. Incomplete enrollment cannot be approved; received is not verified (E2008).**
1. Employee → E2008. Under *Your dependents*: Camila **Verified by HR**, Mateo **Received, awaiting HR check**, Lucia **Not on file**. *Still to do* lists Mateo's and Lucia's birth certificates.
2. **Check enrollment and create case**. HR → open the case: the **Approve** option is **disabled**.
3. HR → **Dependent documents → Mark verified** on Mateo's certificate. The list drops to Lucia only. Approval is still blocked.
4. Employee → click **Mark as uploaded** on Lucia. It becomes *Received* (not verified; still on the list). HR → **Mark verified**.
5. **Expect:** *Still to do* is empty; the case is *Ready for HR review*; Approve is enabled.
- [ ] Pass [ ] Fail

**T3. An eligibility flag needs a reason (E2009).**
1. Employee → E2009 → check. The employee page shows an ordinary checklist and **no mention of hours or eligibility rules**.
2. HR → open the case. **Trusted check results → HR-only review flags** says 24 hours is under the 30-hour rule.
3. Choose **Approve** and leave the reason empty → the page asks for a reason. Add one and approve.
- [ ] Pass [ ] Fail

**T4. Missed enrollment window, then information request and correction (E2010).**
1. Employee → E2010: the deadline is **Oct 22, 2026** and the days left are negative. Check enrollment.
2. HR → case shows the flag *Enrollment deadline passed on 2026-10-22* and 2 missing items; Approve is disabled.
3. Choose **Request information**, reason "Please choose dental and retirement" → status *More information requested*.
4. Employee → My requests shows HR's message. On My benefits, elect a dental plan (or waive it) and a retirement percent, **Save election** each, then **Recheck enrollment**.
5. HR → the case is back as *Ready for HR review*. **Approve** now needs a reason because of the late-enrollment flag.
- [ ] Pass [ ] Fail

**T5. Build an enrollment from nothing (E2011).**
1. Employee → E2011: four items to do, 30 days left, no cost summary yet.
2. Medical: choose **Elect coverage** and **Silver PPO — Employee** (the employee-only tier, so no dependents are needed). Click **Check with the Enrollment Agent** *before* saving: it explains the cost and says **nothing is saved**.
3. **Save election**. Do the same for dental, vision and retirement (waive or elect).
4. **Expect:** *Your cost per paycheck* appears. **Check enrollment and create case** → *Ready for HR review* with nothing missing.
5. Try a dependent: elect the *Employee + spouse* tier. A spouse is now required: add one (Relationship + Name), then **Mark as uploaded**; it stays on the list as *Received*.
- [ ] Pass [ ] Fail

**T6. Carrier disagreements and follow-ups (E2012).**
1. Employee → E2012 → check. HR → approve → **Prepare vendor records** → **Record simulated sending** → **Check confirmations**.
2. **Expect:** medical *Confirmed*; dental *No confirmation*; vision *Discrepancy* (tier); retirement *Discrepancy* (5% vs 4%). Status *Vendor follow-up needed* with **3 follow-up drafts**, each labelled as a draft for HR to send. Nothing is sent.
- [ ] Pass [ ] Fail

**T7. Specialist consultation (seeded case C1, E2004).** HR → open **C1** → **Check confirmations**. Expect a **Specialist consultation** panel (Vendor Agent → Enrollment Agent), the family-vs-employee mismatch, and a draft that cites the evidence. With AI off it shows *Unavailable* and still gives rule-based drafts.
- [ ] Pass [ ] Fail

**T8. A stale view cannot approve (E2007).**
1. Employee → E2007 → check (a case exists). HR → open that case and leave it open.
2. In a **second browser tab**, Employee → E2007 → change dental to *Waived* → **Save election**.
3. Back in the HR tab, choose **Approve** → **Record HR decision**.
4. **Expect:** the approval is **refused** ("This case changed after you opened it"), the page shows the **latest** version, and you can approve that version.
- [ ] Pass [ ] Fail

**T9. Ask questions (E2001, then E2005).** Employee → My benefits → *Ask the Enrollment Agent*: "I already uploaded my marriage certificate. Why is it still on my list?" Expect: received, waiting for HR, still on the list (E2001). The same question for **E2005** should say no document is on record and ask one question. *(Needs live AI for the sentences; with AI off you still get the facts list.)*
- [ ] Pass [ ] Fail

### Leave of absence

**T10. Leave from description to HR approval (E1006).**
1. Employee → Leave requests → pick **E1006**. *Your leave balance* shows 120 / 56 / 24 hours.
2. *Not sure what kind of leave?* → type "I need surgery and expect to be out about two weeks" → **Get a suggestion**. *(Needs live AI.)*
3. Choose **Your own serious health condition**, dates, **One continuous block**, tick the medical certification → **Check draft with the Leave Agent**. A draft is **not** a case yet.
4. Tick the confirmation → **Submit to HR**. HR → the case is *Ready for HR review* with *FMLA pre-check: meets the basics* (HR only). Approve.
- [ ] Pass [ ] Fail

**T11. Failing the FMLA basics is not a denial (E1007, E1008).** Submit a request for each. HR sees *does not meet the basics* with 11 months / 1,180 hours (E1007) and 30 months / 1,240 hours (E1008), and the note that HR still checks state leave and company policy. The **employee never sees** the pre-check.
- [ ] Pass [ ] Fail

**T12. Approved, pending a document (E1009).** Submit own-health leave **without** the certification. HR → **Approve, pending a document**, reason "a signed doctor's note" → status *Approved, pending a document*. Employee → the request → **Documents HR asked for** → **Mark as provided** for each item → *Approved, documents to verify*. HR → **Documents requested with the approval** → *Documents verified: complete the approval* → *Approved*. Also try *Ask for the document again* and *Withdraw the approval* (both need a reason).
- [ ] Pass [ ] Fail

**T13. Information request and correction on the same request (E1003).** Submit a request. HR → **Request information** with a reason. Employee → the request → **Correct and resubmit**, change the end date → **Resubmit to HR**. Expect the **same case number**, back in HR review, and no second case.
- [ ] Pass [ ] Fail

**T14. Unknown is never "no" (E1004, E1005).** Employee → Leave requests: the balance says it **could not be determined** (not zero). Submit a request: HR's pre-check says **Cannot determine**, not "not eligible".
- [ ] Pass [ ] Fail

**T15. A real zero versus unknown (E1002 vs E1005).** E1002 shows **0 hrs** for PTO, sick and personal. E1005 shows *could not be determined*. These must look different.
- [ ] Pass [ ] Fail

### Boundaries

**T16. The employee never sees HR-only information.** For E2003 (hours flag) and E1003 (fails the basics), look at every employee page and the request details. There must be no flag text, no "30-hour", no "FMLA basics" and no HR notes.
- [ ] Pass [ ] Fail

**T17. AI off.** Put `BENEFITS_AI_DISABLED=1` in `.env`, restart the server. The badge says *AI unavailable*. Repeat T1 and T6: every step still works; the AI boxes say they are unavailable, and the vendor drafts are plain templates.
- [ ] Pass [ ] Fail

**T18. Edit the data, then reset.** In `data/benefits_demo.json` change Elif Demir's `weekly_hours` from 40 to 20 and save. Press **Reset demo data**. Elect a medical plan for E2011 and check: HR now sees the hours flag. Change it back and reset.
- [ ] Pass [ ] Fail

## 4. What to write down when something looks wrong

Person ID, the test number and step, what you expected, what you saw, and a screenshot of the page and the Terminal window. **Never include `.env` or your key in a screenshot.**

## 5. Known limits (not bugs)

Fictional data; cases live in memory and reset on restart; "uploads" are labels only; the demo has no real login (you pick the person, and "HR" is the other view); carriers are simulated from `vendor_confirmations` in the data file; HR verification records that HR checked a document but not who or when beyond the demo name. See [the handoff](JOAN-HANDOFF.md) for the full list, and note that **live-AI behavior has not been verified by the author**: run T5 (explain a choice), T9 and T10 with a working key and report what you see.
