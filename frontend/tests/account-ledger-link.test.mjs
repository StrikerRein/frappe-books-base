import assert from 'node:assert/strict';
import { test } from 'node:test';
import {
  fyo,
  BalanceSheet,
  GeneralLedger,
  ProfitAndLoss,
  TrialBalance,
  getAccountLedgerLink,
} from './helpers/frappe.mjs';

const account = '4000 - Rendering of services / memberships';
test('bank ledger source links keep the exact batch and transaction', () => {
  const report = new GeneralLedger(fyo);
  report.columns = [
    { fieldname: 'bank_statement', fieldtype: 'Data' },
    { fieldname: 'bank_transaction', fieldtype: 'Data' },
    { fieldname: 'bank_description', fieldtype: 'Data' },
  ];
  const row = report.getReportRow({
    type: 'entry',
    bank_statement: 'BS-001',
    bank_transaction: 'line-123',
    bank_description: 'Membership receipt',
  });
  assert.deepEqual(getAccountLedgerLink(report, row, report.columns[2]), {
    path: '/bank-statements/BS-001',
    query: { transaction: 'line-123' },
  });
  const opening = report.getReportRow({
    type: 'opening',
    bank_statement: 'BS-001',
  });
  assert.equal(getAccountLedgerLink(report, opening), null);
});
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

test('balance sheet accounts drill through with the selected statement period', () => {
  const report = new BalanceSheet(fyo);
  report.columns = [
    { fieldname: 'account', label: 'Account', fieldtype: 'Link' },
    {
      fieldname: 'period_2026_02_28',
      fieldtype: 'Currency',
      fromDate: '2025-03-01',
      toDate: '2026-02-28',
    },
  ];
  const row = report.getReportRow({
    account: '1100 - Owner current account / mixed bank clearing',
    indent: 2,
    period_2026_02_28: 197138.62,
  });
  assert.deepEqual(
    filters(getAccountLedgerLink(report, row, report.columns[1])),
    {
      account: '1100 - Owner current account / mixed bank clearing',
      fromDate: '2025-03-01',
      toDate: '2026-02-28',
      referenceType: 'All',
      groupBy: 'none',
    }
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

test('comparative amounts open their source without widening current account dates', () => {
  const report = statement();
  report.columns.push({ fieldname: 'comparison', fieldtype: 'Currency', fromDate: '2024-03-01', toDate: '2025-02-28', comparisonSource: 'CMP-001' });
  const row = report.getReportRow({ account, indent: 2, comparison: 100 });
  assert.deepEqual(getAccountLedgerLink(report, row, report.columns.at(-1)), { path: '/report-comparison/CMP-001', query: { account } });
  assert.equal(filters(getAccountLedgerLink(report, row)).fromDate, '2025-06-09');
});
test('opening balance amounts open ledger history through the day before the period', () => {
  const report = new TrialBalance(fyo);
  report.fromDate = '2025-03-01'; report.toDate = '2026-02-28';
  report.columns = [{ fieldname: 'account', fieldtype: 'Link' }, { fieldname: 'opening_debit', fieldtype: 'Currency' }];
  const row = report.getReportRow({ account, indent: 2, opening_debit: 100 });
  const dates = filters(getAccountLedgerLink(report, row, report.columns[1]));
  assert.equal(dates.fromDate, '1900-01-01');
  assert.equal(dates.toDate, '2025-02-28');
});
