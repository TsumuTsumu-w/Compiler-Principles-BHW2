<script setup lang="ts">
defineProps<{
  requestError: string
  lexErrors: string[]
  parseErrors: string[]
  semanticErrors: string[]
}>()
</script>

<template>
  <section class="error-panel">
    <header class="panel-header">
      <h3 class="panel-title">诊断信息</h3>
    </header>

    <p v-if="requestError" class="request-error">请求失败: {{ requestError }}</p>

    <div class="error-group">
      <h4 class="group-title">词法错误</h4>
      <ul v-if="lexErrors.length" class="error-list">
        <li v-for="(err, idx) in lexErrors" :key="`lex-${idx}-${err}`">{{ err }}</li>
      </ul>
      <p v-else class="empty-text">无</p>
    </div>

    <div class="error-group">
      <h4 class="group-title">语法错误</h4>
      <ul v-if="parseErrors.length" class="error-list">
        <li v-for="(err, idx) in parseErrors" :key="`parse-${idx}-${err}`">{{ err }}</li>
      </ul>
      <p v-else class="empty-text">无</p>
    </div>

    <div class="error-group">
      <h4 class="group-title">语义错误</h4>
      <ul v-if="semanticErrors.length" class="error-list">
        <li v-for="(err, idx) in semanticErrors" :key="`semantic-${idx}-${err}`">{{ err }}</li>
      </ul>
      <p v-else class="empty-text">无</p>
    </div>
  </section>
</template>

<style scoped>
.error-panel {
  border-radius: 22px;
  background: rgba(255, 252, 249, 0.93);
  border: 1px solid rgba(138, 83, 48, 0.28);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
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

.phase-sem {
  background: linear-gradient(135deg, #b45309, #92400e);
  color: #fffbeb;
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
  color: #5f3612;
}

.request-error {
  margin: 0;
  border-radius: 12px;
  padding: 10px;
  border: 1px solid #b7362f;
  background: #fff0eb;
  color: #9b261f;
  font-size: 13px;
}

.error-group {
  border-top: 1px dashed #d5ba9d;
  padding-top: 8px;
}

.group-title {
  margin: 0;
  font-size: 14px;
  color: #70401b;
}

.error-list {
  margin: 8px 0 0;
  padding-left: 18px;
  display: grid;
  gap: 6px;
  color: #72370e;
  font-size: 13px;
}

.empty-text {
  margin: 8px 0 0;
  color: #986741;
  font-size: 13px;
}
</style>
