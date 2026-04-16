import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

test('watch later action has a clearly differentiated active state', async () => {
  const videoPlaySource = await readFile(new URL('../src/views/VideoPlay.vue', import.meta.url), 'utf8')

  assert.match(
    videoPlaySource,
    /label:\s*'稍后看'/,
  )
  assert.match(
    videoPlaySource,
    /icon:\s*isLaterActionActive\.value \? 'lucide:bookmark-check' : 'lucide:bookmark-plus'/,
  )
  assert.match(
    videoPlaySource,
    /\.action-btn\.tone-later\.is-active\s*\{[\s\S]*linear-gradient\([\s\S]*border-color:\s*hsl\(var\(--primary\) \/ 0\.45\);[\s\S]*box-shadow:/,
  )
  assert.match(
    videoPlaySource,
    /\.action-btn\.tone-later\.is-active \.action-btn__icon\s*\{[\s\S]*color:\s*hsl\(var\(--primary\)\);/,
  )
})
