# Scaffold handoff

**Status: complete.** The new interface foundation is committed locally. Core workflow integration is the next development phase.

## Delivered

- Modular HTML/CSS/JavaScript frontend with shared tokens, components, role-specific routes, and one API adapter.
- Read-only employee overview, benefits, next steps, request detail, and leave-form preview.
- HR queue with filters/search, case review, vendor overview, derived next steps, and history.
- Loading, error, and empty states; responsive navigation; keyboard focus and skip-link handling.
- Existing fictional records and workflow state are displayed without generating AI output or creating cases.
- Original connected workflow remains at `/legacy`.

## Verified

- 45 Python tests passed: original workflow tests plus read-model privacy/non-mutation and asset isolation.
- 7 Node tests passed: role-aware deep links, unknown cases, HTML escaping, status semantics, and API error handling.
- Browser checks: employee profile changes, enrollment navigation, leave preview, HR queue filters/search/empty state, case detail and approved handoff, vendor overview, next steps, and history.
- Mobile at 390px: navigation closes after selection, filtered rows remain hidden, and no page-level horizontal overflow was observed on the checked views.

## Commit milestones

1. `feat(api): add read-only employee workspace overview`
2. `feat(ui): scaffold employee and HR workspaces`
3. `docs: document scaffold setup and integration boundaries`

Commits are local; no remote push was performed.

## Next slice

Connect the new enrollment check to the existing endpoint, then HR decisions, vendor preparation, mark-sent, and confirmation checks. Preserve existing backend guards and the frozen approved handoff. Follow with leave submission and correction/resubmission. See `FRONTEND-SCAFFOLD.md` for the architecture and explicit boundaries.

## Start locally

Run `python3 -m benefits_leave.web` from the repository root, then open http://127.0.0.1:8001.

Role and identity controls are demo previews, not authentication. The case store is still in memory. New decision, submission, upload, election-editing, and persistent task controls remain disconnected until their workflow phase.
