<template>
  <main class="h-full overflow-auto p-5 text-ink-gray-8">
    <div class="flex justify-between items-center mb-3"><h1 class="text-xl font-semibold">Workflows</h1><button class="border rounded px-3 py-2" :disabled="busy" @click="load">Refresh</button></div>
    <p class="mb-4">Manage client questions, transaction clarification and tax reviews through reusable stages.</p>
    <p v-if="error" role="alert" class="bg-red-50 text-red-700 p-3 mb-3">{{ error }}</p>
    <p v-if="message" role="status" class="bg-green-50 p-3 mb-3">{{ message }}</p>
    <div class="flex gap-3 mb-4"><button class="border rounded px-3 py-2" @click="tab = 'work'">Client workflows</button><button class="border rounded px-3 py-2" @click="tab = 'templates'">Workflow templates</button></div>
    <template v-if="data && tab === 'work'">
      <details class="border rounded p-4 mb-5"><summary class="font-semibold cursor-pointer">Start a workflow</summary>
        <div class="grid sm:grid-cols-2 gap-3 mt-3">
          <label>Template<select v-model="newCase.template" class="field"><option v-for="t in data.templates.filter(t => t.enabled)" :key="t.name" :value="t.name">{{ t.title }} · {{ t.topic }}</option></select></label>
          <label>Client<select v-model="newCase.client" class="field"><option value="">Choose client</option><option v-for="c in eligibleClients" :key="c.email" :value="c.email">{{ c.label }}</option></select></label>
          <label>Company<select v-model="newCase.source_site" class="field"><option v-for="(label, site) in data.sources" :key="site" :value="site">{{ label }}</option></select></label>
          <label>Workflow title<input v-model="newCase.title" class="field" maxlength="140" placeholder="e.g. FY2026 personal income tax review" /></label>
          <label>Due date (optional)<input v-model="newCase.due_date" type="date" class="field" /></label>
          <label>First client question (optional)<textarea v-model="newCase.question" class="field" maxlength="4000" placeholder="Leave empty to prepare a draft workflow." /></label>
        </div><button class="button mt-3" :disabled="busy || !newCase.client || !newCase.title" @click="act('create', newCase, 'Workflow created.')">Create workflow</button>
      </details>
      <label class="block mb-3">Find a workflow<input v-model="search" class="field" placeholder="Search client, title, company or topic" /></label>
      <p v-if="!filteredCases.length" class="p-5 border rounded">No workflows yet. Start one above, or assign selected bank or ledger items to a client.</p>
      <section v-for="w in filteredCases" :key="w.name" class="border rounded p-4 mb-4">
        <div class="flex justify-between gap-3"><h2 class="font-semibold text-lg">{{ w.title }}</h2><span class="rounded bg-blue-50 px-3 py-1">{{ w.stage }}</span></div>
        <p class="text-sm my-2">{{ w.name }} · {{ w.topic }} · {{ w.company }} · {{ clientName(w.client) }} <span v-if="w.due_date">· Due {{ w.due_date }}</span></p>
        <ol class="flex flex-wrap gap-2 my-3"><li v-for="s in w.stages" :key="s.name" class="rounded border px-2 py-1 text-sm" :class="s.name === w.stage ? 'bg-blue-50 font-semibold' : ''">{{ s.name }}</li></ol>
        <details class="mb-3"><summary class="cursor-pointer underline">Questions and review tasks ({{ w.tasks.length }})</summary>
          <article v-for="task in w.tasks" :key="task.name" class="bg-gray-50 rounded p-3 mt-3">
            <p class="font-semibold">{{ task.question }}</p><p class="text-sm my-2">{{ task.name }} · {{ task.status }}</p>
            <p v-if="task.answer" class="whitespace-pre-wrap">{{ task.answer }}</p>
            <p v-if="task.answer && task.kind === 'Transaction'" class="text-sm mt-2">Suggested use: {{ task.classification }} <span v-if="task.classification === 'Mixed'">· {{ task.percentage }}% business/rental</span> · {{ task.suggested_category }}</p>
            <label v-if="task.status !== 'Reviewed'" class="block mt-3">Accountant review note<textarea v-model="taskNotes[task.name]" class="field" maxlength="4000" /></label>
            <div v-if="task.status !== 'Reviewed'" class="flex gap-2 mt-2"><button class="button" :disabled="busy || task.status !== 'Answered' || !taskNotes[task.name]" @click="reviewTask(task, 'Reviewed')">Complete task review</button><button class="button" :disabled="busy || !taskNotes[task.name]" @click="reviewTask(task, 'Follow-up')">Ask for clarification</button></div>
            <p v-if="task.review_note" class="text-sm mt-2">Review note: {{ task.review_note }}</p>
          </article>
        </details>
        <details v-if="!complete(w)" class="mb-3"><summary class="cursor-pointer underline">Add a client question</summary><textarea v-model="questions[w.name]" class="field" maxlength="4000" /><button class="button mt-2" :disabled="busy || !questions[w.name]" @click="act('add_question', { name: w.name, question: questions[w.name], expected_modified: w.modified }, 'Question assigned.')">Assign question</button></details>
        <label>Stage-change note<textarea v-model="notes[w.name]" class="field" maxlength="4000" placeholder="Record why this workflow is moving forward." /></label>
        <button class="button mt-2" :disabled="busy || !notes[w.name]" @click="act('advance', { name: w.name, note: notes[w.name], expected_modified: w.modified, reopen: complete(w) }, complete(w) ? 'Workflow reopened.' : 'Workflow stage updated.')">{{ complete(w) ? 'Reopen for accountant review' : 'Move to next stage' }}</button>
        <details class="mt-3"><summary class="cursor-pointer underline">Workflow history</summary><p v-for="(h, i) in w.history" :key="i" class="text-sm border-b py-2">{{ h.at }} · {{ h.by }} · {{ h.action }} <span v-if="h.to_stage">→ {{ h.to_stage }}</span><br />{{ h.note }}</p></details>
      </section>
    </template>
    <template v-if="data && tab === 'templates'">
      <p class="mb-3">Rename stages and add further accountant review stages. Changes apply to new workflows; existing workflows keep their original stages.</p>
      <div class="flex flex-wrap gap-2 mb-4"><button class="button" @click="editTemplate()">New template</button><button v-for="t in data.templates" :key="t.name" class="button" @click="editTemplate(t)">{{ t.title }}</button></div>
      <section class="border rounded p-4"><label>Template name<input v-model="template.title" class="field" :disabled="!!template.name" maxlength="100" /></label><label class="block mt-3">Topic<input v-model="template.topic" class="field" maxlength="100" /></label>
        <div v-for="(stage, i) in template.stage_list" :key="i" class="flex gap-3 items-end my-3"><label class="flex-1">Stage {{ i + 1 }}<input v-model="stage.name" class="field" maxlength="100" /></label><p class="text-sm pb-2">{{ responsibilities[stage.role] }}</p><button v-if="stage.role === 'Review' && template.stage_list.filter(s => s.role === 'Review').length > 1" class="button" @click="template.stage_list.splice(i, 1)">Remove</button></div>
        <div class="flex gap-3"><button class="button" @click="template.stage_list.splice(template.stage_list.length - 1, 0, { name: 'Additional review', role: 'Review' })">Add accountant review stage</button><button class="button" :disabled="busy || !template.title || !template.topic" @click="act('save_template', template, 'Template saved. Existing workflows keep their stages.')">Save template</button></div>
      </section>
    </template>
    <p class="text-sm mt-5">Completing a workflow records approval. Accounting allocations and tax submissions remain separate actions.</p>
  </main>
</template>
<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { call } from 'src/web/api';
type Stage = { name: string; role: string };
type Template = { name: string; title: string; topic: string; enabled: number; stages: string; modified: string };
type Task = { name: string; question: string; status: string; kind: string; answer: string; classification: string; percentage: number; suggested_category: string; review_note: string; modified: string };
type Workflow = { name: string; title: string; topic: string; client: string; company: string; due_date: string; stage: string; stages: Stage[]; modified: string; tasks: Task[]; history: { action: string; by: string; at: string; note?: string; to_stage?: string }[] };
type Workspace = { templates: Template[]; cases: Workflow[]; clients: { email: string; label: string; sources: string[] }[]; sources: Record<string, string> };
const defaults = () => [{ name: 'Draft', role: 'Draft' }, { name: 'Assigned', role: 'Assigned' }, { name: 'Client responded', role: 'Responded' }, { name: 'Accountant review', role: 'Review' }, { name: 'Complete', role: 'Complete' }];
const responsibilities: Record<string, string> = { Draft: 'Preparation', Assigned: 'Client action', Responded: 'Answers received', Review: 'Accountant approval', Complete: 'Finished' };
const data = ref<Workspace>(); const tab = ref('work'); const busy = ref(false); const error = ref(''); const message = ref(''); const search = ref('');
const notes = ref<Record<string, string>>({}); const questions = ref<Record<string, string>>({}); const taskNotes = ref<Record<string, string>>({});
const newCase = ref({ template: 'Tax review', client: '', source_site: '', title: '', due_date: '', question: '' });
const template = ref({ name: '', title: '', topic: '', expected_modified: '', stage_list: defaults() });
const eligibleClients = computed(() => data.value?.clients.filter(c => c.sources.includes(newCase.value.source_site)) || []);
watch(() => newCase.value.source_site, () => { newCase.value.client = eligibleClients.value.length === 1 ? eligibleClients.value[0].email : ''; });
const filteredCases = computed(() => data.value?.cases.filter(w => `${w.title} ${w.topic} ${w.company} ${clientName(w.client)}`.toLowerCase().includes(search.value.toLowerCase())) || []);
function clientName(email: string) { return data.value?.clients.find(c => c.email === email)?.label || email; }
function complete(w: Workflow) { return w.stages.find(s => s.name === w.stage)?.role === 'Complete'; }
function editTemplate(t?: Template) { template.value = t ? { name: t.name, title: t.title, topic: t.topic, expected_modified: t.modified, stage_list: JSON.parse(t.stages) } : { name: '', title: '', topic: '', expected_modified: '', stage_list: defaults() }; }
async function load() { busy.value = true; error.value = ''; try { data.value = await call('frappe_books.review_bridge.workflow', { operation: 'workspace' }); if (!newCase.value.source_site) newCase.value.source_site = Object.keys(data.value!.sources)[0] || ''; } catch (e) { error.value = e instanceof Error ? e.message : String(e); } finally { busy.value = false; } }
async function act(operation: string, values: unknown, success: string) { busy.value = true; error.value = ''; message.value = ''; try { await call('frappe_books.review_bridge.workflow', { operation, values }); await load(); message.value = success; if (operation === 'create') { newCase.value.title = ''; newCase.value.question = ''; } if (operation === 'save_template') editTemplate(); } catch (e) { error.value = e instanceof Error ? e.message : String(e); } finally { busy.value = false; } }
async function reviewTask(task: Task, action: string) { await act('review_task', { name: task.name, action, note: taskNotes.value[task.name], expected_modified: task.modified }, action === 'Reviewed' ? 'Task reviewed. No accounting entries were changed.' : 'Clarification requested.'); }
onMounted(load);
</script>
<style scoped>
.field { display: block; border: 1px solid #cbd5e1; border-radius: 6px; padding: 9px; width: 100%; margin-top: 5px; }
.button { border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 12px; background: white; }
button:disabled { opacity: .5; }
</style>
