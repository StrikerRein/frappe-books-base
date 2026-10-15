<template>
  <section class="border rounded p-3 my-3 bg-blue-50">
    <div class="flex gap-3 items-center">
      <strong>{{ items.length }} selected for client review</strong>
      <button class="border rounded px-3 py-1" :disabled="!items.length || busy" @click="open">Assign client review</button>
      <button v-if="items.length" class="underline" @click="$emit('clear')">Clear selection</button>
    </div>
    <div v-if="opened" class="grid gap-3 mt-3">
      <label>Workflow template<select v-model="workflowTemplate" class="border rounded p-2 block w-full"><option v-for="t in workflowTemplates" :key="t.name" :value="t.name">{{ t.title }}</option></select></label>
      <label>Client<select v-model="client" class="border rounded p-2 block w-full"><option value="">Choose client</option><option v-for="c in clients" :key="c.email" :value="c.email">{{ c.label }}</option></select></label>
      <p v-if="!busy && !clients.length">No client has review access to this company. Configure access in the review desk.</p>
      <label>Question or instructions<textarea v-model="question" class="border rounded p-2 block w-full" maxlength="4000" placeholder="Please clarify this transaction and identify the business, private or mixed portion." /></label>
      <label>Tax year<input v-model.number="taxYear" type="number" min="2000" max="2100" class="border rounded p-2 block" /></label>
      <label>Due date (optional)<input v-model="due" type="date" class="border rounded p-2 block" /></label>
      <p>Clients can suggest an allocation and a business-use percentage. You review their answers before changing the books.</p>
      <button class="border rounded px-3 py-2 justify-self-start bg-white" :disabled="busy || !client || !question.trim() || !items.length || items.length > 50" @click="send">Send to client review inbox</button>
    </div>
    <p v-if="error" role="alert" class="text-red-700 mt-2">{{ error }}</p>
    <p v-if="message" role="status" class="mt-2">{{ message }}</p>
  </section>
</template>
<script setup lang="ts">
import { ref } from 'vue';
import { call } from 'src/web/api';
const props = defineProps<{ items: { kind: 'bank' | 'ledger'; name: string }[] }>();
const emit = defineEmits<{ clear: [] }>();
const clients = ref<{ email: string; label: string }[]>([]);
const client = ref('');
const workflowTemplate = ref('Transaction clarification');
const workflowTemplates = ref<{ name: string; title: string; enabled: number }[]>([]);
const question = ref('');
const due = ref('');
const taxYear = ref(2026);
const opened = ref(false);
const busy = ref(false);
const error = ref('');
const message = ref('');
async function open() {
  opened.value = true; error.value = ''; message.value = ''; busy.value = true;
  try {
    clients.value = await call('frappe_books.review_bridge.clients');
    const workspace = await call<{ templates: { name: string; title: string; enabled: number }[] }>('frappe_books.review_bridge.workflow', { operation: 'workspace' });
    workflowTemplates.value = workspace.templates.filter(t => t.enabled);
    if (clients.value.length === 1) client.value = clients.value[0].email;
  } catch (e) { error.value = e instanceof Error ? e.message : String(e); }
  finally { busy.value = false; }
}
async function send() {
  busy.value = true; error.value = ''; message.value = '';
  try {
    const names = await call<string[]>('frappe_books.review_bridge.assign', {
      client: client.value, question: question.value, due_date: due.value, items: props.items, workflow_template: workflowTemplate.value, tax_year: taxYear.value,
    });
    message.value = `${names.length} review item(s) assigned. The client can now answer in their portal.`;
    opened.value = false; question.value = ''; emit('clear');
  } catch (e) { error.value = e instanceof Error ? e.message : String(e); }
  finally { busy.value = false; }
}
</script>
