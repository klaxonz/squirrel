import fs from 'node:fs/promises'
import path from 'node:path'

// One-off codemod: replace raw `font-size` values with the typography scale
// tokens defined in shared/styles/layout.css (--app-text-2xs … --app-text-2xl).
// Plain text replacement scoped to <style> blocks in .vue files and whole .css
// files. Always review the diff.

const PROJECT_ROOT = path.resolve(process.cwd(), 'renderer')
const TARGET_ROOT = path.join(PROJECT_ROOT, 'src')

// Declared sub-theme / content-typography zones — deliberately out of scope:
//   video-player/**  the --sp-* player sub-theme (see docs/ui-system-consolidation-plan.md)
//   reader.css       article content typography, not chrome
const EXEMPT = [
  /[/\\]features[/\\]playback[/\\]components[/\\]video-player[/\\]/,
  /[/\\]shared[/\\]styles[/\\]reader\.css$/,
]

// Snap table: raw value → scale token. Values chosen to match the nearest
// scale step; --app-h3-size is kept for the 15px card-title tier it already
// defines.
const MAPPING = [
  ['0.625rem', 'var(--app-text-2xs)'],
  ['0.6875rem', 'var(--app-text-xs)'],
  ['0.75rem', 'var(--app-text-sm)'],
  ['0.78rem', 'var(--app-text-sm)'],
  ['0.8125rem', 'var(--app-text-md)'],
  ['0.875rem', 'var(--app-text-base)'],
  ['0.9rem', 'var(--app-text-base)'],
  ['0.9375rem', 'var(--app-h3-size)'],
  ['0.95rem', 'var(--app-text-lg)'],
  ['1rem', 'var(--app-text-lg)'],
  ['1.125rem', 'var(--app-text-xl)'],
  ['1.25rem', 'var(--app-text-2xl)'],
  ['11px', 'var(--app-text-xs)'],
  ['12px', 'var(--app-text-sm)'],
  ['13px', 'var(--app-text-md)'],
  ['14px', 'var(--app-text-base)'],
  ['15px', 'var(--app-text-lg)'],
]

// Ordered longest-value-first so `1rem` can't shadow `1.125rem` etc.
const RULES = MAPPING
  .map(([from, to]) => ({
    re: new RegExp(`(font-size:\\s*)${from.replace('.', '\\.')}(?=[;\\s}!])`, 'g'),
    to,
  }))
  .sort((a, b) => b.re.source.length - a.re.source.length)

async function walk(dir) {
  const entries = await fs.readdir(dir, { withFileTypes: true })
  const files = []
  for (const entry of entries) {
    const full = path.join(dir, entry.name)
    if (entry.isDirectory()) files.push(...(await walk(full)))
    else if (/\.(vue|css)$/.test(entry.name)) files.push(full)
  }
  return files
}

function transform(source, isVue) {
  if (!isVue) return apply(source)
  // Only rewrite inside <style> blocks; <script>/<template> may carry
  // non-CSS strings (canvas drawing, docs) that can't resolve var().
  return source.replace(/(<style[^>]*>)([\s\S]*?)(<\/style>)/g, (_, open, body, close) => open + apply(body) + close)
}

function apply(text) {
  let out = text
  for (const { re, to } of RULES) out = out.replace(re, `$1${to}`)
  return out
}

const files = await walk(TARGET_ROOT)
let changed = 0
for (const file of files) {
  if (EXEMPT.some((re) => re.test(file))) continue
  const isVue = file.endsWith('.vue')
  const source = await fs.readFile(file, 'utf8')
  const next = transform(source, isVue)
  if (next !== source) {
    await fs.writeFile(file, next)
    changed++
    console.log('updated', path.relative(PROJECT_ROOT, file))
  }
}
console.log(`\n${changed} file(s) updated`)
