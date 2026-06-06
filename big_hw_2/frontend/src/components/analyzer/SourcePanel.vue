<script setup lang="ts">
const model = defineModel<string>({ required: true })

const emit = defineEmits<{
  (event: 'analyze'): void
  (event: 'load-example'): void
}>()

function onAnalyzeClick() {
  emit('analyze')
}

function onLoadExampleClick() {
  emit('load-example')
}
</script>

<template>
  <section class="source-panel">
    <header class="source-header">
      <div class="title-wrap">
        <p class="eyebrow">Source</p>
        <h2 class="panel-title">类 Rust 源代码</h2>
      </div>
      <div class="action-wrap">
        <button class="ghost-btn" type="button" @click="onLoadExampleClick">加载示例</button>
        <button class="primary-btn" type="button" @click="onAnalyzeClick">开始分析</button>
      </div>
    </header>

    <label class="source-label" for="source-input">输入代码</label>
    <textarea
      id="source-input"
      v-model="model"
      class="source-input"
      spellcheck="false"
      placeholder="在这里输入类 Rust 程序..."
    />
  </section>
</template>

<style scoped>
.source-panel {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(12, 52, 61, 0.2);
  border-radius: 24px;
  padding: 20px;
  box-shadow: 0 18px 40px rgba(14, 33, 43, 0.12);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.source-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.title-wrap {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.eyebrow {
  margin: 0;
  text-transform: uppercase;
  font-size: 12px;
  letter-spacing: 0.18em;
  color: #195b66;
}

.panel-title {
  margin: 0;
  font-size: 22px;
  font-family: 'Noto Serif SC', serif;
  color: #0b2a36;
}

.action-wrap {
  display: flex;
  gap: 8px;
}

.primary-btn,
.ghost-btn {
  font-family: 'IBM Plex Sans Condensed', sans-serif;
  border-radius: 999px;
  border: none;
  padding: 10px 16px;
  font-size: 14px;
  cursor: pointer;
  transition: transform 180ms ease, box-shadow 180ms ease, background 180ms ease;
}

.primary-btn {
  background: linear-gradient(120deg, #0f766e, #1d4ed8);
  color: #f8feff;
  box-shadow: 0 10px 20px rgba(24, 103, 143, 0.28);
}

.ghost-btn {
  background: #e3f4f3;
  color: #155e63;
}

.primary-btn:hover,
.ghost-btn:hover {
  transform: translateY(-1px);
}

.source-label {
  font-size: 13px;
  color: #24545d;
}

.source-input {
  width: 100%;
  min-height: 320px;
  resize: vertical;
  border-radius: 16px;
  border: 1px solid #9bc3cb;
  background: linear-gradient(160deg, #fafdff, #eef8fb);
  font-family: 'IBM Plex Mono', monospace;
  font-size: 14px;
  line-height: 1.56;
  color: #0f2633;
  padding: 14px;
  box-sizing: border-box;
}

.source-input:focus-visible {
  outline: 2px solid #2b7da7;
  outline-offset: 2px;
}

@media (max-width: 768px) {
  .source-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .action-wrap {
    width: 100%;
  }

  .primary-btn,
  .ghost-btn {
    flex: 1;
  }

  .source-input {
    min-height: 240px;
  }
}
</style>
