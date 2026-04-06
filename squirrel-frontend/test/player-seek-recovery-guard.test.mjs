import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const enginePath = new URL('../src/components/video-player/core/createPlayerEngine.ts', import.meta.url)

test('player engine gives manual seeks a grace window before stall recovery can reload the source', async () => {
  const source = await readFile(enginePath, 'utf8')

  assert.match(source, /const seek = \(time: number\): void => \{/)
  assert.match(source, /const seek = \(time: number\): void => \{[\s\S]*clearWaitingRecovery\(\)/)
  assert.match(source, /const seek = \(time: number\): void => \{[\s\S]*waitingRecoverySuppressedUntil = Date\.now\(\) \+ Math\.max\(retryDelay \* 2,\s*4000\)/)
  assert.match(source, /const seek = \(time: number\): void => \{[\s\S]*videoElement\.currentTime = time/)
})
