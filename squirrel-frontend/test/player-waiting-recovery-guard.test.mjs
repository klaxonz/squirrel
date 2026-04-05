import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const enginePath = new URL('../src/components/video-player/core/createPlayerEngine.ts', import.meta.url)

test('player engine only escalates waiting recovery when playback is still stalled at the same time position', async () => {
  const source = await readFile(enginePath, 'utf8')

  assert.match(source, /const stalledAtTime = videoElement\?\.currentTime \?\? 0/)
  assert.match(source, /if \(!videoElement \|\| !loading \|\| videoElement\.ended\) return/)
  assert.match(source, /if \(Math\.abs\(\(videoElement\.currentTime \?\? 0\) - stalledAtTime\) > 0\.25\) return/)
})
