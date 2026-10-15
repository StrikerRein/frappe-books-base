<template>
  <div class="h-full overflow-auto">
    <PageHeader title="Comparative workbook source" />
    <div class="p-6 space-y-4">
      <p v-if="error" role="alert">{{ error }}</p>
      <template v-if="source">
        <h2 class="text-xl font-semibold">{{ source.title }}</h2>
        <p>{{ source.from_date }} to {{ source.to_date }}</p>
        <p class="text-sm whitespace-pre-line">{{ source.notes }}</p>
        <p class="text-sm">These are reported comparison figures. They do not create General Ledger transactions.</p>
        <a class="text-blue-600 underline" :href="download">Download source: {{ source.source_file }}</a>
        <table class="w-full text-sm">
          <thead><tr class="border-b"><th class="p-3 text-left">Account</th><th class="p-3 text-right">Debit</th><th class="p-3 text-right">Credit</th><th class="p-3 text-left">Workbook cell</th></tr></thead>
          <tbody><tr v-for="row in source.rows" :key="row.account" class="border-b"><td class="p-3">{{ row.account }}</td><td class="p-3 text-right">{{ amount(Math.max(Number(row.balance), 0)) }}</td><td class="p-3 text-right">{{ amount(Math.max(-Number(row.balance), 0)) }}</td><td class="p-3">{{ row.source_cell }}</td></tr></tbody>
        </table>
      </template>
    </div>
  </div>
</template>
<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import PageHeader from 'src/components/PageHeader.vue';
import { call } from 'src/web/api';
interface Source { title: string; from_date: string; to_date: string; notes: string; source_file: string; rows: { account: string; balance: number; source_cell: string }[] }
const route = useRoute();
const source = ref<Source>();
const error = ref('');
const download = computed(() => `/api/method/frappe_books.reports.comparatives.download_source?name=${encodeURIComponent(String(route.params.name))}`);
const amount = (value: number) => value.toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
watch(() => [route.params.name, route.query.account], async () => {
  source.value = undefined;
  error.value = '';
  try {
    source.value = await call<Source>('frappe_books.reports.comparatives.get_source', { name: String(route.params.name), account: String(route.query.account ?? '') });
  } catch (e) { error.value = e instanceof Error ? e.message : 'Unable to load comparative source.'; }
}, { immediate: true });
</script>
