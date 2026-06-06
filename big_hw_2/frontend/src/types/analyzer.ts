export interface TokenRow {
  type: string
  value: string
  line: number
  column: number
}

export interface AnalyzeResponse {
  ok: boolean
  tokens: TokenRow[]
  lexErrors: string[]
  parseErrors: string[]
  semanticErrors: string[]
  astSummary: string
  astTree: string
  ast: Record<string, unknown>
}

export interface AnalyzeRequest {
  source: string
}
