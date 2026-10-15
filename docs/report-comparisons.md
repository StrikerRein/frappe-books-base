# Prior-year report comparisons

The trial balance, profit and loss and balance sheet offer **Compare Previous Year**. Existing ledger calculations remain the current-year source. Approved `Books Report Comparison` records supply non-posting prior-year amounts, including accounts with no current-year movement.

Each comparison has an exact financial-year date range, a private source workbook, its SHA-256, source notes, and one row per leaf account. `balance` is debit less credit; `source_cell` identifies the original workbook location. Import only verified source amounts. A supplied zero differs from a missing prior-year comparison: when no approved comparison exists, the report displays a notice and does not create zero comparison columns.

Only Books Managers and System Managers can maintain or read comparison records. Source viewing and downloading also require ledger read permission. Attach the private File to the comparison record after creation. Do not place client workbooks, amounts, credentials or import payloads in the repository.

For closing AFS figures, retained earnings already include that year's result. The comparative balance sheet therefore does not add comparative P&L again. A trial balance reference containing both closing equity and P&L can differ between debits and credits; the report explicitly discloses this and creates no balancing journal. Comparative columns are labelled AFS references rather than an unclosed trial balance.

Comparative amounts open their workbook source. Current-period amounts open General Ledger; trial balance opening amounts show history through the day before the selected start. Account labels keep the current reporting period. Print views retain comparison disclosures.

On sites with approved comparison data, report defaults use the financial year of the latest posted ledger entry and enable comparison. Other sites keep their existing defaults. The comparison is the entire prior financial year; partial current-period selections are explicitly disclosed and are not used to prorate source figures. Multi-year selections do not append an ambiguous comparison.

Deployment: migrate the site to create the two comparison DocTypes, build the frontend, and clear the site cache. Existing journals, ledger entries and bank transactions are unchanged by this feature.

Verification: `frappe_books.tests.test_comparatives`, frontend `tests/account-ledger-link.test.mjs`, frontend typecheck and production build. Reconcile imported source totals and compare a ledger fingerprint before and after each data import.
