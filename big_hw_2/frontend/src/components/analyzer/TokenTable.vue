<script setup lang="ts">
import { computed } from 'vue'
import type { TokenRow } from '../../types/analyzer'

const props = defineProps<{
  tokens: TokenRow[]
}>()

const visibleTokens = computed(() => props.tokens.slice(0, 400))
</script>

<template>
  <section class="token-panel">
    <header class="panel-header">
      <div class="phase-badge phase-lex">
        <span class="phase-step">1</span>
        <span class="phase-label">词法分析 Lexical Analysis</span>
      </div>
      <h3 class="panel-title">Token 序列</h3>
    </header>

    <div class="table-wrap">
      <table class="token-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Type</th>
            <th>Value</th>
            <th>Ln</th>
            <th>Col</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(item, index) in visibleTokens" :key="`${index}-${item.type}-${item.line}-${item.column}`">
            <td>{{ index + 1 }}</td>
            <td>{{ item.type }}</td>
            <td class="value-cell">{{ item.value || '∅' }}</td>
            <td>{{ item.line }}</td>
            <td>{{ item.column }}</td>
          </tr>
          <tr v-if="visibleTokens.length === 0">
            <td colspan="5" class="empty-row">暂无 Token 数据，先点击“开始分析”</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<style scoped>
.token-panel {
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(12, 56, 67, 0.2);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 340px;
}

.panel-header {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.panel-header {
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

.phase-lex {
  background: linear-gradient(135deg, #0e7490, #155e75);
  color: #ecfeff;
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
  color: #0f2f3b;
}

.table-wrap {
  overflow: auto;
  max-height: 520px;
}

.token-table {
  width: 100%;
  border-collapse: collapse;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 12px;
}

.token-table th {
  position: sticky;
  top: 0;
  background: #d3ecf4;
  color: #15404c;
  text-align: left;
  padding: 8px;
}

.token-table td {
  border-bottom: 1px solid #d6e8ee;
  padding: 8px;
  color: #12313c;
  vertical-align: top;
}

.value-cell {
  max-width: 220px;
  white-space: pre-wrap;
  word-break: break-word;
}

.empty-row {
  text-align: center;
  color: #567983;
  padding: 24px;
}
</style>
