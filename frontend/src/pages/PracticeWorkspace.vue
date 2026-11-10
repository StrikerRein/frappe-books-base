<template>
  <main class="h-full overflow-y-auto bg-gray-50 text-gray-900">
    <div class="mx-auto max-w-7xl px-4 pb-16 pt-6 sm:px-7 lg:pt-9">
      <header class="mb-7 flex flex-col justify-between gap-5 sm:flex-row sm:items-start">
        <div>
          <p class="mb-2 text-xs font-semibold uppercase tracking-widest text-blue-700">Your accounting practice</p>
          <h1 class="text-2xl font-semibold tracking-tight sm:text-3xl">Good to see you. Here's the work that matters.</h1>
          <p class="mt-2 max-w-xl text-sm leading-6 text-gray-600">
            Find client questions, bookkeeping and reviews in one place. Everything shown here comes from your saved records.
          </p>
        </div>
        <div class="flex flex-wrap gap-2">
          <button type="button" class="secondary-button" :disabled="busy" @click="load">
            {{ busy ? 'Refreshing…' : 'Refresh' }}
          </button>
          <button type="button" class="primary-button" :disabled="!workspace || busy" @click="openNewWorkflow()">
            + New client workflow
          </button>
        </div>
      </header>

      <p v-if="notice" role="status" class="mb-5 rounded-xl border border-green-200 bg-green-50 p-3 text-sm text-green-900">{{ notice }}</p>

      <section v-if="newOpen && workspace" class="mb-6 rounded-2xl border border-blue-200 bg-white p-5 shadow-sm" aria-label="New client workflow">
        <div class="mb-4 flex items-center justify-between gap-3">
          <div>
            <h2 class="text-lg font-semibold">Start a client workflow</h2>
            <p class="mt-1 text-sm text-gray-600">Send one clear request to the right client. You can also leave the first question blank and prepare the workflow as a draft.</p>
          </div>
          <button type="button" class="secondary-button" @click="newOpen = false">Close</button>
        </div>
        <form class="grid gap-4 md:grid-cols-2" @submit.prevent="createWorkflow">
          <label class="field-label">
            Company or entity
            <select v-model="form.source_site" class="field-input" required>
              <option value="" disabled>Select an entity</option>
              <option v-for="(label, site) in workspace.sources" :key="site" :value="site">{{ label }}</option>
            </select>
          </label>
          <label class="field-label">
            Client
            <select v-model="form.client" class="field-input" required>
              <option value="" disabled>Select a client</option>
              <option v-for="client in eligibleClients" :key="client.email" :value="client.email">{{ client.label }}</option>
            </select>
          </label>
          <label class="field-label">
            Type of work
            <select v-model="form.template" class="field-input" required>
              <option v-for="template in activeTemplates" :key="template.name" :value="template.name">{{ template.title }}</option>
            </select>
          </label>
          <label class="field-label">
            Due date (optional)
            <input v-model="form.due_date" type="date" class="field-input" />
          </label>
          <label class="field-label md:col-span-2">
            What needs to be done?
            <input v-model.trim="form.title" class="field-input" required maxlength="140" placeholder="e.g. 2026 annual accounts and tax review" />
          </label>
          <label class="field-label md:col-span-2">
            First question for your client (optional)
            <textarea v-model.trim="form.question" class="field-input min-h-24" maxlength="4000" placeholder="e.g. Can you upload your outstanding bank statements?" />
          </label>
          <div class="md:col-span-2">
            <p v-if="createError" role="alert" class="mb-3 text-sm text-red-700">{{ createError }}</p>
            <button type="submit" class="primary-button" :disabled="submitting || !canCreate">
              {{ submitting ? 'Creating…' : form.question.trim() ? 'Create and assign question' : 'Create draft workflow' }}
            </button>
          </div>
        </form>
      </section>

      <div v-if="busy && !workspace && !batches.length" role="status" class="rounded-2xl border bg-white p-8 text-sm text-gray-600">Loading your practice workspace…</div>

      <section v-else>
        <div class="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
          <button type="button" class="metric-card text-left" :aria-pressed="filter === 'review'" @click="setFilter('review')">
            <span class="metric-label">Ready for your review</span>
            <strong class="mt-3 block text-3xl font-semibold tabular-nums">{{ counts.review }}</strong>
            <span class="mt-2 block text-xs text-gray-500">Client answers to check</span>
          </button>
          <button type="button" class="metric-card text-left" :aria-pressed="filter === 'waiting'" @click="setFilter('waiting')">
            <span class="metric-label">Waiting for clients</span>
            <strong class="mt-3 block text-3xl font-semibold tabular-nums">{{ counts.waiting }}</strong>
            <span class="mt-2 block text-xs text-gray-500">Workflows needing a response</span>
          </button>
          <button type="button" class="metric-card text-left" :aria-pressed="filter === 'all'" @click="setFilter('all')">
            <span class="metric-label">Active workflows</span>
            <strong class="mt-3 block text-3xl font-semibold tabular-nums">{{ counts.active }}</strong>
            <span class="mt-2 block text-xs text-gray-500">Across enabled client entities</span>
          </button>
          <RouterLink to="/bank-statements" class="metric-card block no-underline">
            <span class="metric-label">Bank batches to post</span>
            <strong class="mt-3 block text-3xl font-semibold tabular-nums">{{ counts.draftBatches }}</strong>
            <span class="mt-2 block text-xs text-gray-500">Current company only</span>
          </RouterLink>
        </div>

        <div v-if="portalError" role="status" class="mb-5 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
          <strong>Client workspace not connected.</strong>
          <p class="mt-1">Banking is still available. The client-review service could not be loaded: {{ portalError }}. Check your portal configuration to enable practice-wide workflows.</p>
        </div>
        <div v-if="bankError" role="status" class="mb-5 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
          Bank statement summaries are unavailable for this company: {{ bankError }}
        </div>

        <div class="grid items-start gap-5 lg:grid-cols-3">
          <section class="rounded-2xl border border-gray-200 bg-white shadow-sm lg:col-span-2" aria-labelledby="work-heading">
            <div class="border-b border-gray-100 px-5 py-5">
              <div class="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
                <div>
                  <h2 id="work-heading" class="text-lg font-semibold">Work queue</h2>
                  <p class="mt-1 text-sm text-gray-500">{{ selectedClient === 'all' ? 'All clients' : clientLabel(selectedClient) }} · {{ visibleCases.length }} workflow(s)</p>
                </div>
                <RouterLink to="/workflows" class="text-sm font-semibold text-blue-700 hover:underline">Manage all workflows</RouterLink>
              </div>
              <div class="mt-4 flex flex-col gap-3 sm:flex-row">
                <label class="min-w-0 flex-1">
                  <span class="sr-only">Search workflows</span>
                  <input v-model="search" type="search" class="field-input !mt-0" placeholder="Search by client, work or entity" />
                </label>
                <label class="sm:w-48">
                  <span class="sr-only">Filter workflows</span>
                  <select v-model="filter" class="field-input !mt-0">
                    <option value="all">All work</option>
                    <option value="review">My review</option>
                    <option value="waiting">Waiting for client</option>
                    <option value="draft">Drafts</option>
                    <option value="active">In progress</option>
                    <option value="complete">Completed</option>
                  </select>
                </label>
              </div>
            </div>
            <div v-if="!workspace" class="px-5 py-12 text-center text-sm text-gray-500">Connect the client review service to see your work queue.</div>
            <div v-else-if="!visibleCases.length" class="px-5 py-12 text-center">
              <p class="font-medium text-gray-800">Nothing to show with these filters.</p>
              <p class="mt-1 text-sm text-gray-500">Try another filter or start a new client workflow.</p>
              <button type="button" class="secondary-button mt-4" @click="resetFilters">Show all work</button>
            </div>
            <div v-else class="divide-y divide-gray-100">
              <article v-for="work in visibleCases.slice(0, 40)" :key="work.name" class="px-5 py-4 transition hover:bg-gray-50">
                <div class="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
                  <div class="min-w-0">
                    <span class="mb-2 inline-block rounded-full px-2.5 py-1 text-xs font-medium" :class="statusClass(work)">
                      {{ statusLabels[workStatus(work)] }}
                    </span>
                    <h3 class="break-words font-semibold text-gray-900">{{ work.title }}</h3>
                    <p class="mt-1 text-sm text-gray-500">{{ clientLabel(work.client) }} · {{ work.company }} · {{ work.topic }}</p>
                    <p v-if="work.due_date" class="mt-2 text-xs" :class="dueLabel(work.due_date, today) === 'Overdue' ? 'font-semibold text-red-700' : 'text-gray-600'">
                      {{ dueLabel(work.due_date, today) || 'Due ' + displayDate(work.due_date) }}
                    </p>
                    <p class="mt-2 text-xs text-gray-500">{{ work.tasks.length }} question(s) · {{ work.tasks.filter(task => task.status === 'Answered').length }} awaiting approval</p>
                  </div>
                  <RouterLink :to="{ path: '/workflows', query: { search: work.name } }" class="secondary-button inline-flex shrink-0 items-center justify-center">
                    Open work
                  </RouterLink>
                </div>
              </article>
              <p v-if="visibleCases.length > 40" class="px-5 py-3 text-sm text-gray-500">Showing the first 40 workflows. Narrow your search to find more.</p>
            </div>
          </section>

          <aside class="space-y-5">
            <section class="rounded-2xl border border-gray-200 bg-white shadow-sm" aria-labelledby="clients-heading">
              <div class="border-b border-gray-100 px-5 py-4">
                <div class="flex items-center justify-between gap-2">
                  <h2 id="clients-heading" class="text-lg font-semibold">Clients</h2>
                  <span class="text-sm text-gray-500">{{ counts.clients }}</span>
                </div>
                <p class="mt-1 text-sm text-gray-500">Choose a client to focus your work queue.</p>
                <input v-model="clientSearch" type="search" class="field-input mt-3" placeholder="Find a client" aria-label="Find a client" />
              </div>
              <div class="max-h-80 overflow-y-auto p-2">
                <button type="button" class="client-choice" :class="selectedClient === 'all' ? 'bg-blue-50 text-blue-900' : ''" :aria-pressed="selectedClient === 'all'" @click="selectedClient = 'all'">
                  <span>All clients</span><span class="text-xs text-gray-500">Show everything</span>
                </button>
                <button v-for="client in visibleClients" :key="client.email" type="button" class="client-choice" :class="selectedClient === client.email ? 'bg-blue-50 text-blue-900' : ''" :aria-pressed="selectedClient === client.email" @click="selectedClient = client.email">
                  <span class="truncate font-medium">{{ client.label }}</span>
                  <span class="whitespace-nowrap text-xs text-gray-500">{{ clientWorkCount(workspace?.cases || [], client.email) }} active</span>
                </button>
                <p v-if="!visibleClients.length" class="p-4 text-sm text-gray-500">{{ workspace ? 'No clients match your search. Client access is managed in the review portal.' : 'Clients appear when the review portal is connected.' }}</p>
              </div>
              <div v-if="selectedClient !== 'all'" class="border-t border-gray-100 px-5 py-3">
                <button type="button" class="text-sm font-semibold text-blue-700 hover:underline" @click="openNewWorkflow(selectedClient)">Start work for this client</button>
              </div>
            </section>

            <section class="rounded-2xl border border-gray-200 bg-white shadow-sm" aria-labelledby="bank-heading">
              <div class="flex items-start justify-between gap-2 border-b border-gray-100 px-5 py-4">
                <div>
                  <h2 id="bank-heading" class="text-lg font-semibold">Bank statements</h2>
                  <p class="mt-1 text-xs text-gray-500">Current accounting company</p>
                </div>
                <RouterLink to="/bank-statements" class="text-sm font-semibold text-blue-700 hover:underline">View all</RouterLink>
              </div>
              <div v-if="!batches.length" class="p-5 text-sm text-gray-600">
                No bank statement batches found.
              </div>
              <div v-else class="divide-y divide-gray-100">
                <RouterLink v-for="batch in recentBatches" :key="batch.name" :to="'/bank-statements/' + encodeURIComponent(batch.name)" class="block px-5 py-3 no-underline hover:bg-gray-50">
                  <span class="block truncate text-sm font-medium text-gray-900">{{ batch.title }}</span>
                  <span class="mt-1 flex flex-wrap items-center justify-between gap-2 text-xs text-gray-500">
                    <span class="truncate">{{ batch.bank_account }}</span>
                    <span :class="batch.status === 'Draft' ? 'font-semibold text-amber-700' : 'text-gray-500'">{{ batch.status }}</span>
                  </span>
                </RouterLink>
              </div>
              <div class="border-t border-gray-100 px-5 py-4">
                <RouterLink to="/bank-statements" class="secondary-button block text-center">Import or review a statement</RouterLink>
              </div>
            </section>
            <section class="rounded-xl border border-gray-200 bg-white p-5">
              <h2 class="font-semibold">Accounting tools</h2>
              <div class="mt-3 grid grid-cols-2 gap-2 text-sm">
                <RouterLink to="/report/TrialBalance" class="tool-link">Trial balance</RouterLink>
                <RouterLink to="/report/ProfitAndLoss" class="tool-link">Profit &amp; loss</RouterLink>
                <RouterLink to="/bank-reallocation" class="tool-link">Reclassify</RouterLink>
                <RouterLink to="/chart-of-accounts" class="tool-link">Accounts</RouterLink>
              </div>
            </section>
          </aside>
        </div>
        <p class="mt-6 text-xs leading-5 text-gray-500">
          Workflow completion records client and accountant review only. It does not post bank transactions, approve financial statements or file SARS returns.
        </p>
      </section>
    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { call } from 'src/web/api';
import {
  type BankBatch, type PracticeClient, type PracticeData, type PracticeWorkflow,
  clientWorkCount, dueLabel, orderWork, practiceCounts, statusLabels, workStatus
} from 'src/utils/practiceWorkspace';

const workspace = ref<PracticeData>();
const batches = ref<BankBatch[]>([]);
const busy = ref(false);
const submitting = ref(false);
const portalError = ref('');
const bankError = ref('');
const createError = ref('');
const notice = ref('');
const selectedClient = ref('all');
const clientSearch = ref('');
const search = ref('');
const filter = ref('all');
const newOpen = ref(false);

const date = new Date();
const today = [date.getFullYear(), String(date.getMonth() + 1).padStart(2, '0'), String(date.getDate()).padStart(2, '0')].join('-');
const emptyForm = () => ({ template: '', client: '', source_site: '', title: '', question: '', due_date: '' });
const form = ref(emptyForm());

const counts = computed(() => practiceCounts(workspace.value?.cases || [], workspace.value?.clients || [], batches.value));
const activeTemplates = computed(() => workspace.value?.templates.filter((template) => template.enabled) || []);
const eligibleClients = computed(() => workspace.value?.clients.filter((client) => client.sources.includes(form.value.source_site)) || []);
const visibleClients = computed(() => [...(workspace.value?.clients || [])]
  .filter((client) => client.label.toLocaleLowerCase().includes(clientSearch.value.toLocaleLowerCase()))
  .sort((a, b) => a.label.localeCompare(b.label)));
const visibleCases = computed(() => orderWork(workspace.value?.cases || []).filter((work) => {
  if (selectedClient.value !== 'all' && work.client !== selectedClient.value) return false;
  if (filter.value !== 'all' && workStatus(work) !== filter.value) return false;
  const needle = search.value.trim().toLocaleLowerCase();
  return !needle || [work.name, work.title, work.topic, work.company, clientLabel(work.client)].join(' ').toLocaleLowerCase().includes(needle);
}));
const recentBatches = computed(() => [...batches.value].sort((a, b) => {
  if (a.status === 'Draft' && b.status !== 'Draft') return -1;
  if (b.status === 'Draft' && a.status !== 'Draft') return 1;
  return (b.to_date || '').localeCompare(a.to_date || '');
}).slice(0, 5));
const canCreate = computed(() => {
  const value = form.value;
  return !!value.source_site && !!value.client && !!value.template && !!value.title.trim()
    && eligibleClients.value.some((client) => client.email === value.client);
});

watch(() => form.value.source_site, () => {
  if (!eligibleClients.value.some((client) => client.email === form.value.client)) {
    form.value.client = '';
  }
});

function clientLabel(email: string) {
  return workspace.value?.clients.find((client) => client.email === email)?.label || email;
}
function statusClass(work: PracticeWorkflow) {
  const status = workStatus(work);
  if (status === 'review') return 'bg-blue-100 text-blue-800';
  if (status === 'waiting') return 'bg-amber-100 text-amber-900';
  if (status === 'complete') return 'bg-green-100 text-green-800';
  return 'bg-gray-100 text-gray-700';
}
function displayDate(value: string) {
  return new Intl.DateTimeFormat('en-ZA', { day: 'numeric', month: 'short', year: 'numeric' }).format(new Date(value + 'T12:00:00'));
}
function setFilter(value: string) { filter.value = filter.value === value ? 'all' : value; }
function resetFilters() { filter.value = 'all'; search.value = ''; selectedClient.value = 'all'; }
function openNewWorkflow(email = '') {
  if (!workspace.value) return;
  const client = workspace.value.clients.find((item: PracticeClient) => item.email === email);
  form.value = {
    ...emptyForm(),
    source_site: client?.sources[0] || Object.keys(workspace.value.sources)[0] || '',
    client: client?.email || '',
    template: activeTemplates.value.find((template) => template.name === 'Tax review')?.name || activeTemplates.value[0]?.name || '',
  };
  createError.value = '';
  newOpen.value = true;
}
async function load() {
  if (busy.value) return;
  busy.value = true;
  portalError.value = '';
  bankError.value = '';
  const [work, bank] = await Promise.allSettled([
    call<PracticeData>('frappe_books.review_bridge.workflow', { operation: 'workspace' }),
    call<BankBatch[]>('frappe_books.bank_import.list_batches'),
  ]);
  if (work.status === 'fulfilled') {
    workspace.value = work.value;
  } else {
    workspace.value = undefined;
    portalError.value = work.reason instanceof Error ? work.reason.message : String(work.reason);
  }
  if (bank.status === 'fulfilled') {
    batches.value = bank.value;
  } else {
    batches.value = [];
    bankError.value = bank.reason instanceof Error ? bank.reason.message : String(bank.reason);
  }
  busy.value = false;
}
async function createWorkflow() {
  if (!canCreate.value || submitting.value) return;
  submitting.value = true;
  createError.value = '';
  notice.value = '';
  try {
    await call('frappe_books.review_bridge.workflow', { operation: 'create', values: { ...form.value } });
    newOpen.value = false;
    notice.value = 'Workflow created. You can manage its questions and approvals from the work queue.';
    filter.value = 'all';
    selectedClient.value = form.value.client;
    search.value = '';
    await load();
  } catch (error) {
    createError.value = error instanceof Error ? error.message : String(error);
  } finally {
    submitting.value = false;
  }
}
onMounted(load);
</script>

<style scoped>
.metric-card { @apply rounded-2xl border border-gray-200 bg-white p-4 shadow-sm transition hover:border-blue-300 hover:shadow-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500; }
.metric-label { @apply text-sm font-medium text-gray-600; }
.primary-button { @apply rounded-lg bg-blue-700 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500 disabled:cursor-not-allowed disabled:opacity-50; }
.secondary-button { @apply rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm font-semibold text-gray-800 transition hover:bg-gray-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500 disabled:cursor-not-allowed disabled:opacity-50; }
.field-label { @apply block text-sm font-medium text-gray-700; }
.field-input { @apply mt-1 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100; }
.client-choice { @apply flex w-full items-center justify-between gap-2 rounded-lg px-3 py-2.5 text-left text-sm transition hover:bg-gray-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500; }
.tool-link { @apply rounded-lg border border-gray-200 bg-gray-50 px-3 py-3 text-center text-sm text-gray-800 hover:border-blue-300 hover:text-blue-700; }
</style>
