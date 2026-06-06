import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { spawn } from 'node:child_process'
import { resolve } from 'node:path'
import type { IncomingMessage, ServerResponse } from 'node:http'

function readRequestBody(req: IncomingMessage): Promise<string> {
  return new Promise((resolveBody, rejectBody) => {
    const chunks: Buffer[] = []
    req.on('data', (chunk) => {
      chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk))
    })
    req.on('end', () => resolveBody(Buffer.concat(chunks).toString('utf-8')))
    req.on('error', rejectBody)
  })
}

function runPythonAnalyzer(source: string): Promise<string> {
  return new Promise((resolveOutput, rejectOutput) => {
    const projectRoot = __dirname
    const analyzerCwd = resolve(projectRoot, '../bighw2')
    const analyzerScript = resolve(analyzerCwd, 'analyze_source.py')
    const pythonBin = process.env.PYTHON_BIN ?? 'D:/python/python.exe'

    const child = spawn(pythonBin, ['-X', 'utf8', analyzerScript], {
      cwd: analyzerCwd,
      stdio: ['pipe', 'pipe', 'pipe'],
      env: {
        ...process.env,
        PYTHONUTF8: '1',
        PYTHONIOENCODING: 'utf-8',
      },
    })

    let stdout = ''
    let stderr = ''

    child.stdout.on('data', (chunk) => {
      stdout += chunk.toString('utf8')
    })

    child.stderr.on('data', (chunk) => {
      stderr += chunk.toString('utf8')
    })

    child.on('error', (err) => {
      rejectOutput(err)
    })

    child.on('close', (code) => {
      if (code === 0) {
        resolveOutput(stdout)
      } else {
        rejectOutput(
          new Error(`Analyzer exited with code ${String(code)}${stderr ? `: ${stderr}` : ''}`),
        )
      }
    })

    child.stdin.write(source)
    child.stdin.end()
  })
}

async function handleAnalyzeApi(req: IncomingMessage, res: ServerResponse) {
  if (req.method !== 'POST') {
    res.statusCode = 405
    res.setHeader('Content-Type', 'application/json; charset=utf-8')
    res.end(JSON.stringify({ message: 'Method Not Allowed' }))
    return
  }

  try {
    const rawBody = await readRequestBody(req)
    const body = JSON.parse(rawBody) as { source?: string }
    const source = body.source ?? ''

    const output = await runPythonAnalyzer(source)
    res.statusCode = 200
    res.setHeader('Content-Type', 'application/json; charset=utf-8')
    res.end(output)
  } catch (error) {
    res.statusCode = 500
    res.setHeader('Content-Type', 'application/json; charset=utf-8')
    res.end(
      JSON.stringify({
        message: error instanceof Error ? error.message : 'Unknown server error',
      }),
    )
  }
}

function analyzerApiPlugin() {
  return {
    name: 'analyzer-api-plugin',
    configureServer(server: { middlewares: { use: (path: string, cb: (req: IncomingMessage, res: ServerResponse) => void) => void } }) {
      server.middlewares.use('/api/analyze', (req: IncomingMessage, res: ServerResponse) => {
        void handleAnalyzeApi(req, res)
      })
    },
    configurePreviewServer(server: { middlewares: { use: (path: string, cb: (req: IncomingMessage, res: ServerResponse) => void) => void } }) {
      server.middlewares.use('/api/analyze', (req: IncomingMessage, res: ServerResponse) => {
        void handleAnalyzeApi(req, res)
      })
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(), analyzerApiPlugin()],
})
