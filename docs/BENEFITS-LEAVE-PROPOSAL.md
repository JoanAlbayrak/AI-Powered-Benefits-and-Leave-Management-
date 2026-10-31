# Benefits & Leave Case Team
## A plain-English field guide and product proposal

Prepared for Joan Albayrak and Dikshyant Giri | 31 October 2026

> The product in one sentence: help employees get their benefits and leave requests ready, help HR understand the evidence, and help HR follow up when a provider records something different.

This report explains the real-world process first, then proposes three cooperating AI agents that fit our existing application. Think of them as a small case team: a preparation specialist, a provider follow-up specialist and a leave guide. HR remains accountable for decisions.

### Your reading route
- Pages 2-5: understand the people, processes and real employer examples.
- Pages 6-10: meet the agents and watch them work together.
- Pages 11-12: understand the rules and documents behind the work.
- Pages 13-14: see the benefits, risks and practical build plan.
- Pages 15-17: open the official sources and suggested reading.

### How to read the labels
REAL EXAMPLE means a public employer or provider describes that practice. PROPOSED means a feature we recommend building. FICTIONAL means a teaching scenario, not a real employee or legal determination.

### Scope and evidence
U.S. employer benefits and leave, primarily the Department of Labor's FMLA framework. New York is one optional state example, not a national rule or an assumption about our deployment. Federal employment systems, other countries, collective bargaining agreements and every state/local rule need separate analysis.

Public documents support the examples; the process maps are our synthesis. Pain points are product hypotheses to validate with HR and employees. This is a product and learning report, not individualized legal advice or a production compliance certification. Sources were consulted on 31 October 2026.

---
# 01 / HR without the jargon
## Who does what?

An employee choosing insurance is not buying it from HR. The employer sponsors benefits, a plan defines the terms, and outside organizations may insure or administer them. Several records must agree.

| Person or system | Plain-English job |
| Employee | Chooses available benefits, supplies information and confirms their own request. |
| HR / benefits team | Explains process, verifies evidence, applies approved rules and handles exceptions. |
| Carrier / administrator | The insurer or service provider that processes coverage or administers benefits. |
| HRIS / payroll | The employment-record system and the system that handles pay and deductions. |
| Leave administrator | An internal specialist or external team coordinating leave paperwork and notices. |

### Six words you will see
- Election: the employee's recorded benefit choice, including a permitted waiver.
- Dependent: an eligible family member being covered, under the particular plan's rules.
- Coverage tier: who is covered, such as employee-only or employee plus spouse.
- Premium: the cost of coverage; an employee may pay part through payroll.
- Open enrollment: the employer's regular opportunity to make benefit elections. New hires and qualifying events may have other opportunities under applicable rules.
- Certification: supporting information for a leave request; it is not automatically a request for a diagnosis or full medical chart.

> Four different milestones: employee selected -> HR reviewed -> record sent -> provider confirmed. One milestone does not prove the next.

### A useful distinction
A benefit tells you what support or coverage is available. A leave entitlement tells you when time away may be protected. A pay benefit tells you what income may continue. These can overlap without being the same thing. See [1], [2] and [5].

---
# 02 / How enrollment works today
## From choosing a plan to confirmed coverage

FLOW: Learn the options | Record choices | Review and resolve | Send approved data | Confirm and reconcile

### 1. The employer makes the rules available
Employees receive enrollment instructions and plan information. The plan documents, eligibility rules, rates and applicable enrollment event determine what is available. A company deadline is not automatically a universal legal deadline. [1], [2]

### 2. The employee records their choices
They select permitted medical, dental, vision or retirement options, add eligible dependents and provide any required evidence. Some benefits may have default or automatic enrollment arrangements; the product must support the actual employer configuration rather than assume every missing choice is an error. [2], [12]

### 3. HR or an administrator resolves problems
A missing field can be detected by code. A statement such as "I already sent that document to onboarding" needs investigation: which system, which document, what verification status, and which policy applies? Our proposed Enrollment Agent assists here.

### 4. Records move to providers and payroll
Organizations can use integrated systems, file transfers or administrative portals. ADP publicly describes API and EDI carrier connections; mature employers are not universally running on paper. Integration availability depends on the provider and platform. [4]

### 5. Someone checks what actually happened
Our proposed reconciliation compares the approved choice with the applicable provider confirmation. It checks the person, plan, tier, effective date and transaction version. "Sent" alone is not confirmation. A pending response is not automatically a rejection or a provider error.

> Our opening: help people resolve unclear or conflicting cases around existing systems. A new portal alone does not solve the investigation work.

---
# 03 / How leave works today
## Three questions hiding inside one request

| Employee asks | HR must work out |
| Can I be away? | Which employer policies and legal protections might apply? |
| Will I be paid? | PTO, employer paid leave, disability or state benefits may have different conditions. |
| What happens to my insurance? | Applicable continuation rules, plan terms and any employee premium obligations. |

FLOW: Notice of need | Eligibility and rights | Supporting information | Designation and coordination | Track and return

### The practical journey
An employee tells the employer they need time away. They may not know the legal name of the leave. HR identifies potentially applicable programs, checks relevant employment facts, supplies required notices, obtains permitted supporting information where needed, and determines the request. Payroll or an outside administrator may also be involved. [5], [6], [7]

HR then coordinates dates, time used, pay arrangements and return-to-work steps. A manager usually needs operational information about availability and restrictions, not the employee's full medical story. Medical-record handling needs separate controls. [10]

### What our app should do
Let an employee start in ordinary language: "I need two Fridays each month to help my father with treatment." The proposed Leave Agent asks about dates and schedule, retrieves the relevant approved guidance and prepares a review packet. It does not promise that the request qualifies.

> FMLA protection is generally unpaid. A paid-leave program is a separate question. Failing an FMLA pre-check must not automatically become "all leave denied." Other laws or policies may apply. [5], [9], [13]

### Important workflow change
Separate a friendly clarification from an official HR request for information. An agent conversation must not silently start a statutory notice deadline or change a formal case decision. HR-approved notices need their own recorded event.

---
# 04 / Real organizations, concrete lessons
## What public documents show

### REAL EXAMPLE / Stanford University
Stanford's benefits instructions give new hires 31 days to complete health enrollment through its benefits portal and tell them to print a confirmation statement. They also describe specific default coverage if the window is missed. This is one employer's arrangement, not a nationwide 31-day rule. [2]

PRODUCT LESSON: show the actual employer deadline, preserve the employee's confirmation and distinguish a default election from a missing record. Stanford is an employer example; its page does not establish the law for every organization.

### REAL EXAMPLE / GitLab
GitLab's U.S. leave handbook says that, effective 2 February 2026, its U.S. requests are administered through Tilt. Employees can access that service through Okta and receive leave-specialist support. The handbook discusses coordinating company and statutory programs, including pay questions. [3]

PRODUCT LESSON: real leave processes may involve a specialist outside HR's own portal. Our product should organize a case and hand it to the responsible person or administrator, rather than pretend one chatbot owns every decision.

### REAL EXAMPLE / ADP carrier integrations
ADP describes electronic exchanges for plan setup, employee enrollment and evidence of insurability, using APIs or EDI. These are provider-described capabilities, not independent proof of error reductions or evidence that every employer has these connections. [4]

PRODUCT LESSON: keep our first version independent of live integrations. Use realistic fictional confirmations; add a provider adapter later without changing the case model.

> None of these organizations is claimed to use our product or our multi-agent design. Their public practices help us ground the workflow; our agent proposal is our own.

---
# 05 / Agent 1: Enrollment Guide
## "Help me get this ready correctly."

PROPOSED / Keeps the existing Enrollment Agent's domain and HR approval boundary.

### Its goal and trigger
Help an employee understand and complete an enrollment packet. Run when the employee asks for help, responds to a clarification or asks to check readiness. Browsing the dashboard should not launch an AI run.

### What it can read
The scoped employee's elections, deterministic completeness results, approved plan explanations, policy version, evidence status and relevant case history. It needs document status first, not unrestricted access to every uploaded file.

### Where it uses judgment
It decides whether the next useful step is explaining a term, retrieving an evidence record, asking one focused question or escalating an exception. It must support its explanation with a source and keep employee claims separate from verified facts.

### FICTIONAL / A short conversation
Employee: "Why does it say spouse proof is missing? I sent it already."

Agent checks the evidence index and sees a received document awaiting HR verification. It explains: "A document was received, but HR has not verified it yet. You do not need to upload another copy unless HR asks." If there is no matching record, it asks where the employee submitted it.

### What it hands over
An employee checklist and an HR summary: verified facts, outstanding choices, evidence references, policy references, unknowns and proposed next action. When asked by the Vendor Agent, it can explain the intent captured in a particular approved snapshot.

> It never selects a plan, recommends a retirement contribution, verifies a marriage certificate on its own, grants eligibility or approves enrollment. Received, verified and approved are separate states.

### What stays in ordinary code
Required-field checks, configured deadlines, match calculations, access scope and the rule preventing approval of an incomplete enrollment. A match formula belongs to the plan; our demo's 4% is fictional, not a statutory promise. [12]

---
# 06 / Agent 2: Vendor Investigator
## "Did the provider record what HR approved?"

PROPOSED / Extends the existing Vendor Agent without giving it external sending rights.

### Its goal and trigger
Help HR investigate an unconfirmed or inconsistent enrollment after HR approval and recorded sending. Run on HR request or a future configured confirmation event. The first build can remain manually triggered.

### What it can read
The frozen approved handoff, the record marked as sent, scoped provider confirmations, transaction identifiers and relevant correspondence supplied to the case. A later election edit must not silently replace what was approved earlier.

### Where it uses judgment
Code identifies the exact difference. The agent investigates whether a newer response exists, whether two records refer to the same transaction, and what follow-up would resolve the uncertainty. It distinguishes evidence from a possible explanation; it must not invent a provider's root cause.

### FICTIONAL / A specialist consultation
Confirmation: employee-only medical coverage. Approved snapshot v3: employee plus spouse.

Vendor Agent asks the Enrollment Agent: "For case C1, approved snapshot v3, what coverage intent and dependent-verification status were recorded?" The reply cites that snapshot. Vendor Agent incorporates the answer and drafts a precise HR follow-up identifying the discrepancy.

### What it hands over
A discrepancy list with source references, questions still open, proposed follow-ups and draft messages. HR reviews and sends them through the approved channel. A later matching confirmation can support resolution through the controlled workflow.

> A draft is not a sent message. An acknowledgment is not necessarily successful enrollment. An old confirmation cannot prove a newer change was processed.

### What stays in ordinary code
Field comparisons, employee and transaction matching, approval/sent prerequisites, handoff validation and resolution gates. Cases with missing or stale evidence remain open or uncertain rather than being marked corrected by a persuasive summary.

---
# 07 / Agent 3: Leave Guide
## "Help me describe what I need and understand the next step."

PROPOSED / Builds on the existing Leave Agent and its deterministic pre-check.

### Its goal and trigger
Prepare a clear leave request and an evidence-backed HR packet. Run when an employee asks for help with a draft or submits an explicitly confirmed request, or when HR asks for a case summary.

### What it can read
The scoped request, relevant employment facts from an authorized lookup, approved leave policy snippets and permitted evidence status. Access to medical documents must be narrower than access to ordinary case history.

### Where it uses judgment
It translates ordinary language into a proposed schedule and request category, notices ambiguities, asks targeted questions and explains sourced instructions. The employee confirms the structured request before submission. An uncertain classification stays uncertain.

### FICTIONAL / Jordan's two Fridays
Jordan: "I need two Fridays a month to care for my father."

Agent: "What date would this start, and do you expect full days or part days?" It prepares a draft schedule for confirmation. Code checks dates and retrieves employment facts. The agent explains which information is missing and routes possible intermittent family-care leave for HR review; it does not guarantee qualification.

### What it hands over
Confirmed request details, pre-check results, missing facts, evidence references and questions for HR. If benefits continuation is relevant, it can ask the Enrollment Agent for an authorized summary of current elections. That summary cannot establish leave-related continuation or payment rights by itself.

> An unavailable HR lookup means "cannot determine." It must never become zero service, an eligibility failure or an automatic denial.

### What stays in ordinary code and human review
Date validation and configured pre-checks stay in code. HR determines eligibility/designation, applies exceptions and sends required notices. The agent must not demand a diagnosis or a medical certificate for every request just because a generic checklist has that field. [5], [7], [9]

---
# 08 / How the team becomes multi-agent
## A consultation must change the work

Three differently named prompts are not a convincing demonstration of collaboration. Our proposal gives each specialist its own bounded objective and tools, then lets a specialist request useful information from another specialist through controlled workflow code.

FLOW: Employee or HR asks | Specialist investigates | Scoped consultation | Evidence-backed answer | Human review

### Keep the coordinator as code
The existing workflow remains the traffic controller. It validates the case and permissions, routes an allowed request, records the response and resumes the requesting agent. We do not need a fourth AI manager, a new agent platform or an unrestricted agent group chat.

### Example handoff / Vendor -> Enrollment
| Field | Example content |
| Scope | Case C1; employee E2004; approved snapshot v3 |
| Question | What medical coverage intent was approved? |
| Evidence | Snapshot v3 and sent transaction T42; confirmation R17 |
| Reply | Employee plus spouse approved; cite the snapshot fields |
| Unknown | Whether the provider has processed the correction |
| Next action | Return findings to Vendor Agent for an HR-reviewed draft |

### The loop that makes the agent useful
Retrieve relevant evidence -> inspect the uncertainty -> choose a question or consultation -> incorporate the response -> submit a sourced finding or escalate. The next step depends on what the agent discovers, within fixed permissions.

### Boundaries to implement
Use an allow-list of consultation types, employee/case scope, maximum calls, a total case budget and a stop/escalation rule. Avoid recursive back-and-forth. Keep agent-run states such as awaiting clarification separate from formal approval states. Log useful findings and references rather than hidden model reasoning.

> Not every case needs every agent. A clear leave request can use the Leave Agent alone. Demonstrate real collaboration on cases where a specialist's answer changes the investigation or draft.

---
# 09 / Follow one case from start to finish
## Maya's enrollment mystery

FICTIONAL / This is a proposed demonstration using synthetic records, not a real employee outcome. Its document requirements are fictional employer policy.

### Scene 1 / "I already uploaded it"
Maya's checklist says her dependent evidence is outstanding. Enrollment Agent retrieves evidence status instead of repeating the warning. It finds a document received but awaiting verification. Maya sees the actual next step: wait for HR review, with a clear status rather than another upload request.

### Scene 2 / The human checkpoint
HR verifies the evidence and reviews Maya's confirmed elections. Code allows approval only when required conditions are met. It freezes snapshot v3. HR prepares the provider record and marks it sent. Neither agent performs those actions.

### Scene 3 / Something does not match
The applicable provider confirmation lists employee-only coverage. Code detects a tier mismatch against the approved employee-plus-spouse snapshot. Vendor Agent checks whether the response is current and consults Enrollment Agent about v3's approved intent.

### Scene 4 / A precise follow-up
Enrollment Agent returns the approved intent with references. Vendor Agent drafts a follow-up naming the case, approved tier, transaction and discrepancy. HR reviews it and sends through the proper channel. Our app records the sending event only when HR explicitly does so.

### Scene 5 / Evidence closes the loop
A later applicable confirmation matches the approved record. Code rechecks the fields and controlled workflow records the outcome. If no matching confirmation arrives, the case remains unresolved. AI confidence cannot close it.

> The demonstration's proof: the consultation supplies verified context that changes the final follow-up. Show the before-and-after draft alongside the evidence, not just three animated agent icons.

### A second, smaller story
For Jordan's leave request, show a missing start date, a focused clarification, employee confirmation and HR review. Add a benefits consultation only if it answers a real question, and show escalation when the continuation policy is absent.

---
# 10 / Rules: what comes from where?
## Law, plan terms and company policy are different

"Bylaws" usually means rules governing an organization. For this product, the practical document set is employment law and regulations, benefit plan documents, approved employer policies and individual case evidence.

| Layer | What it tells us | Product treatment |
| Law / regulation | Applicable rights, duties and limits | HR-approved rules with jurisdiction and effective dates |
| Plan documents / SPD / SBC | How a particular benefit works and a summary of coverage | Retrieve the applicable plan version; do not invent terms |
| Employer policy | Enrollment instructions, paid leave arrangements and internal process | Explicit configuration; cannot simply override applicable law |
| Case evidence | What was selected, received, verified, approved or confirmed | Preserve origin, date, scope and version |

### FMLA basics / federal example
Eligible employees of covered employers generally receive up to 12 workweeks of job-protected leave for qualifying reasons, with a separate military-caregiver entitlement. FMLA itself is generally unpaid and includes group-health continuation conditions. The usual eligibility checks involve employer coverage, 12 months of employment, 1,250 service hours and the worksite threshold; special rules and exceptions matter. Our current simple pre-check cannot establish all of this. [5]

### Notices and supporting information
Eligibility notice is generally due within five business days, absent extenuating circumstances. Designation follows once the employer has sufficient information. Certification timing and correction opportunities have specific rules and exceptions; do not turn them into a universal upload countdown. [6], [8], [11]

### State and accommodation layers
New York Paid Family Leave provides eligible workers job protection and partial wage replacement for covered family-related reasons; it is not a general substitute for an employee's own medical leave. ADA accommodation obligations may require separate review even when FMLA does not apply. Pregnancy-related accommodation rules can also matter. [9], [13], [14]

> Never let "the FMLA check failed" automatically answer every legal, pay and accommodation question.

---
# 11 / The documents our product needs
## A small, governed policy library

### Benefits pack
Obtain the applicable plan documents, Summary Plan Description (SPD), Summary of Benefits and Coverage (SBC), enrollment guide, rate sheet, eligibility/dependent rules and event instructions. For retirement, use the plan's actual match and participation terms. The SPD and SBC are different documents; neither is just marketing copy. [1], [12]

### Leave pack
Obtain approved leave policies, applicable jurisdiction guidance, employer notice procedures and official or equivalent forms. DOL provides optional-use templates: WH-381 for eligibility and rights/responsibilities; WH-382 for designation; WH-380-E/F for employee/family medical certification. Equivalent complete certification cannot be rejected merely for using another format. [7]

### Evidence pack
Keep election confirmations, received/verified evidence status, HR decisions, approved snapshots, sent records, provider replies and discrepancy history. Store only what each actor needs; avoid putting medical details in a vendor handoff or a broadly visible timeline.

### Every policy entry needs a label
Owner; title; employer/plan; jurisdiction; effective-from/to dates; version; section/page; source link; review date; approved use. If the right version cannot be found, say so and escalate. Start with a small curated JSON or text library; a vector database is not required for the first slice.

### Privacy is more specific than "HIPAA compliant"
HHS explains that HIPAA generally does not protect employment records, even if health-related; health-plan and provider records can be treated differently. This does not make HR medical data unrestricted. FMLA medical certifications and histories require confidential handling in separate records, subject to applicable rules. [10], [15]

> First demo: use fictional evidence references and status fields. Real document ingestion needs a separate access, retention, security and model-provider review before use with employee data.

### Conflicting documents
The agent flags the conflict, quotes only the relevant short passage and cites both versions. HR or the plan administrator resolves it. Do not let an AI decide that the newest-looking PDF automatically overrides governing plan terms or applicable law.

---
# 12 / Honest assessment
## Where this helps, and where it can fail

| Potential benefit | Tradeoff or failure mode | Design response |
| Fewer repetitive questions | A fluent answer may still be wrong | Show the exact source and unknowns |
| Clearer HR packets | Too much output adds review work | Short facts / gaps / next action format |
| Better exception investigation | More calls add cost and delay | Consult only when useful; cap calls |
| Specialist separation | Handoffs can lose context | Structured packets with case/version scope |
| Easier employee intake | Chat can obscure formal submission | Show a confirmed form before submission |
| Better provider follow-up | An old response may look convincing | Compare transaction and effective-date context |

### The realistic product position
Established HR platforms already offer enrollment, rules, workflows and integrations. We should not claim that adding three agents makes those capabilities new. Our proposed advantage is helping resolve unclear cases with traceable explanations and useful specialist consultations around that foundation. This is a hypothesis, not proven differentiation. [2], [3], [4]

### Why AI belongs here
Use it for interpreting an ambiguous employee question, selecting relevant evidence, asking a focused clarification and drafting a context-aware explanation. Use ordinary code for dates, arithmetic, required fields, comparisons, permission enforcement and state changes. A routine complete case should move forward without unnecessary agent discussion.

### What we still need to learn
Interview at least one HR benefits specialist, one leave specialist and several employees. Ask them to walk through anonymized difficult cases, identify repeated questions and explain what makes a packet reviewable. Do not collect real medical records for discovery. Validate pain points before claiming time savings.

> A successful demo shows correct handling of uncertainty and a useful resolution path. It does not need to pretend to replace HR, a benefits administrator or legal counsel.

---
# 13 / Build it without rebuilding the app
## A practical sequence with visible proof

### Where we actually are
The repository has three scoped agent definitions, deterministic checks, bounded tool execution and a code-owned case workflow. The new employee/HR interface is a read-only scaffold; the older /legacy demo connects workflow actions. Storage is in memory, identities are demo selections and data is fictional. The public static demo uses example messages rather than live model calls. This is a demo foundation, not a production HR platform.

### Milestone 1 / Connect one benefits journey
Use the existing routes and API adapter for employee check -> HR review -> approval -> provider preparation -> mark sent -> confirmation review. Preserve approval guards and the frozen handoff. Finish when the new UI completes that journey and an incomplete enrollment still cannot be approved.

### Milestone 2 / Add evidence and clarification
Add versioned policy snippets, evidence-status/history retrieval and saved clarification context. Add a small "Help me finish" panel, not a new dashboard. Finish when "already uploaded" can produce different, grounded responses for absent, received and verified evidence.

### Milestone 3 / Add one real consultation
Route Vendor -> Enrollment requests through workflow code. Add allowed request types, scope checks, call limits, failure handling and a recorded exchange. Finish when the answer changes the HR follow-up and cross-employee or wrong-version requests are blocked.

### Milestone 4 / Connect leave and evaluate
Add draft clarification, employee confirmation, HR review and separate formal notice events. Test missing dates, unavailable employment data, uncertain policy and potential non-FMLA review. Persistent storage and real identity controls are later prerequisites for use beyond a fictional demo.

### What proves quality
Require zero unauthorized decisions/sends and zero cross-employee disclosures in the evaluation set; reject wrong-snapshot reconciliation. Check factual findings against source records, measure unnecessary questions and compare HR review effort, latency and cost with the simpler deterministic baseline. Use synthetic cases and a fake model for workflow tests, plus controlled live-model evaluations for answer quality.

> Recommended next build: connect the existing benefits journey, then add one evidence clarification and one useful Vendor-to-Enrollment consultation. Keep all three agents; deepen their work in small, testable steps.

---
# 14 / Reading shelf
## Start with these public examples and guides

Each numbered reference is clickable in the PDF. Titles and URLs are included in the editable source. Sources support the adjacent factual claims; architecture, UI and delivery recommendations are our proposal.

### [1] DOL / Plan Information
Explains SPD and SBC documents and participant information duties for applicable plans. Read this to understand why a plan booklet is more useful than a generic benefits FAQ.
LINK: https://www.dol.gov/general/topic/health-plans/planinformation

### [2] Stanford / Eligibility and Enrollment
A real employer's enrollment portal, new-hire deadline and confirmation instructions. Use as a workflow example, not as our employer policy.
LINK: https://cardinalatwork.stanford.edu/benefits-rewards/my-benefits-portal/eligibility-enrollment

### [3] GitLab / United States Leave of Absence Policies
A public company handbook describing third-party administration and coordinated leave programs. Company policy can change; this is not a universal legal rule.
LINK: https://handbook.gitlab.com/handbook/people-policies/leave-of-absence/us/

### [4] ADP / Insurance Benefits Carrier Integrations
A provider's description of API/EDI exchanges and enrollment capabilities. Treat benefits claims as vendor statements, not independently measured results.
LINK: https://www.adp.com/what-we-offer/benefits/benefits-administration/carrier-integrations.aspx

### [5] DOL / Fact Sheet 28: FMLA
The best first legal-domain primer: covered employers, employee eligibility, qualifying reasons and protections. Guidance, not a substitute for the statute or regulations.
LINK: https://www.dol.gov/agencies/whd/fact-sheets/28-fmla

### [6] DOL / The FMLA Leave Process
A plain-language sequence from employee notice through employer designation and return. Read alongside the timing details and exceptions in the rules.
LINK: https://www.dol.gov/agencies/whd/fmla/FMLA-leave-process

### [7] DOL / FMLA Forms
Official optional-use forms and explanations. Open WH-381 and WH-382 first, then WH-380-E/F. Do not send completed employee certifications to DOL.
LINK: https://www.dol.gov/agencies/whd/fmla/forms

---
# 15 / Legal and policy references
## Keep these beside the product specification

### [8] DOL / FMLA FAQs
Practical details about eligibility notices, timing and other common situations. Agency guidance explaining the underlying rules.
LINK: https://www.dol.gov/agencies/whd/fmla/faq

### [9] EEOC / Employer-Provided Leave and the ADA
Explains why disability-related accommodation review may still be required when ordinary leave or FMLA is unavailable. This is agency technical assistance.
LINK: https://www.eeoc.gov/laws/guidance/employer-provided-leave-and-americans-disabilities-act

### [10] 29 CFR 825.500 / Recordkeeping
Official 2025 annual CFR edition: includes separate confidential handling for FMLA medical records. For deployment, verify the current regulation through [11].
LINK: https://www.govinfo.gov/content/pkg/CFR-2025-title29-vol3/pdf/CFR-2025-title29-vol3-sec825-500.pdf

### [11] DOL / Applicable Laws and Regulations
The official route to the FMLA statute and current 29 CFR Part 825. Review 825.110 (eligibility), 825.300 (notices), 825.305 (certification) and 825.500 (records). Direct eCFR access was unavailable during this review; annual-edition excerpts were also checked. No claim of a complete current-law audit is made.
LINK: https://www.dol.gov/agencies/whd/fmla/laws-and-regulations

---
# 16 / Benefits, state rules and privacy
## The remaining reference documents

### [12] IRS / Matching Contributions
Explains why retirement matching conditions come from the actual plan document and SPD. Our demonstration match formula is only an example.
LINK: https://www.irs.gov/retirement-plans/matching-contributions-help-you-save-more-for-retirement

### [13] New York / Paid Family Leave for Employees
One state-specific example with eligibility, applications, protections and annually changing benefit information. Do not copy it into a nationwide default.
LINK: https://paidfamilyleave.ny.gov/employees

### [14] EEOC / Pregnant Workers Fairness Act
An additional accommodation framework to flag for HR when relevant; it requires its own applicability and current-law review.
LINK: https://www.eeoc.gov/wysk/what-you-should-know-about-pregnant-workers-fairness-act

### [15] HHS / Employers and Health Information
Explains the distinction between employment records and covered health information. Other confidentiality duties still matter.
LINK: https://www.hhs.gov/hipaa/for-individuals/employers-health-information-workplace/index.html

### Project basis
Original Benefits & Leave Agents PRD v4, dated 26 October 2026; repository README and scaffold handoff inspected 31 October 2026. Where PRD test counts or capabilities differ from the current scaffold, this report uses the observed implementation boundary and avoids treating historical test totals as current validation.
