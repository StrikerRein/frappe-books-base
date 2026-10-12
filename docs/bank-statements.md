# Bank statement batches

Open **Common → Bank Statements** to upload and review a CSV statement. Download the template on that page. Required columns are `date`, `description`, `money_out`, and `money_in`; optional columns are `balance`, `reference`, `account`, and `classification`. Dates use `YYYY-MM-DD`. Categories use the full chart-of-accounts name. Keep the bank's original line order.

Supply the statement opening and closing balances. Every supplied line balance and the batch closing balance must reconcile. The original upload is retained as a private attachment. Classify every line before posting; personal and own-account movements use the owner's personal/current account.

Posting creates one **Books Bank Statement** voucher for the whole upload. Each source line creates its own two balanced ledger legs with the original transaction date and an explicit source-line link. It creates no journal-entry documents. The ledger's opening bank balance must agree with the statement opening balance, and overlapping bank periods are rejected. Opening balances are posted separately, rather than being repeated by every statement upload.

Profit & Loss, Balance Sheet and Trial Balance account links open the General Ledger. Click a bank description, statement or reference in that ledger to open the batch and highlight the exact original line. Each statement line links back to its bank and category postings. Searching a statement does not change its opening, movement or closing totals.

Existing journal imports can be retained as **Linked history** batches with their original source lines and ledger links. These batches are read-only and cannot be posted again; linking them does not change the accounting balances.

The initial uploader accepts the supplied CSV layout. It does not parse arbitrary bank PDFs or arbitrary Excel workbook layouts.
