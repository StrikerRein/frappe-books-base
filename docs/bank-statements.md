# Bank statement batches

Open **Common → Bank Statements** to upload and review a CSV statement. Download the template on that page. Required columns are `date`, `description`, `money_out`, and `money_in`; optional columns are `balance`, `reference`, `account`, and `classification`. Dates use `YYYY-MM-DD`. Categories use the full chart-of-accounts name. Keep the bank's original line order.

Supply the statement opening and closing balances. Every supplied line balance and the batch closing balance must reconcile. The original upload is retained as a private attachment. Classify every line before posting; personal and own-account movements use the owner's personal/current account.

Posting creates one **Books Bank Statement** voucher for the whole upload. Each source line creates its own two balanced ledger legs with the original transaction date and an explicit source-line link. It creates no journal-entry documents. The ledger's opening bank balance must agree with the statement opening balance, and overlapping bank periods are rejected. Opening balances are posted separately, rather than being repeated by every statement upload.

Profit & Loss, Balance Sheet and Trial Balance account links open the General Ledger. Click a bank description, statement or reference in that ledger to open the batch and highlight the exact original line. Each statement line links back to its bank and category postings. Searching a statement does not change its opening, movement or closing totals.

Existing journal imports can be retained as **Linked history** batches with their original source lines and ledger links. These batches are read-only and cannot be posted again; linking them does not change the accounting balances.

## Bulk category corrections

For shared personal/business payments, select **Mixed spend**, choose the business category, enter the business-use percentage, and choose the owner's personal account for the remainder. The same split can be applied to one payment or a selected group of payments. The preview shows both amounts. Each payment retains its full statement amount and balance; only its category allocation is split. Business amounts are rounded in the company currency and the personal portion receives the exact remainder.

Posted splits can be revised or converted to a full category allocation through bulk reallocation, with history and undo. On a statement, **Split / change spend** opens the selected payment. Draft statements also have percentage and personal-account fields. The CSV template supports `business_percentage` and `personal_account` columns. Mixed-spend percentages must be greater than zero and less than 100; use Business or Personal for a full allocation.

Open **Common → Bulk Reallocation**, or **Bulk reallocate** from the General Ledger. Filter by dates, current category or bank description; select up to 1,000 transactions across statement batches; choose the new category and classification; enter a reason; then review and apply.

Posted statements and linked historical imports are supported. Category corrections create one audited reallocation record, with balanced corrections on each original transaction date. The original source lines and bank ledger entries are preserved. Statement categories and reports reflect the correction. Split or inconsistent allocations must be reviewed separately.

The statement's **Category change history** shows the user, time, reason and destination category. **Undo this reallocation** restores all transactions in that operation, including any from other statements. If there are later changes, undo those first. A statement cannot be cancelled while it has active reallocations.

The initial uploader accepts the supplied CSV layout. It does not parse arbitrary bank PDFs or arbitrary Excel workbook layouts.
