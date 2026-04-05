import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const enginePath = new URL('../src/components/video-player/core/createPlayerEngine.ts', import.meta.url)

test('player engine resolves selected quality state from either ids or labels and clears it for auto mode', async () => {
  const source = await readFile(enginePath, 'utf8')

  assert.match(source, /const directMatch = qualities\.find\(/)
  assert.match(source, /String\(item\.id\) === String\(quality\) \|\| item\.label === String\(quality\)/)
  assert.match(source, /const isAutoQuality = quality === 'auto' \|\| quality === -1 \|\| qStr === 'auto' \|\| qStr === '自动'/)
  assert.match(source, /currentQualityId = null[\s\S]*registeredQualityId = null[\s\S]*currentQualityLabel = 'auto'/)
})
