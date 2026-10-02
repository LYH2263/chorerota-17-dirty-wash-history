<template>
  <div>
    <h1 class="brand">成员</h1>
    <p class="muted">dirty/停用成员照常展示，但生成与对调不会引用；回洗后仅新生成可纳入</p>
    <form @submit.prevent="add">
      <input v-model="name" placeholder="新成员姓名" />
      <button type="submit">添加</button>
    </form>
    <p v-if="err" class="err">{{ err }}</p>
    <ul class="list">
      <li v-for="m in rows" :key="m.id">
        <strong>{{ m.name }}</strong>
        <span class="muted"> · {{ m.active ? '在岗' : '停用' }} · </span>
        <span class="chip" :class="{ bad: m.data_quality !== 'clean' }">{{ m.data_quality }}</span>
        <button v-if="m.data_quality === 'clean'" class="ghost" style="margin-left:8px" @click="isolate(m.id)">隔离</button>
        <button v-else style="margin-left:8px" @click="backwash(m.id)">现行回洗</button>
      </li>
    </ul>
    <p v-if="note" class="muted">{{ note }}</p>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'
const rows = ref([])
const name = ref('')
const err = ref('')
const note = ref('')
async function load() { rows.value = await api('/members') }
async function add() {
  if (!name.value.trim()) return
  await api('/members', { method: 'POST', body: JSON.stringify({ name: name.value }) })
  name.value = ''; await load()
}
async function isolate(id) {
  err.value = ''; note.value = ''
  try {
    const r = await api('/members/' + id + '/isolate', { method: 'POST', body: '{}' })
    note.value = `已隔离，闩锁历史异常格 ${r.latched_cells} 个`
    await load()
  } catch (e) { err.value = e.message }
}
async function backwash(id) {
  err.value = ''; note.value = ''
  try {
    const r = await api('/members/' + id + '/backwash', { method: 'POST', body: JSON.stringify({ active: 1 }) })
    note.value = r.residual_anomaly_cells
      ? `已回洗，仅新生成可纳入；仍有 ${r.residual_anomaly_cells} 个历史异常格，请到看板走历史格回洗`
      : '已回洗，新生成即可纳入'
    await load()
  } catch (e) { err.value = e.message }
}
onMounted(load)
</script>
