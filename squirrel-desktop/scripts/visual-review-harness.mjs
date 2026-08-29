import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

export const MANIFEST_VERSION = 1
export const DEFAULT_MANIFEST = {
  schemaVersion: MANIFEST_VERSION,
  scenario: 'offline-electron-smoke',
  viewport: { width: 1280, height: 800, deviceScaleFactor: 1 },
  electron: { version: '41.2.0', channel: 'stable' },
  os: process.platform,
  locale: 'en-US',
  theme: 'light',
  fixture: 'tests/fixtures/electron-smoke.html',
  promptVersion: '1.0',
  provenance: { mode: 'fixture', target: 'smoke-only' },
}

export function validateManifest(manifest) {
  const required = ['schemaVersion', 'scenario', 'viewport', 'electron', 'os', 'locale', 'theme', 'fixture', 'promptVersion', 'provenance']
  const missing = required.filter((key) => manifest?.[key] === undefined)
  if (missing.length) throw new Error(`manifest missing: ${missing.join(', ')}`)
  if (manifest.schemaVersion !== MANIFEST_VERSION) throw new Error(`unsupported schemaVersion: ${manifest.schemaVersion}`)
  if (!Number.isInteger(manifest.viewport.width) || !Number.isInteger(manifest.viewport.height) || manifest.viewport.width < 320 || manifest.viewport.height < 240) {
    throw new Error('viewport must contain integer width >= 320 and height >= 240')
  }
  if (!manifest.scenario || !manifest.fixture || !manifest.promptVersion || !manifest.provenance?.mode || !manifest.provenance?.target) throw new Error('scenario, fixture, promptVersion and provenance must be non-empty')
  return manifest
}

export function evaluateAutomation(evidence, thresholds = {}) {
  const errors = []
  const contrastMin = thresholds.contrastMin ?? 4.5
  for (const item of evidence.contrast ?? []) if (item.ratio < contrastMin) errors.push(`contrast:${item.selector}`)
  for (const item of evidence.rawStyles ?? []) if (item.rawColor || item.rawFontSize) errors.push(`raw-style:${item.selector}`)
  if (evidence.overflow?.horizontal || evidence.overflow?.vertical) errors.push('overflow')
  for (const item of evidence.accessibility ?? []) if (!item.accessibleName) errors.push(`accessible-name:${item.selector}`)
  for (const item of evidence.console ?? []) if (item.level === 'error' || item.type === 'unhandledrejection') errors.push(`console:${item.type}`)
  const task = evidence.taskTrace ?? {}
  if (task.status !== 'passed' || !Array.isArray(task.steps) || task.steps.length === 0) errors.push('task-trace')
  if (evidence.provenance?.target === 'smoke-only' || evidence.runtime === 'blocked-unless-electron-smoke-passes') return { status: 'blocked', errors: ['fixture-smoke-only'], thresholds: { contrastMin } }
  return { status: errors.length ? 'failed' : 'passed', errors, thresholds: { contrastMin } }
}

function svgFixture(manifest) {
  const { width, height } = manifest.viewport
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}"><rect width="100%" height="100%" fill="#f8fafc"/><rect x="32" y="28" width="${width - 64}" height="72" rx="8" fill="#0f172a"/><text x="56" y="73" fill="#ffffff" font-family="Arial" font-size="24">Squirrel offline fixture</text><rect x="32" y="132" width="${width - 64}" height="${height - 164}" rx="8" fill="#ffffff" stroke="#cbd5e1"/><text x="56" y="180" fill="#0f172a" font-family="Arial" font-size="18">Deterministic visual review fixture</text></svg>`
}

export function fixtureEvidence(manifest) {
  return {
    source: 'deterministic-fixture',
    provenance: { mode: 'fixture', target: 'smoke-only' },
    viewport: { ...manifest.viewport, overflow: false },
    aria: { role: 'document', name: 'Squirrel offline fixture' },
    accessibility: [{ selector: 'svg', role: 'document', accessibleName: 'Squirrel offline fixture' }],
    styles: [{ selector: 'svg', display: 'block', color: '#0f172a', fontSize: '18px' }],
    rawStyles: [],
    contrast: [{ selector: 'header', foreground: '#ffffff', background: '#0f172a', ratio: 17.85 }],
    overflow: { horizontal: false, vertical: false },
    console: [],
    unhandledRejections: [],
    taskTrace: { status: 'passed', steps: [{ id: 'fixture-ready', status: 'passed' }] },
  }
}

export async function collectFixture(outDir, manifest) {
  await fs.mkdir(outDir, { recursive: true })
  await fs.writeFile(path.join(outDir, 'actual.svg'), svgFixture(manifest))
  const evidence = fixtureEvidence(manifest)
  await fs.writeFile(path.join(outDir, 'dom.json'), JSON.stringify(evidence.aria, null, 2))
  await fs.writeFile(path.join(outDir, 'styles.json'), JSON.stringify(evidence.styles, null, 2))
  await fs.writeFile(path.join(outDir, 'task-trace.json'), JSON.stringify(evidence.taskTrace, null, 2))
  return evidence
}

export async function writeReviewInputs(root, manifest, evidence, verdict) {
  await fs.writeFile(path.join(root, 'manifest.json'), JSON.stringify(manifest, null, 2))
  await fs.writeFile(path.join(root, 'automation-verdict.json'), JSON.stringify(verdict, null, 2))
  const payload = { promptVersion: manifest.promptVersion, manifest, evidence, instruction: 'Review only supplied artifacts. Do not claim completion; report findings with selectors and evidence.' }
  await fs.writeFile(path.join(root, 'visual-ai-review.json'), JSON.stringify(payload, null, 2))
  await fs.writeFile(path.join(root, 'task-ai-review.json'), JSON.stringify({ ...payload, instruction: 'Assess task trace and UI evidence against the requested scenario; do not infer unobserved behavior.' }, null, 2))
  await fs.writeFile(path.join(root, 'review-prompts.md'), '# AI review inputs\n\n- Visual AI: read visual-ai-review.json; inspect actual.svg, DOM and styles.\n- Task AI: read task-ai-review.json; assess task-trace and verdict.\n\nAI review is not run by this harness.\n')
}

export async function finalizeArtifacts(root, candidate, baseline, manifest, evidence, verdict, updateBaseline = false) {
  await fs.mkdir(baseline, { recursive: true })
  const actualPng = path.join(candidate, 'actual.png')
  const actualSvg = path.join(candidate, 'actual.svg')
  const referencePng = path.join(baseline, 'baseline.png')
  const referenceSvg = path.join(baseline, 'baseline.svg')
  const hasActualPng = await exists(actualPng)
  const hasActualSvg = await exists(actualSvg)
  let hasReferencePng = await exists(referencePng)
  let hasReferenceSvg = await exists(referenceSvg)
  if (updateBaseline) {
    if (hasActualPng) await fs.copyFile(actualPng, referencePng)
    if (hasActualSvg) await fs.copyFile(actualSvg, referenceSvg)
    hasReferencePng = await exists(referencePng)
    hasReferenceSvg = await exists(referenceSvg)
  }
  const actual = hasActualPng ? actualPng : actualSvg
  const reference = hasReferencePng ? referencePng : referenceSvg
  const hasActual = hasActualPng || hasActualSvg
  const hasReference = hasReferencePng || hasReferenceSvg
  const status = hasReference && hasActual ? (await fs.readFile(actual)).equals(await fs.readFile(reference)) ? 'identical' : 'changed' : 'blocked'
  await fs.writeFile(path.join(root, 'diff.json'), JSON.stringify({ status, baselinePresent: hasReference, actualPresent: hasActual }, null, 2))
  await writeReviewInputs(root, manifest, evidence, verdict)
}

async function exists(file) { try { await fs.access(file); return true } catch { return false }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const args = new Set(process.argv.slice(2))
  const root = path.resolve(process.cwd(), args.has('--out') ? process.argv[process.argv.indexOf('--out') + 1] : 'visual-review-results')
  const candidate = path.join(root, 'candidate')
  const baseline = path.join(root, 'baseline')
  const manifest = validateManifest({ ...DEFAULT_MANIFEST, ...(await readOptional(path.join(root, 'manifest.json'))) })
  const evidence = await collectFixture(candidate, manifest)
  const verdict = evaluateAutomation(evidence)
  await fs.writeFile(path.join(candidate, 'manifest.json'), JSON.stringify(manifest, null, 2))
  await finalizeArtifacts(root, candidate, baseline, manifest, evidence, verdict, args.has('--update-baseline'))
  console.log(JSON.stringify({ status: verdict.status, source: evidence.source, output: root, baselineUpdated: args.has('--update-baseline') }, null, 2))
  if (verdict.status !== 'passed') process.exitCode = 1
}

async function readOptional(file) { try { return JSON.parse(await fs.readFile(file, 'utf8')) } catch { return {} } }
