import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const enginePath = new URL('../src/components/video-player/core/createPlayerEngine.ts', import.meta.url)

test('player engine gives explicit quality switches a grace window before stall recovery can reload the source', async () => {
  const source = await readFile(enginePath, 'utf8')

  assert.match(source, /let waitingRecoverySuppressedUntil = 0/)
  assert.match(source, /waitingRecoverySuppressedUntil = Date\.now\(\) \+ Math\.max\(retryDelay \* 2,\s*4000\)/)
  assert.match(source, /const suppressionDelay = Math\.max\(0,\s*waitingRecoverySuppressedUntil - Date\.now\(\)\)/)
  assert.match(source, /}, Math\.max\(retryDelay,\s*1500\) \+ suppressionDelay\)/)
})
