<template>
  <div class="h-full overflow-auto p-5 text-ink-gray-8">
    <div class="flex items-center justify-between mb-5">
      <h1 class="text-xl font-semibold">Bank statements</h1>
      <RouterLink to="/bank-statements" class="underline"
        >All batches</RouterLink
      >
    </div>
    <p v-if="error" role="alert" class="p-3 mb-4 bg-red-50 text-red-700">
      {{ error }}
    </p>
    <p v-if="busy">Loading…</p>
    <template v-if="batch">
      <h2 class="text-lg font-semibold">{{ batch.title }}</h2>
      <p class="my-2">
        {{ batch.bank_account }} · {{ batch.from_date }} to
        {{ batch.to_date }} · {{ batch.status }}
      </p>
      <div class="flex gap-8 my-4">
        <p>
          Opening <strong>{{ money(batch.opening_balance) }}</strong>
        </p>
        <p>
          Money in <strong>{{ money(totalIn) }}</strong>
        </p>
        <p>
          Money out <strong>{{ money(totalOut) }}</strong>
        </p>
        <p>
          Closing <strong>{{ money(batch.closing_balance) }}</strong>
        </p>
      </div>
      <a
        v-if="batch.source_attachment"
        :href="batch.source_attachment"
        target="_blank"
        class="underline"
        >Open original source file</a
      >
      <div v-if="batch.status === 'Draft'" class="flex gap-3 my-4">
        <button class="border rounded px-3 py-2" :disabled="busy" @click="save">
          Save classifications
        </button>
        <button
          class="border rounded px-3 py-2 bg-blue-50"
          :disabled="busy"
          @click="post"
        >
          Post statement batch
        </button>
      </div>
      <input
        v-model="search"
        placeholder="Search description, reference or account"
        class="border rounded p-2 w-full my-4"
        aria-label="Search bank transactions"
      />
      <div class="overflow-auto">
        <table class="w-full text-sm tabular-nums border-collapse">
          <thead>
            <tr class="text-left border-b">
              <th class="p-2">Date / reference</th>
              <th class="p-2">Bank description</th>
              <th class="p-2 text-right">Money out</th>
              <th class="p-2 text-right">Money in</th>
              <th class="p-2 text-right">Balance</th>
              <th class="p-2">Classification / account</th>
              <th class="p-2">Posting</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="line in visibleLines"
              :id="`line-${line.name}`"
              :key="line.name"
              class="border-b"
              :class="
                route.query.transaction === line.name ? 'bg-yellow-50' : ''
              "
            >
              <td class="p-2 whitespace-nowrap">
                {{ line.transaction_date }}<br /><span class="text-xs">{{
                  line.reference
                }}</span>
              </td>
              <td class="p-2 min-w-64">
                {{ line.description }}
                <p class="text-xs text-gray-500">
                  {{ line.source_file }} · row {{ line.source_row
                  }}<span v-if="line.source_page">
                    · page {{ line.source_page }}</span
                  >
                </p>
                <details
                  v-if="line.review_note || line.source_data"
                  class="text-xs mt-2"
                >
                  <summary class="cursor-pointer underline">
                    Allocation and review details
                  </summary>
                  <p class="whitespace-pre-wrap my-2">{{ line.review_note }}</p>
                  <pre v-if="line.source_data" class="whitespace-pre-wrap">{{
                    line.source_data
                  }}</pre>
                </details>
              </td>
              <td class="p-2 text-right">{{ money(line.money_out) }}</td>
              <td class="p-2 text-right">{{ money(line.money_in) }}</td>
              <td class="p-2 text-right">{{ money(line.running_balance) }}</td>
              <td class="p-2 min-w-64">
                <template v-if="batch.status === 'Draft'"
                  ><select
                    v-model="line.classification"
                    class="border p-1"
                    aria-label="Classification"
                  >
                    <option
                      v-for="c in [
                        'Business',
                        'Personal',
                        'Transfer',
                        'Review',
                      ]"
                      :key="c"
                    >
                      {{ c }}
                    </option></select
                  ><select
                    v-model="line.offset_account"
                    class="border p-1 w-full"
                    aria-label="Category"
                  >
                    <option value="">Select account</option>
                    <option
                      v-for="a in accountOptions"
                      :key="a.name"
                      :value="a.name"
                    >
                      {{ a.name }}
                    </option>
                  </select></template
                >
                <template v-else
                  >{{ line.classification }}<br />{{
                    line.offset_account
                  }}</template
                >
              </td>
              <td class="p-2">
                <RouterLink
                  v-if="line.offset_account && batch.status !== 'Draft'"
                  :to="ledgerLink(line)"
                  class="underline"
                  >Category ledger</RouterLink
                >
                <RouterLink
                  v-if="
                    batch.status !== 'Draft' &&
                    (Number(line.money_out) || Number(line.money_in))
                  "
                  :to="ledgerLink(line, true)"
                  class="block underline mt-2"
                  >Bank ledger</RouterLink
                >
                <span v-if="!Number(line.money_out) && !Number(line.money_in)"
                  >Bank memo — no cash movement</span
                >
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
    <template v-else-if="!busy">
      <section class="border rounded p-4 mb-6">
        <h2 class="font-semibold mb-2">Upload a statement batch</h2>
        <p class="mb-3">
          Each upload keeps the original bank lines together. Review the
          categories, then post the batch once.
        </p>
        <button class="underline mb-3" @click="template">
          Download CSV template
        </button>
        <div class="grid grid-cols-2 gap-3">
          <label
            >Statement name<input
              v-model="title"
              class="border rounded p-2 w-full"
          /></label>
          <label
            >Bank account<select
              v-model="bankAccount"
              class="border rounded p-2 w-full"
            >
              <option value="">Select bank</option>
              <option v-for="a in bankAccounts" :key="a.name" :value="a.name">
                {{ a.name }}
              </option>
            </select></label
          >
          <label
            >Opening balance<input
              v-model="opening"
              type="number"
              step="0.01"
              class="border rounded p-2 w-full"
          /></label>
          <label
            >Closing balance<input
              v-model="closing"
              type="number"
              step="0.01"
              class="border rounded p-2 w-full"
          /></label>
          <label class="col-span-2"
            >Statement CSV<input
              type="file"
              accept=".csv"
              class="block my-2"
              @change="pickFile"
          /></label>
        </div>
        <button
          class="border rounded px-3 py-2 mt-3"
          :disabled="busy || !file || !title || !bankAccount"
          @click="upload"
        >
          Upload and review
        </button>
        <p class="text-sm mt-2">
          Dates use YYYY-MM-DD. Personal and transfer lines should use the
          owner's personal account. Opening balances must already be in the
          ledger; this upload posts statement movements.
        </p>
      </section>
      <table class="w-full">
        <thead>
          <tr class="text-left">
            <th>Statement</th>
            <th>Bank</th>
            <th>Period</th>
            <th>Closing</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="b in batches" :key="b.name" class="border-b">
            <td class="py-3">
              <RouterLink
                :to="`/bank-statements/${b.name}`"
                class="underline"
                >{{ b.title }}</RouterLink
              >
            </td>
            <td>{{ b.bank_account }}</td>
            <td>{{ b.from_date }} – {{ b.to_date }}</td>
            <td>{{ money(b.closing_balance) }}</td>
            <td>{{ b.status }}</td>
          </tr>
        </tbody>
      </table>
    </template>
  </div>
</template>
<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';
import { RouterLink, useRoute, useRouter } from 'vue-router';
import { call } from 'src/web/api';
import { fyo } from 'src/initFyo';
interface Line {
  name: string;
  transaction_date: string;
  reference: string;
  description: string;
  money_out: number;
  money_in: number;
  running_balance: number;
  classification: string;
  offset_account: string;
  source_file: string;
  source_row: number;
  source_page: string;
  review_note?: string;
  source_data?: string;
}
interface Batch {
  name: string;
  title: string;
  bank_account: string;
  from_date: string;
  to_date: string;
  opening_balance: number;
  closing_balance: number;
  status: string;
  source_attachment: string;
  lines: Line[];
}
const route = useRoute();
const router = useRouter();
const batches = ref<Batch[]>([]);
const batch = ref<Batch | null>(null);
const accountOptions = ref<{ name: string; account_type: string }[]>([]);
const busy = ref(false);
const error = ref('');
const search = ref('');
const title = ref('');
const bankAccount = ref('');
const opening = ref('0');
const closing = ref('0');
const file = ref<File | null>(null);
const bankAccounts = computed(() =>
  accountOptions.value.filter((a) => a.account_type === 'Bank')
);
const totalIn = computed(
  () => batch.value?.lines.reduce((n, l) => n + Number(l.money_in), 0) ?? 0
);
const totalOut = computed(
  () => batch.value?.lines.reduce((n, l) => n + Number(l.money_out), 0) ?? 0
);
const visibleLines = computed(
  () =>
    batch.value?.lines.filter((l) =>
      `${l.description} ${l.reference} ${l.offset_account}`
        .toLowerCase()
        .includes(search.value.toLowerCase())
    ) ?? []
);
function money(value: number) {
  return new Intl.NumberFormat('en-ZA', {
    style: 'currency',
    currency: String(fyo.singles.SystemSettings?.currency || 'ZAR'),
  }).format(Number(value));
}
function ledgerLink(line: Line, bank = false) {
  return {
    path: '/report/GeneralLedger',
    query: {
      defaultFilters: JSON.stringify({
        account: bank ? batch.value!.bank_account : line.offset_account,
        fromDate: line.transaction_date,
        toDate: line.transaction_date,
        referenceType: 'All',
        bankTransaction: line.name,
        groupBy: 'none',
      }),
    },
  };
}
async function run(action: () => Promise<void>) {
  busy.value = true;
  error.value = '';
  try {
    await action();
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  } finally {
    busy.value = false;
  }
}
async function load() {
  await run(async () => {
    accountOptions.value = await call('frappe_books.bank_import.accounts');
    if (route.params.name) {
      batch.value = await call('frappe_books.bank_import.get_batch', {
        name: route.params.name,
      });
    } else {
      batch.value = null;
      batches.value = await call('frappe_books.bank_import.list_batches');
    }
  });
  await nextTick();
  if (route.query.transaction)
    document
      .getElementById(`line-${route.query.transaction}`)
      ?.scrollIntoView({ block: 'center' });
}
function pickFile(event: Event) {
  file.value = (event.target as HTMLInputElement).files?.[0] ?? null;
}
async function upload() {
  await run(async () => {
    const name = await call<string>('frappe_books.bank_import.upload', {
      title: title.value,
      bank_account: bankAccount.value,
      opening_balance: opening.value,
      closing_balance: closing.value,
      content: await file.value!.text(),
      filename: file.value!.name,
    });
    await router.push(`/bank-statements/${name}`);
  });
}
async function save() {
  await run(async () => {
    await call('frappe_books.bank_import.save_categories', {
      name: batch.value!.name,
      lines: batch.value!.lines.map((l) => ({
        name: l.name,
        offset_account: l.offset_account,
        classification: l.classification,
      })),
    });
  });
}
async function post() {
  await save();
  if (error.value) return;
  await run(async () => {
    await call('frappe_books.bank_import.post', { name: batch.value!.name });
  });
  if (!error.value) await load();
}
function template() {
  const blob = new Blob(
    [
      'date,description,money_out,money_in,balance,reference,account,classification\n',
    ],
    { type: 'text/csv' }
  );
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'bank-statement-template.csv';
  a.click();
  URL.revokeObjectURL(a.href);
}
watch(() => route.fullPath, load, { immediate: true });
</script>
