<script setup lang="ts">
import { computed, shallowRef } from 'vue'
import type { QuadRow, TokenRow } from '../../types/analyzer'

const props = defineProps<{
  tokens: TokenRow[]
  quads: QuadRow[]
  astSummary: string
  astTree: string
  astJson: string
  hasResult: boolean
  hasLexErrors: boolean
  hasParseErrors: boolean
  hasSemanticErrors: boolean
}>()

type Tab = 'lex' | 'syn' | 'sem'
const activeTab = shallowRef<Tab>('lex')

const showTokenTable = computed(() => props.hasResult && !props.hasLexErrors)
const showAst = computed(() => props.hasResult && !props.hasLexErrors && !props.hasParseErrors)
const showQuads = computed(
  () => props.hasResult && !props.hasLexErrors && !props.hasParseErrors && !props.hasSemanticErrors,
)

const visibleTokens = computed(() => props.tokens.slice(0, 400))
const visibleQuads = computed(() => props.quads)

const viewMode = shallowRef<'summary' | 'tree' | 'json'>('summary')

const astContent = computed(() => {
  if (viewMode.value === 'tree') return props.astTree
  if (viewMode.value === 'json') return props.astJson
  return props.astSummary
})
</script>

<template>
  <section class="analysis-panel">
    <!-- Tab bar -->
    <nav class="tab-bar">
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'lex', 'has-error': hasResult && hasLexErrors }"
        type="button"
        @click="activeTab = 'lex'"
      >
        <span class="tab-step">1</span>
        <span class="tab-label">词法分析</span>
      </button>
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'syn', 'has-error': hasResult && hasParseErrors && !hasLexErrors }"
        type="button"
        @click="activeTab = 'syn'"
      >
        <span class="tab-step">2</span>
        <span class="tab-label">语法分析</span>
      </button>
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'sem' }"
        type="button"
        @click="activeTab = 'sem'"
      >
        <span class="tab-step">3</span>
        <span class="tab-label">语义分析</span>
      </button>
    </nav>

    <!-- 词法分析 Tab -->
    <div v-show="activeTab === 'lex'" class="tab-body">
      <template v-if="showTokenTable">
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
                <td colspan="5" class="empty-row">暂无 Token 数据，先点击"开始分析"</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
      <div v-else-if="hasResult && hasLexErrors" class="skipped-card skip-lex">
        <span class="skip-step">1</span>
        <div>
          <p class="skip-title">词法分析 — 存在错误</p>
          <p class="skip-desc">请先修复左侧面板中的词法错误，再重新分析。</p>
        </div>
      </div>
      <div v-else class="empty-hint">暂无数据，请先运行分析</div>
    </div>

    <!-- 语法分析 Tab -->
    <div v-show="activeTab === 'syn'" class="tab-body">
      <template v-if="showAst">
        <div class="ast-toolbar">
          <div class="mode-switch">
            <button
              class="mode-btn"
              type="button"
              :class="{ active: viewMode === 'summary' }"
              @click="viewMode = 'summary'"
            >Summary</button>
            <button
              class="mode-btn"
              type="button"
              :class="{ active: viewMode === 'tree' }"
              @click="viewMode = 'tree'"
            >Tree</button>
            <button
              class="mode-btn"
              type="button"
              :class="{ active: viewMode === 'json' }"
              @click="viewMode = 'json'"
            >JSON</button>
          </div>
        </div>
        <pre class="ast-content">{{ astContent || '暂无 AST 数据' }}</pre>
      </template>
      <div v-else-if="hasResult && hasParseErrors && !hasLexErrors" class="skipped-card skip-syn">
        <span class="skip-step">2</span>
        <div>
          <p class="skip-title">语法分析 — 存在错误</p>
          <p class="skip-desc">请先修复左侧面板中的语法错误，再重新分析。</p>
        </div>
      </div>
      <div v-else-if="hasResult && hasLexErrors" class="skipped-card skip-lex">
        <span class="skip-step">1</span>
        <div>
          <p class="skip-title">词法分析 — 存在错误</p>
          <p class="skip-desc">请先修复词法错误后，语法分析才能进行。</p>
        </div>
      </div>
      <div v-else class="empty-hint">暂无数据，请先运行分析</div>
    </div>

    <!-- 语义分析 Tab -->
    <div v-show="activeTab === 'sem'" class="tab-body sem-tab">
      <template v-if="showQuads">
        <div class="table-wrap">
          <table class="token-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Op</th>
                <th>Arg1</th>
                <th>Arg2</th>
                <th>Result</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in visibleQuads" :key="`quad-${item.index}-${item.op}-${item.result}`">
                <td>{{ item.index }}</td>
                <td>{{ item.op }}</td>
                <td class="value-cell">{{ item.arg1 || '-' }}</td>
                <td class="value-cell">{{ item.arg2 || '-' }}</td>
                <td class="value-cell">{{ item.result || '-' }}</td>
              </tr>
              <tr v-if="visibleQuads.length === 0">
                <td colspan="5" class="empty-row">暂无四元组中间代码</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
      <div v-else-if="hasResult && hasLexErrors" class="skipped-card skip-lex">
        <span class="skip-step">1</span>
        <div>
          <p class="skip-title">词法分析 — 存在错误</p>
          <p class="skip-desc">请先修复左侧面板中的词法错误，再重新分析。</p>
        </div>
      </div>
      <div v-else-if="hasResult && hasParseErrors" class="skipped-card skip-syn">
        <span class="skip-step">2</span>
        <div>
          <p class="skip-title">语法分析 — 存在错误</p>
          <p class="skip-desc">请先修复语法错误后，语义分析才能进行。</p>
        </div>
      </div>
      <div v-else-if="hasResult && hasSemanticErrors" class="skipped-card skip-sem">
        <span class="skip-step">3</span>
        <div>
          <p class="skip-title">语义分析 — 存在错误</p>
          <p class="skip-desc">请先修复左侧面板中的语义错误，再重新分析。</p>
        </div>
      </div>
      <div v-else class="empty-hint">暂无数据，请先运行分析</div>
    </div>
  </section>
</template>

<style scoped>
.analysis-panel {
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(12, 56, 67, 0.2);
  display: flex;
  flex-direction: column;
  min-height: 420px;
  overflow: hidden;
}

/* ---- Tab bar ---- */
.tab-bar {
  display: flex;
  border-bottom: 1px solid rgba(12, 56, 67, 0.15);
  background: rgba(240, 248, 252, 0.6);
  flex-shrink: 0;
}

.tab-btn {
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 14px 16px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-family: 'IBM Plex Sans Condensed', sans-serif;
  font-size: 15px;
  font-weight: 500;
  color: #4a7a87;
  transition: background 0.18s, color 0.18s;
  position: relative;
}

.tab-btn:hover {
  background: rgba(14, 116, 144, 0.06);
}

.tab-btn.active {
  color: #0e7490;
  font-weight: 700;
}

.tab-btn.active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 12px;
  right: 12px;
  height: 3px;
  border-radius: 3px 3px 0 0;
  background: linear-gradient(90deg, #0e7490, #15803d);
}

.tab-btn.has-error .tab-step {
  background: #dc2626;
  color: #fff;
}

.tab-step {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: rgba(14, 116, 144, 0.15);
  font-family: 'IBM Plex Mono', monospace;
  font-size: 12px;
  font-weight: 600;
  color: #0e7490;
  flex-shrink: 0;
}

.tab-btn:nth-child(2) .tab-step {
  background: rgba(21, 128, 61, 0.15);
  color: #15803d;
}

.tab-btn:nth-child(3) .tab-step {
  background: rgba(151, 67, 13, 0.15);
  color: #99440d;
}

.tab-label {
  letter-spacing: 0.03em;
}

/* ---- Tab body ---- */
.tab-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 16px;
  overflow: hidden;
}

/* ---- Token table ---- */
.table-wrap {
  overflow: auto;
  flex: 1;
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

.sem-tab .token-table th {
  background: #e6ded8;
  color: #70401b;
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

/* ---- AST ---- */
.ast-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 8px;
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
  padding: 6px 12px;
  font-family: 'IBM Plex Sans Condensed', sans-serif;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
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
  flex: 1;
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

/* ---- Skipped / empty states ---- */
.skipped-card {
  border-radius: 16px;
  padding: 24px;
  display: flex;
  align-items: center;
  gap: 14px;
  min-height: 120px;
  flex: 1;
}

.skip-lex {
  background: rgba(14, 116, 144, 0.08);
  border: 2px dashed rgba(14, 116, 144, 0.35);
}

.skip-syn {
  background: rgba(21, 128, 61, 0.08);
  border: 2px dashed rgba(21, 128, 61, 0.35);
}

.skip-sem {
  background: rgba(151, 67, 13, 0.08);
  border: 2px dashed rgba(151, 67, 13, 0.35);
}

.skip-step {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 16px;
  font-weight: 600;
  flex-shrink: 0;
}

.skip-lex .skip-step {
  background: rgba(14, 116, 144, 0.15);
  color: #0e7490;
}

.skip-syn .skip-step {
  background: rgba(21, 128, 61, 0.15);
  color: #15803d;
}

.skip-sem .skip-step {
  background: rgba(151, 67, 13, 0.08);
  color: #99440d;
}

.skip-title {
  margin: 0;
  font-family: 'Noto Serif SC', serif;
  font-size: 16px;
  color: #374151;
}

.skip-desc {
  margin: 4px 0 0;
  font-size: 13px;
  color: #6b7280;
}

.empty-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  min-height: 200px;
  color: #7a9ba6;
  font-size: 14px;
}
</style>
