import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const source = readFileSync(path.join(__dirname, 'SiteIcon.vue'), 'utf8')

test('site icon falls back to a generic icon instead of text initials', () => {
  assert.match(source, /name="siteFallback"/)
  assert.doesNotMatch(source, /fallbackText/)
})
