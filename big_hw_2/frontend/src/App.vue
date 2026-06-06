<script setup lang="ts">
import { computed } from 'vue'
import { useAnalyzer } from './composables/useAnalyzer'
import SourcePanel from './components/analyzer/SourcePanel.vue'
import MetricStrip from './components/analyzer/MetricStrip.vue'
import AnalysisPanel from './components/analyzer/AnalysisPanel.vue'
import ErrorPanel from './components/analyzer/ErrorPanel.vue'

const {
  source,
  loading,
  requestError,
  result,
  tokenCount,
  lexErrorCount,
  parseErrorCount,
  semanticErrorCount,
  analyze,
  loadExample,
} = useAnalyzer()

const astJson = computed(() => {
  if (!result.value?.ast) {
    return ''
  }
  return JSON.stringify(result.value.ast, null, 2)
})

const hasResult = computed(() => result.value !== null)
const hasLexErrors = computed(() => (result.value?.lexErrors?.length ?? 0) > 0)
const hasParseErrors = computed(() => (result.value?.parseErrors?.length ?? 0) > 0)
</script>

<template>
  <div class="page-shell">
    <header class="hero">
      <p class="hero-eyebrow">Tongji Compiler Principles</p>
      <h1 class="hero-title">类 Rust 词法 / 语法 分析演示台</h1>
      <p class="hero-subtitle">
        前端展示层连接本地 Python 分析器，实时查看 Token、AST 与语义诊断结果。
      </p>
    </header>

    <MetricStrip
      :token-count="tokenCount"
      :lex-error-count="lexErrorCount"
      :parse-error-count="parseErrorCount"
      :semantic-error-count="semanticErrorCount"
      :loading="loading"
    />

    <main class="layout-grid">
      <section class="left-column">
        <SourcePanel v-model="source" @analyze="analyze" @load-example="loadExample" />
        <ErrorPanel
          :request-error="requestError"
          :lex-errors="result?.lexErrors ?? []"
          :parse-errors="result?.parseErrors ?? []"
          :semantic-errors="result?.semanticErrors ?? []"
        />
      </section>

      <section class="right-column">
        <AnalysisPanel
          :tokens="result?.tokens ?? []"
          :ast-summary="result?.astSummary ?? ''"
          :ast-tree="result?.astTree ?? ''"
          :ast-json="astJson"
          :has-result="hasResult"
          :has-lex-errors="hasLexErrors"
          :has-parse-errors="hasParseErrors"
        />
      </section>
    </main>
  </div>
</template>

<style scoped></style>
