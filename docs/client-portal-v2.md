# Client review portal — pilot

The client home opens on **2026 Tax & Accounts Review**, with Transactions to review, Missing documents, Questions / decisions and Progress. Clients see only their assigned tasks in enabled own/joint entities. Lindi Sugar Art is the portal display name of the existing Lindie bakery books; no extra legal entity or ledger was created.

## Accountant use

Select bank or ledger rows in Books and choose Assign client review. Set the question, client, workflow template and tax year. In `/client-review`, **Documents / questions** assigns a titled document request, question or allocation decision. Specify what is actually missing; the application does not assume example certificates are missing or fabricate task counts.

**Preview client view** is read-only, uses the accountant's existing permissions and does not impersonate a client session or send responses. Choose the client on the assignment screen first. Existing client logins remain unchanged. No invitation or notification emails are sent automatically.

## Client use

The overview counts real assigned items by tax year and entity. Continue review shows one unanswered item at a time, with follow-ups first. Transactions show date, amount, bank description and statement reference. Buttons distinguish business/personal expenses, split percentages and income classifications. Answers and reviewed items remain accessible separately. Progress distinguishes client action, accountant review and resolved tasks; it does not claim AFS or tax submission milestones have been completed.

Document requests accept up to 10 private files per request, 10 MB each: unlocked PDF, JPG, PNG, DOCX and XLSX. Format checks run before storage, alongside Frappe's native PDF safeguards. Downloads recheck the current task assignment and entity grant and are forced attachments. The public gateway exposes the checked download API, not raw private-file URLs, Desk or Books. Task and workflow audit histories record uploads and responses.

## Reusable split approvals

Clients can propose using a mixed-use percentage on similar payments. The accountant must first complete the task review, then explicitly approve a bank-description match and reason. Rules are scoped to client, entity and tax year. The approved rule opens the existing bulk-allocation screen with the match, date range, percentage and approval reference prefilled. The accountant still selects transactions and business/personal accounts and confirms before posting; existing stale-selection checks and audit/undo remain in force. Asking for further clarification pauses related rules until a new approval is recorded.

## Upgrade and verification

Back up the central portal. Reload Books Client Review and install Books Client Allocation Rule on the portal site. Backfill prior review tax years from their snapshot transaction dates (March–February year); question-only pilot items use 2026. Update the company-label configuration as approved. Rebuild the frontend and restart company/core web services. `deployment/client_review_gateway.py` documents the restricted VM preview gateway; upload body allowance is enlarged only on the checked upload endpoint.

Tests use fictional source scopes with rollback, no real client credentials, no emails and no ledger changes. They cover private upload/download, other-client denial, shared-entity assignment isolation, year/entity progress, malformed/oversized files, required document uploads, rule approval, paused rules and workflow regression. The online preview remains temporary and requires the PC/VM to stay online.
