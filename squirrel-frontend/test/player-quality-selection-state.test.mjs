import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const enginePath = new URL('../src/components/video-player/core/createPlayerEngine.ts', import.meta.url)

test('player engine resolves selected quality state from either ids or labels and clears it for auto mode', async () => {
  const source = await readFile(enginePath, 'utf8')

  assert.match(source, /const isAutoQualityToken = \(quality: QualitySelectionRequest\): boolean =>/)
  assert.match(source, /return quality === 'auto' \|\| quality === -1 \|\| qStr === 'auto' \|\| qStr === '自动'/)
  assert.match(source, /const findQualityByRequest = \(quality: QualitySelectionRequest\): QualityLevel \| null =>/)
  assert.match(source, /String\(item\.id\) === normalizedQuality \|\| item\.label === normalizedQuality/)
  assert.match(source, /const resolveQualitySelection = \(quality: QualitySelectionRequest\):/)
  assert.match(source, /matchedQuality\?\.runtimeSelection/)
  assert.match(source, /currentQualityId = null[\s\S]*registeredQualityId = null[\s\S]*currentQualityLabel = 'auto'/)
})

test('player engine disables automatic quality fallback by default', async () => {
  const source = await readFile(enginePath, 'utf8')

  assert.match(source, /const enableQualityFallback = options\.errorRecovery\?\.enableQualityFallback \?\? false/)
  assert.match(source, /if \(enableQualityFallback && getNextLowerQuality\(\)\) return 'quality-fallback'/)
})
