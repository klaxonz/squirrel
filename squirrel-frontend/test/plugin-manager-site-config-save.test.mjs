import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const source = readFileSync(path.join(__dirname, '..', 'src', 'views', 'PluginManager.vue'), 'utf8')

test('plugin manager site editor only submits the edited site payload', () => {
  assert.match(
    source,
    /await saveCatalog\(\s*\{\s*\[slug\]: sitePayload,\s*\}\s*\)/,
  )
  assert.doesNotMatch(source, /const updatedCatalog = \{ \.\.\.siteCatalog\.value \}/)
})
