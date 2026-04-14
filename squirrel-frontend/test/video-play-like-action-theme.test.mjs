import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const videoPlayPath = new URL('../src/views/VideoPlay.vue', import.meta.url)

test('video play like action uses the shared primary active state instead of a hardcoded green override', async () => {
  const source = await readFile(videoPlayPath, 'utf8')

  assert.match(source, /\.action-btn\.is-active\s*\{[^}]*background:\s*hsl\(var\(--primary\)\s*\/\s*0\.12\);/s)
  assert.match(source, /\.action-btn\.is-active\s*\{[^}]*color:\s*hsl\(var\(--primary\)\);/s)
  assert.match(source, /\.action-btn\.is-active\s*\{[^}]*border-color:\s*hsl\(var\(--primary\)\s*\/\s*0\.4\);/s)
  assert.doesNotMatch(source, /\.action-btn\.tone-like\.is-active\s*\{/s)
  assert.doesNotMatch(source, /hsl\(142\s+76%\s+36%/)
})
