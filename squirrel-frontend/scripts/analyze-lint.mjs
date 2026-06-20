// One-off helper: aggregates the design-token guard violations per file via
// the ESLint Linter API. Used during Batch A to size the fix backlog.
import { fileURLToPath, pathToFileURL } from 'node:url'
import { dirname, resolve } from 'node:path'
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')

// Import the flat config array directly (ESM), then hand it to the Linter.
// Windows: dynamic import needs a file:// URL, not a bare drive path.
const { default: configArray } = await import(pathToFileURL(join(root, 'eslint.config.js')).href)
const { Linter } = await import('eslint')
const linter = new Linter({ configType: 'flat' })
const config = configArray

function walk(dir, acc = []) {
  for (const entry of readdirSync(dir)) {
    if (entry === 'node_modules' || entry === 'dist' || entry === '.git' || entry === 'output') continue
    const p = join(dir, entry)
    const st = statSync(p)
    if (st.isDirectory()) walk(p, acc)
    else if (/\.(vue|ts|tsx|js|mjs)$/.test(p)) acc.push(p)
  }
  return acc
}

const files = walk(resolve(root, 'src'))
const perFile = {}
let total = 0
let sampleTokens = {}
for (const file of files) {
  const code = readFileSync(file, 'utf8')
  const messages = linter.verify(code, config, { filename: file })
  const hits = messages.filter((m) => m.ruleId === 'design-tokens/design-tokens')
  if (hits.length) {
    perFile[file.replace(/.*squirrel-frontend[\\/]/, '')] = hits.length
    total += hits.length
    for (const h of hits) {
      const tok = h.message.match(/`([^`]+)`/)?.[1] ?? '?'
      sampleTokens[tok] = (sampleTokens[tok] || 0) + 1
    }
  }
}

const entries = Object.entries(perFile).sort((a, b) => b[1] - a[1])
console.log(`files scanned: ${files.length}`)
console.log(`files with violations: ${entries.length}`)
console.log(`total design-token violations: ${total}`)
console.log('--- top 20 files ---')
for (const [f, n] of entries.slice(0, 20)) {
  console.log(String(n).padStart(4), f)
}
console.log('--- top 25 offending tokens ---')
const toks = Object.entries(sampleTokens).sort((a, b) => b[1] - a[1]).slice(0, 25)
for (const [t, n] of toks) {
  console.log(String(n).padStart(4), t)
}


