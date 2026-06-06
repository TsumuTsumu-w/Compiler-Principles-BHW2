import { computed, shallowRef } from 'vue'
import type { AnalyzeRequest, AnalyzeResponse } from '../types/analyzer'

const DEFAULT_SOURCE = `fn program_5_2(mut n:i32) {
    for mut i in 1..n+1 {
        n=n-1;
    }
}`

export function useAnalyzer() {
  const source = shallowRef(DEFAULT_SOURCE)
  const loading = shallowRef(false)
  const requestError = shallowRef('')
  const result = shallowRef<AnalyzeResponse | null>(null)

  const tokenCount = computed(() => result.value?.tokens.length ?? 0)
  const lexErrorCount = computed(() => result.value?.lexErrors.length ?? 0)
  const parseErrorCount = computed(() => result.value?.parseErrors.length ?? 0)
  const semanticErrorCount = computed(() => result.value?.semanticErrors.length ?? 0)

  const allErrors = computed(() => {
    if (!result.value) {
      return []
    }
    return [
      ...result.value.lexErrors,
      ...result.value.parseErrors,
      ...result.value.semanticErrors,
    ]
  })

  async function analyze() {
    loading.value = true
    requestError.value = ''

    const payload: AnalyzeRequest = { source: source.value }

    try {
      const response = await fetch('/api/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      })

      if (!response.ok) {
        throw new Error(`Analyzer request failed: ${response.status}`)
      }

      const data = (await response.json()) as AnalyzeResponse
      result.value = data
    } catch (error) {
      requestError.value =
        error instanceof Error ? error.message : 'Unexpected analyzer error'
    } finally {
      loading.value = false
    }
  }

  function loadExample() {
    source.value = DEFAULT_SOURCE
  }

  return {
    source,
    loading,
    requestError,
    result,
    tokenCount,
    lexErrorCount,
    parseErrorCount,
    semanticErrorCount,
    allErrors,
    analyze,
    loadExample,
  }
}
