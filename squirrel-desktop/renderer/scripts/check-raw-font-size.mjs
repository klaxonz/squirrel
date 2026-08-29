import fs from 'node:fs/promises'
import path from 'node:path'

// Lint gate: `font-size` outside the typography scale tokens is forbidden.
// All font sizing must go through --app-text-* (shared/styles/layout.css).
// Allowed residuals:
//   - var(...)/inherit/1em/em-relative/clamp() values
//   - features/playback/components/video-player/**  the declared --sp-*
//     player sub-theme (docs/ui-system-consolidation-plan.md Phase 4)
//   - shared/styles/reader.css  article content typography, not chrome
//   - token *definitions* in shared/styles/layout.css
// Run: npm run check:font-size  (from squirrel-desktop/)

const PROJECT_ROOT = path.resolve(process.cwd(), 'renderer')
const TARGET_ROOT = path.join(PROJECT_ROOT, 'src')

const EXEMPT = [
  /[/\\]features[/\\]playback[/\\]components[/\\]video-player[/\\]/,
  /[/\\]shared[/\\]styles[/\\]reader\.css$/,
  /[/\\]shared[/\\]styles[/\\]layout\.css$/,
]

// Raw values with a fixed rem/px unit. em-relative (0.86em), clamp(),
// var(), and unitless/inherit are contextual and allowed.
const RAW_FONT_SIZE_RE = /font-size:\s*\d*\.?\d+(?:rem|px)\b/g

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

const violations = []
for (const file of await walk(TARGET_ROOT)) {
  if (EXEMPT.some((re) => re.test(file))) continue
  const source = await fs.readFile(file, 'utf8')
  const lines = source.split('\n')
  lines.forEach((line, i) => {
    if (RAW_FONT_SIZE_RE.test(line)) {
      violations.push(`${path.relative(PROJECT_ROOT, file)}:${i + 1}: ${line.trim()}`)
    }
    RAW_FONT_SIZE_RE.lastIndex = 0
  })
}

if (violations.length) {
  console.error(`raw font-size values found (${violations.length}) — use --app-text-* tokens:\n`)
  for (const v of violations) console.error('  ' + v)
  process.exit(1)
}
console.log('check-raw-font-size: OK')
