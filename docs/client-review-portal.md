# Client review portal

`/client-review` is a separate, responsive website with the existing Frappe login. It does not load the Books desktop boot or expose the ledger to clients.

Accountants (System Manager) can choose a configured source account, find bank transactions, assign up to 50 items with a question and optional due date, or ask a question without a transaction. Active duplicate transaction assignments to the same client are rejected. The answer inbox provides completion, follow-up, source links and a response history.

Clients (Website User with Books Review Client role) see only their assigned snapshots in explicitly granted source accounts. They can explain use, suggest business/private/rental/transfer/mixed/unsure and provide a mixed-use percentage or category. Only the assigned client can answer. Revoked access hides existing assignments. Clients have no direct DocType or bank-reading permissions. Answers and completed reviews never post accounting entries; accountant checking and posting remain separate.

The audit log retains assignments, revised answers, follow-ups and completions. Row locks and modification checks prevent an accountant from silently completing an outdated answer. Completed answers require reopening before further client changes.

## Configuration

Install the Books Client Review and Books Review Access DocTypes on the central review site. Create the Books Review Client role with desk_access disabled. Create Website Users without Books or System Manager roles. Enable the intended client/source pairs in Books Review Access. Keep source configuration private in site_config.json:

```json
{
  "books_review_sources": {"example.localhost": "Example business"},
  "books_review_source_urls": {"example.localhost": "https://books.example.com"}
}
```

Source reading runs a fixed, read-only helper in an isolated Frappe process on the same bench. Only configured sibling site directories are accepted. Client API calls cannot invoke it. The accountant gets selected public source fields; client snapshots exclude raw workbook data, internal source review notes, original bank balances and source-file attachments.

No invitation or notification emails are sent automatically. Password provisioning and delivery are handled separately. The preview supplies no upload or email-password-reset workflow. Use a stable HTTPS host with backups and normal operational monitoring for permanent client use. Temporary tunnels depend on the local PC and VM remaining online, and their URLs can change on restart.

The public preview gateway allows only login, logout, the client review page, its public Frappe assets and the six review endpoints. It rejects Books, Desk, general resource APIs and private-file paths. Session cookies are secure and write requests retain Frappe CSRF checks. Production hosting should maintain equivalent isolation and TLS; do not expose a development server directly.

## Validation

The integration test covers separate client visibility, denied cross-client answers and source reading, denied raw document access, guest denial, invalid percentages, mixed-use answers, follow-up, audit retention and completion locking. The local end-to-end verification also checks real client HTTPS login, secure cookies, anonymous API denial and gateway route restrictions. Test questions are rolled back and no client allocations are changed.


## Assign inside Books

On a bank statement, tick transaction checkboxes and choose **Assign client review**. In the General Ledger, tick the checkbox beside each entry number, including journal entries in a suspense account. Up to 50 items can be assigned at once. Choose an eligible client, enter the question and optional due date, then send to the review inbox. Changing ledger filters clears the selection; pagination keeps selected items. Opening, total and closing rows cannot be assigned.

The accountant-only bridge reads snapshots from the current company and writes review tasks into the configured sibling portal site (`books_review_portal_site`, default `books.localhost`). The authenticated accountant must also have an enabled manager account on the portal. Client grants are checked centrally. Browser-supplied amounts and source sites are ignored. Assignment never posts or changes the ledger, and duplicate active reviews for the same source item/client are rejected atomically.
