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

export interface FunctionSignature {
  name: string
  params: string[]
  returnType: string | null
  line: number
  column: number
}

export interface QuadRow {
  index: number
  op: string
  arg1: string
  arg2: string
  result: string
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
  functionSignatures?: FunctionSignature[]
  quads?: QuadRow[]
  astSummary: string
  astTree: string
  ast: Record<string, unknown>
}

export interface AnalyzeRequest {
  source: string
}
