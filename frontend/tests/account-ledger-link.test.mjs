import assert from 'node:assert/strict';
import { test } from 'node:test';
import {
  fyo,
  ProfitAndLoss,
  TrialBalance,
  getAccountLedgerLink,
} from './helpers/frappe.mjs';

const account = '4000 - Rendering of services / memberships';
function statement() {
  const report = new ProfitAndLoss(fyo);
  report.columns = [
    { fieldname: 'account', label: 'Account', fieldtype: 'Link' },
    {
      fieldname: 'period_2025_08_08',
      fieldtype: 'Currency',
      fromDate: '2025-07-09',
      toDate: '2025-08-08',
    },
    {
      fieldname: 'period_2025_07_08',
      fieldtype: 'Currency',
      fromDate: '2025-06-09',
      toDate: '2025-07-08',
    },
    {
      fieldname: 'total',
      fieldtype: 'Currency',
      fromDate: '2025-06-09',
      toDate: '2025-08-08',
    },
  ];
  return report;
}
const filters = (link) => JSON.parse(link.query.defaultFilters);

test('P&L amount links use the exact server period, including partial months', () => {
  const report = statement();
  const row = report.getReportRow({
    account,
    indent: 2,
    period_2025_08_08: 125,
  });
  assert.deepEqual(
    filters(getAccountLedgerLink(report, row, report.columns[1])),
    {
      account,
      fromDate: '2025-07-09',
      toDate: '2025-08-08',
      referenceType: 'All',
      groupBy: 'none',
    }
  );
  assert.equal(getAccountLedgerLink(report, row).path, '/report/GeneralLedger');
  assert.equal(
    filters(getAccountLedgerLink(report, row)).fromDate,
    '2025-06-09'
  );
  assert.equal(
    filters(getAccountLedgerLink(report, row, report.columns[3])).fromDate,
    '2025-06-09'
  );
});

test('trial balance drill-through keeps the selected historical dates and raw account name', () => {
  const report = new TrialBalance(fyo);
  report.fromDate = '2025-03-01';
  report.toDate = '2025-08-08';
  report.columns = [
    { fieldname: 'account', label: 'Account', fieldtype: 'Link' },
  ];
  const row = report.getReportRow({ account, indent: 2 });
  row.cells[0].value = 'Translated display label';
  assert.deepEqual(filters(getAccountLedgerLink(report, row)), {
    account,
    fromDate: '2025-03-01',
    toDate: '2025-08-08',
    referenceType: 'All',
    groupBy: 'none',
  });
});

test('group accounts link to their ledger; synthetic totals and blank rows do not', () => {
  const report = statement();
  assert.ok(
    getAccountLedgerLink(
      report,
      report.getReportRow({ account: 'Income', indent: 0, is_group: 1 })
    )
  );
  assert.equal(
    getAccountLedgerLink(
      report,
      report.getReportRow({ account: 'Total Profit', indent: 0, bold: 1 })
    ),
    null
  );
  assert.equal(getAccountLedgerLink(report, report.getEmptyRow()), null);
});

test('missing period metadata does not silently drill into the current year', () => {
  const report = statement();
  report.columns = report.columns.slice(0, 1);
  assert.equal(
    getAccountLedgerLink(report, report.getReportRow({ account, indent: 2 })),
    null
  );
});

test('drill-through respects permission to open General Ledger', () => {
  const previous = globalThis.window;
  globalThis.window = { frappe: { boot: { allowed_reports: {} } } };
  try {
    const report = statement();
    assert.equal(
      getAccountLedgerLink(report, report.getReportRow({ account, indent: 2 })),
      null
    );
  } finally {
    globalThis.window = previous;
  }
});
