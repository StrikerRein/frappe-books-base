# Practice workspace MVP (November 2026)

This work continues the existing `report-ledger-drilldown` branch without replacing the accounting ledger or deploying untested financial changes. It is the first **practice-focused UX layer** on top of the existing browser-based Frappe Books fork.

## User experience

Open **Practice** in the desktop sidebar, in the phone navigation sheet, or via the accountant's first mobile tab. The workspace includes:

- A prioritised queue of real client workflows: **ready for accountant review**, **waiting for client**, **draft**, **in progress**, **complete**.
- Search, status filters, due-date warnings and direct links to specific workflow records.
- Client/entity filters limited to granted review portal access.
- A guided form for starting a client workflow, with optional first question and due date.
- A current-company bank statement panel with draft batches surfaced first.
- Direct routes to the trial balance, P&L, category reallocation and chart of accounts.
- Independent failure states: if the central review portal is not configured or available, the banking panel still loads.

**Important:** `workflows.workspace` on a company site is intentionally scoped to that source company. The central portal site may show all configured entities. Banking shown in the workspace always comes from the currently selected Frappe site. The interface does not pretend to aggregate bank statements across sites.

The bank statement screen also has an improved upload guide, clearer navigation, an empty state and mobile-friendly layout. The client review portal receives stronger focus indicators, mobile touch targets and easier horizontal navigation.

## Existing system used

- `frappe_books.review_bridge.workflow(operation='workspace')` reads the existing client workflow repository. `operation='create'` creates workflows with the same backend validation as the existing Workflows screen.
- `frappe_books.bank_import.list_batches` reads bank statement status. No ledger mutations are performed by the new workspace.
- Work queue selectors live in `frontend/src/utils/practiceWorkspace.ts` and are covered by `frontend/tests/practice-workspace.test.mjs`.
- Deep links filter the existing `/workflows` screen by exact workflow ID.
- Company scoping is enforced by the existing server bridge, *not just by UI filters*.

## Installation / checks

Work on `feature/practice-workspace-ux`. Do not merge or deploy this branch until it passes the existing repository's CI and a real-site walkthrough.

1. Back up the Frappe sites, database and private attachments. Confirm that the existing pilot branch has already been migrated to the test installation.
2. In a **non-production** bench, checkout the feature branch. Run `bench --site <company-site> migrate` and `bench --site <portal-site> migrate` as appropriate, then rebuild the frontend, clear caches and restart services.
3. Run frontend checks from `frontend/`: `yarn install --frozen-lockfile`, `yarn lint`, `yarn typecheck`, `yarn test`, `yarn build`.
4. Run Frappe integration tests, particularly `frappe_books.tests.test_workflows`, `test_review_portal`, `test_portal_v2`, `test_bank_import` and `test_bank_reallocation`.
5. Verify manager and Books User permissions. Test separate clients with shared entities, portal unavailable, empty accounts, stale client responses and document access denial.
6. In a test company, validate source bank balances, duplicate import detection, posting permission, transaction drill-down and audit/undo before any client data is introduced.

The GitHub repository may not have Actions enabled on the fork; a successful commit alone is **not** proof of passed checks. This branch has not been deployed by the authoring workflow.

## Deliberately not automated

The workspace does **not** create journal entries, change business/private allocations, approve financial statements, file SARS returns, or make tax determinations. Client answers are proposals for accountant review. No LLM API, credentials, client financial files or tax submission automation have been added.

## Next technical phase

1. **Core stability:** decide on a supported Frappe / Frappe Books release and test the migration from the pinned `develop` fork before merging upstream; retain exact versions and restore instructions.
2. **Separate apps:** progressively move practice management and client portal into an independent Frappe app instead of permanently patching the core Books source. Keep the audited ledger logic and database constraints in the accounting engine.
3. **Banking:** build bank-specific import mapping, duplicate/reconciliation review, automated rule suggestions and exception handling, preserving original statement evidence.
4. **Practice management:** add client master, engagements, work ownership, deadlines and SARS/AFS workpapers with authoritative task state.
5. **AI:** add a separate model gateway for *suggested* classifications and document extraction, with explanations, confidence/uncertainty, source evidence, an approval gate and complete logging. Never let an agent directly alter posted ledger or file tax returns without an explicit controlled action.
6. **Operations:** establish backups, monitored HTTPS, least-privilege site access, private attachment storage, audit retention, regression testing and AGPL compliance review before commercial hosting.

## Acceptance criteria for this MVP

- An accountant can open Practice and find their pending client work in a few seconds.
- Counts and status labels always reflect actual saved workflows; no invented completion numbers.
- The accountant can create a draft or assign a question from the new page.
- A client cannot see the accountant dashboard or another client's information through the API.
- On mobile, the Practice tab is the main navigation option for managers and the legacy Dashboard remains reachable via the navigation sheet.
- The bank import workflow still requires an accountant to review, reconcile and explicitly post a statement.
