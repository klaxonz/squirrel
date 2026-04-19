import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const typesPath = new URL('../src/components/video-player/core/types.ts', import.meta.url)
const enginePath = new URL('../src/components/video-player/core/createPlayerEngine.ts', import.meta.url)
const runtimePath = new URL('../src/components/video-player/runtime/usePlayer.ts', import.meta.url)

test('player runtime keeps playback state synced when media resumes through the native playing event after a seek stall', async () => {
  const [typesSource, engineSource, runtimeSource] = await Promise.all([
    readFile(typesPath, 'utf8'),
    readFile(enginePath, 'utf8'),
    readFile(runtimePath, 'utf8'),
  ])

  assert.match(typesSource, /play:\s*void[\s\S]*playing:\s*void[\s\S]*pause:\s*void/)
  assert.match(engineSource, /const onPlaying = \(\) => \{[\s\S]*events\.emit\('playing', undefined\)/)
  assert.match(engineSource, /video\.addEventListener\('playing', onPlaying\)/)
  assert.match(runtimeSource, /const markPlaybackActive = \(\) => \{[\s\S]*store\.setPlaying\(true\)[\s\S]*store\.setHasStartedPlayback\(true\)[\s\S]*store\.setLoading\(false, 'ready'\)[\s\S]*store\.setCanPlay\('video', true\)/)
  assert.match(runtimeSource, /engine\.on\('playing', \(\) => \{[\s\S]*markPlaybackActive\(\)/)
})
