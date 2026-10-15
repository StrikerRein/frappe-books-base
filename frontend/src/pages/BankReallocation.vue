<template>
  <div class="h-full overflow-auto p-5 text-ink-gray-8">
    <div class="flex justify-between mb-4">
      <h1 class="text-xl font-semibold">Bulk reallocate bank transactions</h1>
      <RouterLink to="/bank-statements" class="underline"
        >Bank statements</RouterLink
      >
    </div>
    <p class="mb-4">
      Select transactions across statement batches and move them to a new
      category. The original bank amounts and balances remain unchanged.
    </p>
    <p v-if="error" role="alert" class="bg-red-50 text-red-700 p-3 my-3">
      {{ error }}
    </p>
    <p v-if="success" role="status" class="bg-green-50 p-3 my-3">
      {{ success }}
    </p>
    <div class="grid grid-cols-4 gap-3 mb-4">
      <label
        >From date<input
          v-model="fromDate"
          type="date"
          class="border rounded p-2 w-full"
      /></label>
      <label
        >To date<input
          v-model="toDate"
          type="date"
          class="border rounded p-2 w-full"
      /></label>
      <label
        >Current category<select
          v-model="currentAccount"
          class="border rounded p-2 w-full"
        >
          <option value="">All categories</option>
          <option v-for="a in accounts" :key="a.name" :value="a.name">
            {{ a.name }}
          </option>
        </select></label
      >
      <label
        >Bank description<input
          v-model="search"
          class="border rounded p-2 w-full"
          placeholder="e.g. bank fee or supplier"
      /></label>
    </div>
    <button
      class="border rounded px-3 py-2 mb-4"
      :disabled="busy"
      @click="load"
    >
      Find transactions
    </button>
    <p v-if="hasMore" class="mb-3">
      Showing the first 5,000 results. Narrow the filters before selecting
      transactions.
    </p>
    <section class="border rounded p-4 mb-4 bg-surface-gray-1">
      <p class="font-semibold mb-3">
        {{ selected.length }} selected · Money out {{ money(selectedOut) }} ·
        Money in {{ money(selectedIn) }}
      </p>
      <div class="grid grid-cols-3 gap-3">
        <label
          >New category<select
            v-model="targetAccount"
            class="border rounded p-2 w-full"
          >
            <option value="">Choose category</option>
            <option v-for="a in categoryAccounts" :key="a.name" :value="a.name">
              {{ a.name }}
            </option>
          </select></label
        >
        <label
          >New classification<select
            v-model="classification"
            class="border rounded p-2 w-full"
          >
            <option
              v-for="c in [
                'Business',
                'Personal',
                'Transfer',
                'Review',
                'Mixed spend',
              ]"
              :key="c"
            >
              {{ c }}
            </option>
          </select></label
        >
        <label
          >Reason for reallocation<input
            v-model="reason"
            class="border rounded p-2 w-full"
            placeholder="Explain the category correction"
        /></label>
      </div>
      <div
        v-if="classification === 'Mixed spend'"
        class="grid grid-cols-2 gap-3 my-3"
      >
        <label
          >Business-use percentage<input
            v-model.number="businessPercentage"
            type="number"
            min="0.01"
            max="99.99"
            step="0.01"
            class="border rounded p-2 w-full"
        /></label>
        <label
          >Personal portion account<select
            v-model="personalAccount"
            class="border rounded p-2 w-full"
          >
            <option value="">Choose owner/personal account</option>
            <option v-for="a in personalAccounts" :key="a.name" :value="a.name">
              {{ a.name }}
            </option>
          </select></label
        >
        <p class="col-span-2">
          Business:
          <strong
            >{{ businessPercentage }}% · {{ money(businessAmount) }}</strong
          >
          to {{ targetAccount || 'the chosen category' }}. Personal:
          <strong
            >{{ (100 - Number(businessPercentage)).toFixed(2) }}% ·
            {{ money(selectedOut - businessAmount) }}</strong
          >
          to {{ personalAccount || 'the personal account' }}.
        </p>
        <p v-if="selectedIn > 0" class="col-span-2 text-red-700">
          Mixed spend applies to payments. Deselect receipts before applying a
          split.
        </p>
      </div>
      <button
        v-if="!reviewing"
        class="border rounded px-3 py-2 mt-3"
        :disabled="
          busy ||
          !selected.length ||
          !targetAccount ||
          !reason.trim() ||
          (classification === 'Mixed spend' &&
            (!personalAccount ||
              selectedIn > 0 ||
              Number(businessPercentage) <= 0 ||
              Number(businessPercentage) >= 100))
        "
        @click="reviewing = true"
      >
        Review changes
      </button>
      <div v-else class="mt-3">
        <p>
          Move {{ selected.length }} selected transactions to
          <strong>{{ targetAccount }}</strong> ({{ classification }}). Reports
          will use their original transaction dates.
        </p>
        <p v-if="classification === 'Mixed spend'">
          Business {{ money(businessAmount) }}; personal
          {{ money(selectedOut - businessAmount) }} to {{ personalAccount }}.
        </p>
        <button
          class="border rounded bg-blue-50 px-3 py-2 mt-2 me-2"
          :disabled="busy"
          @click="apply"
        >
          Apply reallocation
        </button>
        <button class="underline" :disabled="busy" @click="reviewing = false">
          Back to selection
        </button>
      </div>
    </section>
    <p v-if="busy">Working…</p>
    <div class="overflow-auto">
      <table class="w-full text-sm tabular-nums">
        <thead>
          <tr class="border-b text-left">
            <th class="p-2">
              <input
                type="checkbox"
                aria-label="Select all matching transactions"
                :checked="allSelected"
                :disabled="busy || !rows.length"
                @change="selectAll"
              />
            </th>
            <th class="p-2">Date / reference</th>
            <th class="p-2">Bank description</th>
            <th class="p-2">Statement</th>
            <th class="p-2 text-right">Money out</th>
            <th class="p-2 text-right">Money in</th>
            <th class="p-2">Current category</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in rows"
            :key="row.name"
            class="border-b"
            :class="selected.includes(row.name) ? 'bg-yellow-50' : ''"
          >
            <td class="p-2">
              <input
                v-model="selected"
                type="checkbox"
                :value="row.name"
                :aria-label="`Select ${row.reference}`"
                :disabled="busy"
                @change="reviewing = false"
              />
            </td>
            <td class="p-2 whitespace-nowrap">
              {{ row.transaction_date }}<br />{{ row.reference }}
            </td>
            <td class="p-2 min-w-64">{{ row.description }}</td>
            <td class="p-2">
              <RouterLink
                :to="{
                  path: `/bank-statements/${row.parent}`,
                  query: { transaction: row.name },
                }"
                class="underline"
                >{{ row.parent }}</RouterLink
              >
            </td>
            <td class="p-2 text-right">{{ money(row.money_out) }}</td>
            <td class="p-2 text-right">{{ money(row.money_in) }}</td>
            <td class="p-2 min-w-64">
              {{ row.offset_account }}<br /><span class="text-xs">{{
                row.classification
              }}</span>
              <p v-if="row.classification === 'Mixed spend'">
                {{ row.business_percentage }}% business ·
                {{ row.personal_account }} personal remainder
              </p>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <p v-if="!busy && !rows.length">
      No bank transactions match these filters.
    </p>
  </div>
</template>
<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { RouterLink, useRoute } from 'vue-router';
import { call } from 'src/web/api';
import { fyo } from 'src/initFyo';
interface Account {
  name: string;
  account_type: string;
  root_type: string;
}
interface Row {
  business_percentage?: number;
  personal_account?: string;
  last_reallocation?: string;
  name: string;
  parent: string;
  transaction_date: string;
  reference: string;
  description: string;
  money_out: number;
  money_in: number;
  offset_account: string;
  classification: string;
}
const route = useRoute();
const accounts = ref<Account[]>([]);
const rows = ref<Row[]>([]);
const selected = ref<string[]>([]);
const fromDate = ref(String(route.query.fromDate ?? ''));
const toDate = ref(String(route.query.toDate ?? ''));
const currentAccount = ref(String(route.query.account ?? ''));
const search = ref('');
const targetAccount = ref('');
const classification = ref('Business');
const businessPercentage = ref(50);
const personalAccount = ref('');
const reason = ref('');
const reviewing = ref(false);
const busy = ref(false);
const hasMore = ref(false);
const error = ref('');
const success = ref('');
const categoryAccounts = computed(() =>
  accounts.value.filter((a) => a.account_type !== 'Bank')
);
const selectedRows = computed(() =>
  rows.value.filter((r) => selected.value.includes(r.name))
);
const personalAccounts = computed(() =>
  categoryAccounts.value.filter((a) =>
    ['Asset', 'Liability', 'Equity'].includes(a.root_type)
  )
);
const businessAmount = computed(() =>
  selectedRows.value.reduce(
    (sum, row) =>
      sum +
      Math.round(
        ((Number(row.money_out) * Number(businessPercentage.value)) / 100 +
          Number.EPSILON) *
          100
      ) /
        100,
    0
  )
);
const selectedOut = computed(() =>
  selectedRows.value.reduce((n, r) => n + Number(r.money_out), 0)
);
const selectedIn = computed(() =>
  selectedRows.value.reduce((n, r) => n + Number(r.money_in), 0)
);
const allSelected = computed(
  () => rows.value.length > 0 && selected.value.length === rows.value.length
);
function money(n: number) {
  return new Intl.NumberFormat('en-ZA', {
    style: 'currency',
    currency: String(fyo.singles.SystemSettings?.currency || 'ZAR'),
  }).format(n);
}
async function load() {
  busy.value = true;
  error.value = '';
  selected.value = [];
  reviewing.value = false;
  try {
    accounts.value = await call('frappe_books.bank_import.accounts');
    if (route.query.rule && !reason.value) {
      const rule = await call<{ match_text: string; percentage: number; reason: string; from_date: string; to_date: string }>('frappe_books.review_bridge.workflow', { operation: 'allocation_rule', values: { name: String(route.query.rule) } });
      search.value = rule.match_text; businessPercentage.value = rule.percentage;
      reason.value = rule.reason; fromDate.value = rule.from_date; toDate.value = rule.to_date;
      classification.value = 'Mixed spend';
    }
    const result = await call<{ rows: Row[]; has_more: boolean }>(
      'frappe_books.bank_reallocation.transactions',
      {
        from_date: fromDate.value,
        to_date: toDate.value,
        account: currentAccount.value,
        search: search.value,
        transaction: String(route.query.transaction || ''),
      }
    );
    rows.value = result.rows;
    if (route.query.transaction && rows.value.length === 1) {
      const row = rows.value[0];
      selected.value = [row.name];
      if (row.classification === 'Mixed spend') {
        targetAccount.value = row.offset_account;
        businessPercentage.value = Number(row.business_percentage);
        personalAccount.value = row.personal_account || '';
      }
      classification.value =
        route.query.mixed || row.classification === 'Mixed spend'
          ? 'Mixed spend'
          : row.classification;
    }
    hasMore.value = result.has_more;
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  } finally {
    busy.value = false;
  }
}
function selectAll() {
  reviewing.value = false;
  if (rows.value.length > 1000) {
    error.value =
      'Narrow the filters to 1,000 or fewer transactions before selecting all.';
    return;
  }
  selected.value = allSelected.value ? [] : rows.value.map((r) => r.name);
}
async function apply() {
  busy.value = true;
  error.value = '';
  success.value = '';
  try {
    const result = await call<{ name: string; count: number }>(
      'frappe_books.bank_reallocation.reallocate',
      {
        transaction_ids: selected.value,
        target_account: targetAccount.value,
        classification: classification.value,
        reason: reason.value,
        business_percentage: Number(businessPercentage.value),
        personal_account: personalAccount.value,
        expected: selectedRows.value.map((row) => ({
          name: row.name,
          offset_account: row.offset_account,
          last_reallocation: row.last_reallocation,
        })),
      }
    );
    success.value = `${result.count} transactions reallocated. Change reference: ${result.name}.`;
    await load();
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  } finally {
    busy.value = false;
  }
}
watch(targetAccount, (name) => {
  if (classification.value === 'Mixed spend') {
    reviewing.value = false;
    return;
  }
  classification.value = ['Income', 'Expense'].includes(
    accounts.value.find((a) => a.name === name)?.root_type ?? ''
  )
    ? 'Business'
    : 'Personal';
  reviewing.value = false;
});
watch([classification, reason, businessPercentage, personalAccount], () => {
  reviewing.value = false;
});
void load();
</script>
