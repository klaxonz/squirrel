import fs from 'node:fs/promises'
import path from 'node:path'

// Replace legacy CSS variables (var(--bg-*), var(--text-*), etc.) with shadcn token usage.
// This is a plain text replacement. Always review the diff.

const PROJECT_ROOT = process.cwd()
const TARGET_ROOTS = [
  path.join(PROJECT_ROOT, 'src'),
]

const FILE_EXTS = new Set(['.vue', '.js', '.ts', '.css'])

const REPLACEMENTS = [
  // Background
  ['var(--bg-primary)', 'hsl(var(--background))'],
  ['var(--bg-secondary)', 'hsl(var(--card))'],
  ['var(--bg-tertiary)', 'hsl(var(--muted))'],
  ['var(--bg-card)', 'hsl(var(--card))'],
  ['var(--bg-elevated)', 'hsl(var(--muted))'],
  ['var(--bg-hover)', 'hsl(var(--accent))'],
  ['var(--bg-media)', '#000'],

  // Text
  ['var(--text-primary)', 'hsl(var(--foreground))'],
  ['var(--text-secondary)', 'hsl(var(--muted-foreground))'],
  ['var(--text-tertiary)', 'hsl(var(--muted-foreground))'],
  ['var(--text-muted)', 'hsl(var(--muted-foreground))'],
  ['var(--text-accent)', 'hsl(var(--foreground))'],

  // Border
  ['var(--border-primary)', 'hsl(var(--border))'],
  ['var(--border-secondary)', 'hsl(var(--border))'],
  ['var(--border-hover)', 'hsl(var(--border))'],

  // Primary / destructive
  ['var(--color-primary)', 'hsl(var(--primary))'],
  ['rgba(var(--color-primary-rgb), 0.16)', 'hsl(var(--primary) / 0.16)'],
  ['rgba(var(--color-primary-rgb), 0.42)', 'hsl(var(--primary) / 0.42)'],
  ['var(--color-error)', 'hsl(var(--destructive))'],
]

async function walk(dir) {
  const entries = await fs.readdir(dir, { withFileTypes: true })
  const files = []
  for (const entry of entries) {
    const full = path.join(dir, entry.name)
    if (entry.isDirectory()) {
      files.push(...(await walk(full)))
      continue
    }
    if (FILE_EXTS.has(path.extname(entry.name))) {
      files.push(full)
    }
  }
  return files
}

function applyReplacements(input) {
  let out = input
  for (const [from, to] of REPLACEMENTS) {
    out = out.split(from).join(to)
  }
  return out
}

async function main() {
  const files = []
  for (const root of TARGET_ROOTS) {
    files.push(...(await walk(root)))
  }

  let changed = 0
  for (const file of files) {
    const before = await fs.readFile(file, 'utf8')
    const after = applyReplacements(before)
    if (after === before) continue
    await fs.writeFile(file, after, 'utf8')
    changed += 1
  }

  // eslint-disable-next-line no-console
  console.log(`Updated ${changed} file(s).`)
}

await main()

