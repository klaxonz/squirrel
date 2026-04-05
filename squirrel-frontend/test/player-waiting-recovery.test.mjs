import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const enginePath = new URL('../src/components/video-player/core/createPlayerEngine.ts', import.meta.url)

test('player engine escalates long waiting or stalled states into the shared recovery flow', async () => {
  const source = await readFile(enginePath, 'utf8')

  assert.match(source, /let waitingRecoveryTimer: ReturnType<typeof setTimeout> \| null = null/)
  assert.match(source, /const scheduleWaitingRecovery = \(\): void =>/)
  assert.match(source, /code: 'STALL_DETECTED'/)
  assert.match(source, /video\.addEventListener\('stalled', onStalled\)/)
})
