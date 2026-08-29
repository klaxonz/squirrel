import assert from 'node:assert/strict'
import test from 'node:test'
import { DEFAULT_MANIFEST, evaluateAutomation, validateManifest, fixtureEvidence } from '../scripts/visual-review-harness.mjs'

test('manifest schema requires stable fields and validates viewport', () => {
  assert.deepEqual(validateManifest(DEFAULT_MANIFEST), DEFAULT_MANIFEST)
  assert.throws(() => validateManifest({ ...DEFAULT_MANIFEST, viewport: { width: 100, height: 100 } }), /viewport/)
  assert.throws(() => validateManifest({ ...DEFAULT_MANIFEST, fixture: undefined }), /manifest missing/)
})

test('automation verdict blocks smoke fixtures and enforces business gates', () => {
  const evidence = fixtureEvidence(DEFAULT_MANIFEST)
  assert.equal(evaluateAutomation(evidence).status, 'blocked')
  const business = { ...evidence, provenance: { mode: 'electron', target: 'business' }, runtime: 'electron' }
  assert.equal(evaluateAutomation(business).status, 'passed')
  assert.equal(evaluateAutomation({ ...business, overflow: { horizontal: true, vertical: false } }).status, 'failed')
  assert.equal(evaluateAutomation({ ...business, contrast: [{ selector: 'x', ratio: 2 }] }).errors[0], 'contrast:x')
  assert.ok(evaluateAutomation({ ...business, accessibility: [{ selector: 'button', accessibleName: '' }] }).errors.includes('accessible-name:button'))
  assert.ok(evaluateAutomation({ ...business, console: [{ level: 'error', type: 'console' }] }).errors.includes('console:console'))
  assert.ok(evaluateAutomation({ ...business, taskTrace: { status: 'failed', steps: [] } }).errors.includes('task-trace'))
})

test('thresholds are configurable', () => {
  const evidence = { ...fixtureEvidence(DEFAULT_MANIFEST), provenance: { mode: 'electron', target: 'business' }, runtime: 'electron' }
  assert.equal(evaluateAutomation(evidence, { contrastMin: 20 }).status, 'failed')
})
