import type { Report } from 'reports/Report';
import { canOpenReport } from 'reports/serverReport';
import type { ColumnField, ReportRow } from 'reports/types';
import type { RouteLocationRaw } from 'vue-router';

/** Account labels use the whole report; statement amounts use their server period. */
export function getAccountLedgerLink(
  report: Report,
  row: ReportRow,
  column?: ColumnField
): RouteLocationRaw | null {
  if (
    !['profit-and-loss', 'trial-balance'].includes(report.reportName) ||
    row.isEmpty ||
    row.isTotal ||
    !canOpenReport('Books General Ledger')
  )
    return null;

  const accountIndex = report.columns.findIndex(
    (c) => c.fieldname === 'account'
  );
  const account = row.cells[accountIndex]?.rawValue;
  if (typeof account !== 'string' || !account) return null;

  let fromDate: string | undefined;
  let toDate: string | undefined;
  if (report.reportName === 'trial-balance') {
    fromDate = report.get('fromDate') as string | undefined;
    toDate = report.get('toDate') as string | undefined;
  } else if (column?.fromDate && column.toDate) {
    ({ fromDate, toDate } = column);
  } else {
    const periods = report.columns.filter((c) => c.fromDate && c.toDate);
    fromDate = periods.map((c) => c.fromDate!).sort()[0];
    toDate = periods
      .map((c) => c.toDate!)
      .sort()
      .at(-1);
  }
  // Never open the ledger with today's defaults when the report is historical.
  if (!fromDate || !toDate) return null;
  return {
    path: '/report/GeneralLedger',
    query: {
      defaultFilters: JSON.stringify({
        account,
        fromDate,
        toDate,
        referenceType: 'All',
        groupBy: 'none',
      }),
    },
  };
}
