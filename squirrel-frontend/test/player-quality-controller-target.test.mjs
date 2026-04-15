import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const enginePath = new URL('../src/components/video-player/core/createPlayerEngine.ts', import.meta.url)

test('player engine passes resolved quality ids to the stream controller instead of ambiguous labels', async () => {
  const source = await readFile(enginePath, 'utf8')

  assert.match(source, /const \{ controllerQuality, emittedLabel, isAutoQuality \} = resolveQualitySelection\(quality\)/)
  assert.match(source, /controllerQuality:\s*currentQualityId \?\? quality/)
  assert.match(source, /controller\.setQuality\(controllerQuality\)/)
  assert.match(source, /setQuality\(nextQuality\.id \?\? nextQuality\.label\)/)
})
