# Reusable Workflows module

Open **Workflows** from the Books sidebar (`/books/workflows`). Company screens show that company's workflows; the central portal site shows all configured companies. Client permissions remain own accounts plus approved shared companies, with assigned tasks only.

## Templates and stages

Transaction clarification, Tax review and General client query are supplied. Template stages can be renamed and additional accountant review stages added. The required responsibility order is preparation, client assignment, client response, one or more accountant review stages, then completion. A workflow stores its stage definition when created; later template edits affect new workflows only.

Select ledger or bank items, choose a workflow template, client and question, then send. The selected items become review tasks in one workflow. Tax and other workflows can instead start with general questions, without transactions. Draft workflows remain internal until a question is assigned.

Client answers move the workflow to Client responded when all assigned questions have answers. Follow-up returns it to Assigned. Accountants advance review stages explicitly, with a note. Completion requires every task to be reviewed. Reopening and all stage changes record actor, time and reason. Task answers and review decisions retain their own history. Workflows do not post accounting entries or submit tax returns.

## Installation

Install the Books Workflow Template and Books Workflow DocTypes and the new workflow link on Books Client Review on the central portal site. Run `bench --site <portal-site> execute frappe_books.workflows.seed_templates` after metadata migration. Back up the portal first. Keep `books_review_portal_site` configured on company sites if it differs from books.localhost. Existing unlinked reviews remain usable; they can be linked during a managed migration without changing responses or financial postings.

The accountant-only bridge uses fixed operations in a separate portal context, verifies the accountant there, pins source company from the session, checks client grants and rejects cross-company workflow mutation. Clients cannot read raw workflow records or advance accountant stages. Public access remains through the restricted existing client portal.

## Validation

Integration tests cover custom stages, frozen definitions, client permission denial, answer/follow-up progression, stale edits, required task approval, completion and reopening. Rollback tests retain no fixtures or financial changes.
