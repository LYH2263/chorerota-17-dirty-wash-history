<template>
  <div>
    <h1 class="brand">本周看板</h1>
    <p class="muted">周卡片网格 · round-robin 落位后可去「对调」申请交换 · 异常格只读，须显式历史格回洗</p>
    <div style="display:flex;gap:8px;margin:12px 0">
      <button @click="generate">生成周表</button>
      <button class="ghost" @click="load">刷新</button>
      <button v-if="anomalyCount" class="warn" @click="backwash">历史格回洗（{{ anomalyCount }}）</button>
    </div>
    <p v-if="err" class="err">{{ err }}</p>
    <p v-if="note" class="muted">{{ note }}</p>
    <div class="week-grid">
      <article v-for="d in days" :key="d" class="week-card">
        <header>Day {{ d }}</header>
        <div v-for="a in byDay(d)" :key="a.id" class="cell" :class="{ anomaly: a.anomaly }">
          <span class="chip">{{ a.task_title }}</span>
          <span class="chip coral">{{ a.member_name }}</span>
          <span v-if="a.anomaly" class="chip bad" title="历史脏引用：现行回洗不会改动此格，须历史格回洗或保持只读异常">⚠ 异常</span>
        </div>
        <p v-if="!byDay(d).length" class="muted">空</p>
      </article>
    </div>
  </div>
</template>
<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'
const assigns = ref([])
const days = [0,1,2,3,4,5,6]
const err = ref('')
const note = ref('')
const weekId = 1
const anomalyCount = computed(() => assigns.value.filter(a => a.anomaly).length)
function byDay(d) { return assigns.value.filter(a => a.day === d) }
async function load() {
  err.value = ''
  try {
    const b = await api('/weeks/' + weekId + '/board')
    assigns.value = b.assignments || []
  } catch (e) { err.value = e.message }
}
async function generate() {
  err.value = ''; note.value = ''
  try {
    const r = await api('/weeks/' + weekId + '/generate', { method: 'POST', body: '{}' })
    const s = r.skipped || { members: [], tasks: [] }
    if (s.members.length || s.tasks.length)
      note.value = `已隔离未引用：成员 ${s.members.join(',') || '无'} · 任务 ${s.tasks.join(',') || '无'}`
    await load()
  } catch (e) { err.value = e.message }
}
async function backwash() {
  err.value = ''; note.value = ''
  try {
    const r = await api('/weeks/' + weekId + '/backwash', { method: 'POST', body: '{}' })
    note.value = `历史格回洗完成：改写 ${r.rewritten} 格`
    await load()
  } catch (e) {
    // 任务仍脏时后端 409：须先去任务页做现行回洗
    err.value = typeof e.message === 'string' ? e.message : JSON.stringify(e.message)
  }
}
onMounted(load)
</script>
