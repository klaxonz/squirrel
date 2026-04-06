import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const source = readFileSync(
  path.join(__dirname, '..', 'src', 'components', 'ui', 'switch', 'Switch.vue'),
  'utf8',
)

test('switch wrapper preserves undefined for controlled boolean props', () => {
  assert.match(source, /defaultValue:\s*\{\s*[\s\S]*default:\s*undefined,/)
  assert.match(source, /trueValue:\s*\{\s*[\s\S]*default:\s*undefined,/)
  assert.match(source, /falseValue:\s*\{\s*[\s\S]*default:\s*undefined,/)
  assert.match(source, /checked:\s*\{\s*[\s\S]*default:\s*undefined,/)
  assert.match(source, /modelValue:\s*\{\s*[\s\S]*default:\s*undefined,/)
  assert.doesNotMatch(source, /defineProps<SwitchProps>\(\)/)
})
