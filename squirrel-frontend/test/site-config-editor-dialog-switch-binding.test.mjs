import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const source = readFileSync(
  path.join(__dirname, '..', 'src', 'components', 'settings', 'SiteConfigEditorDialog.vue'),
  'utf8',
)

test('site config editor switches update the ref-backed form via .value helper', () => {
  assert.match(source, /const setSiteEditorBooleanField = \(key, value\) => \{/)
  assert.match(source, /siteEditorForm\.value\[key\] = !!value/)
  assert.doesNotMatch(source, /siteEditorForm\.enabled = !!v/)
  assert.doesNotMatch(source, /siteEditorForm\.rateLimitEnabled = !!v/)
  assert.doesNotMatch(source, /siteEditorForm\[meta\.key\] = !!v/)
})
