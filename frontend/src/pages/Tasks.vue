<template>
  <div>
    <h1 class="brand">任务</h1>
    <p class="muted">dirty/负权任务照常展示，但生成与对调不会引用；回洗须把权重修正为正数</p>
    <form @submit.prevent="add">
      <input v-model="title" placeholder="任务名" />
      <button type="submit">添加</button>
    </form>
    <p v-if="err" class="err">{{ err }}</p>
    <ul class="list">
      <li v-for="t in rows" :key="t.id">
        <strong>{{ t.title }}</strong>
        <span class="muted"> · 权重 {{ t.weight }} · </span>
        <span class="chip" :class="{ bad: t.data_quality !== 'clean' || t.weight <= 0 }">{{ t.data_quality }}</span>
        <template v-if="t.data_quality === 'clean' && t.weight > 0">
          <button class="ghost" style="margin-left:8px" @click="isolate(t.id)">隔离</button>
        </template>
        <template v-else>
          <input type="number" min="1" style="width:70px;display:inline-block;margin:0 4px" v-model.number="weights[t.id]" placeholder="权重" />
          <button @click="backwash(t)">现行回洗</button>
        </template>
      </li>
    </ul>
    <p v-if="note" class="muted">{{ note }}</p>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'
const rows = ref([])
const title = ref('')
const err = ref('')
const note = ref('')
const weights = ref({})
async function load() {
  rows.value = await api('/tasks')
  for (const t of rows.value) {
    if (!(t.id in weights.value)) weights.value[t.id] = t.weight > 0 ? t.weight : 1
  }
}
async function add() {
  if (!title.value.trim()) return
  await api('/tasks', { method: 'POST', body: JSON.stringify({ title: title.value }) })
  title.value = ''; await load()
}
async function isolate(id) {
  err.value = ''; note.value = ''
  try {
    const r = await api('/tasks/' + id + '/isolate', { method: 'POST', body: '{}' })
    note.value = `已隔离，闩锁历史异常格 ${r.latched_cells} 个`
    await load()
  } catch (e) { err.value = e.message }
}
async function backwash(t) {
  err.value = ''; note.value = ''
  try {
    const r = await api('/tasks/' + t.id + '/backwash', {
      method: 'POST',
      body: JSON.stringify({ weight: weights.value[t.id] }),
    })
    note.value = r.residual_anomaly_cells
      ? `已回洗，仅新生成可纳入；仍有 ${r.residual_anomaly_cells} 个历史异常格，请到看板走历史格回洗`
      : '已回洗，新生成即可纳入'
    await load()
  } catch (e) { err.value = e.message }
}
onMounted(load)
</script>
