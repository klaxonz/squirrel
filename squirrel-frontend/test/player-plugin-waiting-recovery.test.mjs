import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const enginePath = new URL('../src/components/video-player/core/createPlayerEngine.ts', import.meta.url)

test('player engine routes plugin waiting and canplay events through the shared loading recovery state', async () => {
  const source = await readFile(enginePath, 'utf8')

  assert.match(source, /emit\(event,\s*payload\)\s*\{/)
  assert.match(source, /if \(event === 'waiting'\) \{\s*loading = true\s*scheduleWaitingRecovery\(\)\s*\}/)
  assert.match(source, /if \(event === 'canplay'\) \{[\s\S]*loading = false[\s\S]*retryCount = 0[\s\S]*clearWaitingRecovery\(\)/)
})
