import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const source = readFileSync(path.join(__dirname, 'SiteConfigSection.vue'), 'utf8')

test('site config cards use SiteIcon with icon_url instead of slug text avatars', () => {
  assert.match(source, /<SiteIcon/)
  assert.match(source, /:icon-url="site\.iconUrl"/)
  assert.doesNotMatch(source, /site\.slug\.substring\(0,\s*2\)\.toUpperCase\(\)/)
})

