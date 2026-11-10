/**
 * Practice workspace selectors. All counts come from stored Frappe records;
 * stages and client answers are never treated as accounting postings.
 */
export type Stage = { name: string; role: string };
export type PracticeTask = {
  name: string;
  question: string;
  status: string;
  kind: string;
  answer?: string;
};
export type PracticeWorkflow = {
  name: string;
  title: string;
  template: string;
  topic: string;
  client: string;
  company: string;
  source_site: string;
  due_date?: string | null;
  stage: string;
  stages: Stage[];
  tasks: PracticeTask[];
};
export type PracticeClient = {
  email: string;
  label: string;
  sources: string[];
};
export type PracticeTemplate = {
  name: string;
  title: string;
  topic: string;
  enabled: number;
};
export type PracticeData = {
  cases: PracticeWorkflow[];
  clients: PracticeClient[];
  templates: PracticeTemplate[];
  sources: Record<string, string>;
};
export type BankBatch = {
  name: string;
  title: string;
  status: string;
  bank_account: string;
  from_date?: string;
  to_date?: string;
};
export type WorkStatus = 'review' | 'waiting' | 'draft' | 'active' | 'complete';

export function workStatus(work: PracticeWorkflow): WorkStatus {
  const role = work.stages.find((stage) => stage.name === work.stage)?.role;
  if (role === 'Complete') return 'complete';
  if (work.tasks.some((task) => task.status === 'Answered')) return 'review';
  if (work.tasks.some((task) => task.status === 'Open' || task.status === 'Follow-up')) {
    return 'waiting';
  }
  if (role === 'Draft' || work.tasks.length === 0) return 'draft';
  return 'active';
}

export const statusLabels: Record<WorkStatus, string> = {
  review: 'Ready for your review',
  waiting: 'Waiting for client',
  draft: 'Needs preparation',
  active: 'In progress',
  complete: 'Complete',
};

export function practiceCounts(
  cases: PracticeWorkflow[],
  clients: PracticeClient[],
  batches: BankBatch[]
) {
  return {
    review: cases.filter((work) => workStatus(work) === 'review').length,
    waiting: cases.filter((work) => workStatus(work) === 'waiting').length,
    active: cases.filter((work) => workStatus(work) !== 'complete').length,
    clients: clients.length,
    draftBatches: batches.filter((batch) => batch.status === 'Draft').length,
  };
}

/** Dates are compared as ISO calendar dates, avoiding timezone drift. */
export function dueLabel(date: string | null | undefined, today: string): string {
  if (!date) return '';
  if (date < today) return 'Overdue';
  if (date === today) return 'Due today';
  return '';
}

const priority: Record<WorkStatus, number> = {
  review: 0,
  waiting: 1,
  active: 2,
  draft: 3,
  complete: 4,
};

export function orderWork(cases: PracticeWorkflow[]): PracticeWorkflow[] {
  return [...cases].sort((a, b) => {
    const difference = priority[workStatus(a)] - priority[workStatus(b)];
    if (difference) return difference;
    const aDue = a.due_date || '9999-12-31';
    const bDue = b.due_date || '9999-12-31';
    return aDue.localeCompare(bDue) || a.title.localeCompare(b.title);
  });
}

export function clientWorkCount(cases: PracticeWorkflow[], email: string): number {
  return cases.filter((work) => work.client === email && workStatus(work) !== 'complete').length;
}
