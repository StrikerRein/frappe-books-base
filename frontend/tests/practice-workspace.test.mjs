import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
import ts from 'typescript';

// Test the exact selector module consumed by the Vue page without a build step.
const source = readFileSync(new URL('../src/utils/practiceWorkspace.ts', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText;
const module = { exports: {} };
runInNewContext(compiled, { module, exports: module.exports });
const {
  workStatus, practiceCounts, dueLabel, orderWork, clientWorkCount
} = module.exports;

const stages = [
  { name: 'Draft', role: 'Draft' },
  { name: 'Assigned', role: 'Assigned' },
  { name: 'Client responded', role: 'Responded' },
  { name: 'Accountant review', role: 'Review' },
  { name: 'Complete', role: 'Complete' },
];
function workflow(name, status, due_date = '') {
  return {
    name, title: name, template: 'Tax review', topic: 'Tax', client: 'one@example.test',
    company: 'Example company', source_site: 'example.localhost', due_date,
    stages, stage: status === 'complete' ? 'Complete' : status === 'draft' ? 'Draft' : 'Assigned',
    tasks: status === 'draft' ? [] : [{ name: name + '-task', question: 'Example question', status:
      status === 'review' ? 'Answered' : status === 'waiting' ? 'Open' : status === 'complete' ? 'Reviewed' : 'Follow-up' }],
  };
}

test('client answers take priority over unanswered tasks, but completed stays completed', () => {
  const w = workflow('ready', 'waiting');
  w.tasks.push({ name: 'other', question: 'Reply', status: 'Answered' });
  assert.equal(workStatus(w), 'review');
  w.stage = 'Complete';
  assert.equal(workStatus(w), 'complete');
});

test('counts are sourced from actual cases, client grants and current-company bank batches', () => {
  const cases = [workflow('a', 'review'), workflow('b', 'waiting'), workflow('c', 'complete')];
  const grants = [{ email: 'one@example.test', label: 'One', sources: ['example.localhost'] }];
  const banks = [{ name: 'BANK-1', title: 'Import', bank_account: 'Bank', status: 'Draft' }];
  const counts = practiceCounts(cases, grants, banks);
  assert.equal(counts.review, 1);
  assert.equal(counts.waiting, 1);
  assert.equal(counts.active, 2);
  assert.equal(counts.clients, 1);
  assert.equal(counts.draftBatches, 1);
  assert.equal(clientWorkCount(cases, 'one@example.test'), 2);
});

test('due labels use local ISO dates rather than timezone-dependent date conversions', () => {
  assert.equal(dueLabel('2026-11-09', '2026-11-10'), 'Overdue');
  assert.equal(dueLabel('2026-11-10', '2026-11-10'), 'Due today');
  assert.equal(dueLabel('2026-11-11', '2026-11-10'), '');
  assert.equal(dueLabel(null, '2026-11-10'), '');
});

test('priority order puts accountant review first, sorts due dates and preserves source', () => {
  const cases = [
    workflow('waiting', 'waiting'),
    workflow('review-late', 'review', '2026-12-01'),
    workflow('review-early', 'review', '2026-11-10'),
    workflow('done', 'complete'),
  ];
  assert.deepEqual(Array.from(orderWork(cases), (w) => w.name), ['review-early', 'review-late', 'waiting', 'done']);
  assert.equal(cases[0].name, 'waiting');
});
