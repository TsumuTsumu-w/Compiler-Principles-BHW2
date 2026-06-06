<script setup lang="ts">
import { computed, shallowRef } from 'vue'

const props = defineProps<{
  astSummary: string
  astTree: string
  astJson: string
}>()

const mode = shallowRef<'summary' | 'tree' | 'json'>('summary')

const content = computed(() => {
  if (mode.value === 'tree') {
    return props.astTree
  }
  if (mode.value === 'json') {
    return props.astJson
  }
  return props.astSummary
})
</script>

<template>
  <section class="ast-panel">
    <header class="panel-header">
      <div class="header-left">
        <div class="phase-badge phase-syn">
          <span class="phase-step">2</span>
          <span class="phase-label">语法分析 Syntax Analysis</span>
        </div>
        <h3 class="panel-title">AST 视图</h3>
      </div>
      <div class="mode-switch">
        <button
          class="mode-btn"
          type="button"
          :class="{ active: mode === 'summary' }"
          @click="mode = 'summary'"
        >
          Summary
        </button>
        <button
          class="mode-btn"
          type="button"
          :class="{ active: mode === 'tree' }"
          @click="mode = 'tree'"
        >
          Tree
        </button>
        <button
          class="mode-btn"
          type="button"
          :class="{ active: mode === 'json' }"
          @click="mode = 'json'"
        >
          JSON
        </button>
      </div>
    </header>

    <pre class="ast-content">{{ content || '暂无 AST 数据' }}</pre>
  </section>
</template>

<style scoped>
.ast-panel {
  border-radius: 22px;
  background: rgba(254, 255, 251, 0.92);
  border: 1px solid rgba(54, 99, 58, 0.22);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 340px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 10px;
  flex-wrap: wrap;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.phase-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border-radius: 999px;
  padding: 5px 14px 5px 5px;
  width: fit-content;
}

.phase-syn {
  background: linear-gradient(135deg, #15803d, #166534);
  color: #ecfdf5;
}

.phase-step {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.25);
  font-family: 'IBM Plex Mono', monospace;
  font-size: 13px;
  font-weight: 600;
}

.phase-label {
  font-family: 'IBM Plex Sans Condensed', sans-serif;
  font-size: 13px;
  font-weight: 500;
  letter-spacing: 0.04em;
}

.panel-title {
  margin: 0;
  font-family: 'Noto Serif SC', serif;
  font-size: 20px;
  color: #1f3e26;
}

.mode-switch {
  display: flex;
  gap: 6px;
}

.mode-btn {
  border: 1px solid #98c59d;
  background: #edf9ef;
  color: #255430;
  border-radius: 999px;
  padding: 7px 12px;
  font-family: 'IBM Plex Sans Condensed', sans-serif;
  cursor: pointer;
}

.mode-btn.active {
  background: #2d7d4f;
  border-color: #2d7d4f;
  color: #f4fff4;
}

.ast-content {
  margin: 0;
  border-radius: 14px;
  background: #f3f9f1;
  border: 1px solid #cfe5d1;
  padding: 12px;
  min-height: 260px;
  max-height: 520px;
  overflow: auto;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 12px;
  line-height: 1.5;
  color: #1f4f29;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
