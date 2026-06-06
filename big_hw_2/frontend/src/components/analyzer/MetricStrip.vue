<script setup lang="ts">
defineProps<{
  tokenCount: number
  lexErrorCount: number
  parseErrorCount: number
  semanticErrorCount: number
  loading: boolean
}>()
</script>

<template>
  <section class="metric-strip" aria-label="analysis metrics">
    <article class="metric-card accent-lex">
      <p class="metric-label">Token 数量</p>
      <p class="metric-value">{{ tokenCount }}</p>
    </article>
    <article class="metric-card accent-lex">
      <p class="metric-label">词法错误</p>
      <p class="metric-value">{{ lexErrorCount }}</p>
    </article>
    <article class="metric-card accent-syn">
      <p class="metric-label">语法错误</p>
      <p class="metric-value">{{ parseErrorCount }}</p>
    </article>
    <article class="metric-card accent-sem">
      <p class="metric-label">语义错误</p>
      <p class="metric-value">{{ semanticErrorCount }}</p>
    </article>
    <article class="metric-card status-card">
      <p class="metric-label">状态</p>
      <p class="metric-value">{{ loading ? '分析中...' : '待命' }}</p>
    </article>
  </section>
</template>

<style scoped>
.metric-strip {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
}

.metric-card {
  border-radius: 16px;
  padding: 14px;
  background: rgba(250, 255, 255, 0.75);
  border: 1px solid rgba(19, 104, 116, 0.22);
  border-top: 3px solid transparent;
}

.accent-lex {
  border-top-color: #0e7490;
}

.accent-syn {
  border-top-color: #15803d;
}

.accent-sem {
  border-top-color: #b45309;
}

.metric-label {
  margin: 0;
  font-size: 12px;
  letter-spacing: 0.08em;
  color: #20616d;
}

.metric-value {
  margin: 4px 0 0;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 22px;
  color: #103745;
}

.status-card {
  background: linear-gradient(120deg, rgba(32, 139, 138, 0.2), rgba(31, 105, 160, 0.18));
}

@media (max-width: 980px) {
  .metric-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
