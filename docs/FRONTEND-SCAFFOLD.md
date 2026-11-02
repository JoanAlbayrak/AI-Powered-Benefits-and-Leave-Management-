# Frontend scaffold

The root page connects the benefits workflow while keeping ordinary page browsing read-only. The leave form remains a preview. `/legacy` retains the original working workflow demo. Both are served by the same Python application on localhost. See [Benefits workflow](BENEFITS-WORKFLOW.md) for the current integration checkpoint.

## Run

```sh
python3 -m benefits_leave.web
```

Open http://127.0.0.1:8001. No frontend build, package installation, API key, or live AI call is needed to browse the scaffold. Agent actions in `/legacy` still use the original runtime and fallback behavior.

## Structure

- `frontend/index.html`: document, stylesheet/module entry points, no-JavaScript fallback.
- `frontend/styles/tokens.css`: shared palette, spacing, type stack, radii.
- `frontend/styles/app.css`: responsive shell and component layouts.
- `frontend/js/app.js`: rendering, loading/error state, navigation, profile selection, and queue filtering.
- `frontend/js/state.js`: role-specific routes and optional demo-profile preference.
- `frontend/js/api.js`: one same-origin request boundary, timeout handling, and backend error translation.
- `frontend/js/workflows.js`: one in-flight action and scoped status reconciliation after an uncertain response.
- `frontend/js/workflow-ui.js`: enrollment action, HR decision and vendor action/draft components.
- `frontend/js/components.js`: common components, escaping, formatters, icons, and status semantics.
- `frontend/js/views/employee.js`: overview, benefits snapshot, leave-form preview, next steps, and employee case detail.
- `frontend/js/views/hr.js`: queue, vendor overview, derived next steps, case history, and HR case detail.

The frontend uses native browser modules and a system sans-serif fallback when Inter is unavailable. `frontend/package.json` declares module syntax for optional Node-based tests; there are no Node dependencies or build steps.

## Data and boundaries

`POST /api/employee/overview` is a read-only projection over existing checks and fictional records. It does not call an agent, create a case, or alter workflow state. Employee responses omit HR flags, handoff packets, and internal history. `/api/people` and `/api/hr/queue` remain the existing read operations.

The role switch and profile picker are explicitly demo controls, not authentication. The Python case store remains in memory. Static serving is restricted to the dedicated frontend directory and supported extensions.

All dates and countdowns use the backend's demo snapshot date, which is displayed in the UI. Elections, evidence receipt, HR decisions, transmission, and carrier confirmation remain distinct concepts.

## Connected now

- Real demo profiles and election snapshots.
- Existing employee-visible cases and updates.
- HR queue, status filters, search, case details, approved handoff records, and history.
- Separate navigation for employee and HR previews.
- Responsive layout, accessible navigation controls, status labels, loading/error/empty states.
- Explicit enrollment checks and saved employee-safe guidance; HR decisions; approved vendor preparation, simulated sending and confirmation review/drafts.

## Deliberately disconnected

The new UI does not submit leave, edit elections, upload documents or create persistent tasks. These controls remain previews or disabled. No interface sends actual provider records or notices. Evidence clarification and specialist consultation remain proposed. The original workflow remains accessible through `/legacy`.

Next steps displayed from enrollment findings or case status are derived views, not a new persistent task engine. Assignment, due dates beyond existing enrollment rules, evidence lifecycle, reminders, and secure documents require their own implementation.

## Next development slice

Enrollment checking, HR review and vendor actions are connected. Next: live-model configuration/readiness, scoped evidence clarification and specialist consultation, then leave submission and correction/resubmission. Preserve backend guards and the frozen approved handoff. Do not add business rules in presentation code.

## Verification

```sh
python3 -m unittest
node --test tests/frontend.test.mjs
```

Python covers the existing workflows plus projection privacy/non-mutation and asset isolation. Node tests cover deep links, unknown case handling, HTML escaping, status distinctions, and API failures. Node is needed only for these optional frontend tests.

Browser acceptance: profile switching, all role navigation, HR filtering/search/empty state, case detail, leave preview, mobile navigation and layout, and no console errors. The scaffold is local development work; it is not deployed to the separate animated-story Site.
