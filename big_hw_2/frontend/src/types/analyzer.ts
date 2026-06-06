export interface TokenRow {
  type: string
  value: string
  line: number
  column: number
}

export type DiagnosticPhase = 'lexical' | 'syntax' | 'semantic'

export interface Diagnostic {
  phase: DiagnosticPhase
  message: string
  line: number
  column: number
}

export interface AnalyzeResponse {
  ok: boolean
  tokens: TokenRow[]
  lexErrors: string[]
  parseErrors: string[]
  semanticErrors: string[]
  lexDiagnostics?: Diagnostic[]
  parseDiagnostics?: Diagnostic[]
  semanticDiagnostics?: Diagnostic[]
  astSummary: string
  astTree: string
  ast: Record<string, unknown>
}

export interface AnalyzeRequest {
  source: string
}
