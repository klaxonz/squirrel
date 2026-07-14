import fs from 'node:fs/promises'
import path from 'node:path'

// This codemod performs simple, deterministic string replacements for Tailwind
// utility class names used by the legacy token system (bg-bg-*, text-text-*, etc.)
// to shadcn-style utility classes.
//
// It is intentionally dumb: it does not parse Vue templates or CSS ASTs.
// Always review the diff after running.

const PROJECT_ROOT = process.cwd()
const SRC_ROOT = path.join(PROJECT_ROOT, 'src')

const FILE_EXTS = new Set(['.vue', '.js', '.ts', '.css'])

const REPLACEMENTS = [
  // Background
  ['bg-bg-primary', 'bg-background'],
  ['bg-bg-secondary', 'bg-card'],
  ['bg-bg-card', 'bg-card'],
  ['bg-bg-tertiary', 'bg-muted'],
  ['bg-bg-elevated', 'bg-muted'],
  ['bg-bg-hover', 'bg-accent'],

  // Text
  ['text-text-primary', 'text-foreground'],
  ['text-text-secondary', 'text-muted-foreground'],
  ['text-text-tertiary', 'text-muted-foreground/70'],
  ['text-text-muted', 'text-muted-foreground'],
  ['text-text-accent', 'text-foreground'],

  // Status colors
  ['text-color-primary', 'text-primary'],
  ['text-color-error', 'text-destructive'],
  ['text-color-warning', 'text-amber-500'],
  ['text-color-success', 'text-emerald-500'],
  ['text-color-info', 'text-blue-500'],

  ['bg-color-primary', 'bg-primary'],
  ['bg-color-primary-hover', 'bg-primary/90'],
  ['bg-color-error', 'bg-destructive'],
  ['bg-color-error-hover', 'bg-destructive/90'],
  ['bg-color-warning', 'bg-amber-500'],
  ['bg-color-warning-hover', 'bg-amber-600'],
  ['bg-color-success', 'bg-emerald-500'],
  ['bg-color-success-hover', 'bg-emerald-600'],
  ['bg-color-info', 'bg-blue-500'],
  ['bg-color-info-hover', 'bg-blue-600'],

  // Border + ring
  ['border-border-primary', 'border-border'],
  ['border-border-secondary', 'border-border'],
  ['border-border-hover', 'border-border'],
  ['divide-border-primary', 'divide-border'],
  ['divide-border-secondary', 'divide-border'],
  ['divide-border-hover', 'divide-border'],
  ['ring-border-primary', 'ring-border'],
  ['ring-border-secondary', 'ring-border'],
  ['ring-border-hover', 'ring-border'],

  // Overlay
  ['bg-overlay-dark-50', 'bg-black/50'],
  ['bg-overlay-dark-70', 'bg-black/70'],
  ['bg-overlay-dark-75', 'bg-black/75'],

  // Misc oddities seen in CSS @apply
  ['bg-text-tertiary', 'bg-muted-foreground/20'],

  // Form focus helpers from legacy tokens
  ['focus:border-color-info', 'focus:border-ring'],
  ['focus:ring-color-info', 'focus:ring-ring'],
  ['focus:ring-text-muted', 'focus:ring-ring'],
  ['focus:ring-color-primary', 'focus:ring-ring'],

  // Placeholder colors
  ['placeholder-text-muted', 'placeholder:text-muted-foreground'],
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
  const files = await walk(SRC_ROOT)
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
