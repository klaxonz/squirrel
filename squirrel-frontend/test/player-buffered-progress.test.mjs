import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const usePlayerPath = new URL('../src/components/video-player/runtime/usePlayer.ts', import.meta.url)

test('player buffered progress is derived from the current playable range instead of the furthest buffered end', async () => {
  const source = await readFile(usePlayerPath, 'utf8')

  assert.match(source, /const calculateBufferedAheadPercent = \(buffered: TimeRanges, duration: number, currentTime: number\): number =>/)
  assert.match(source, /for \(let index = 0; index < buffered\.length; index \+= 1\)/)
  assert.match(source, /buffered\.start\(index\) <= currentTime && currentTime <= buffered\.end\(index\)/)
  assert.match(source, /store\.setBufferedProgress\(calculateBufferedAheadPercent\(buffered, duration, store\.currentTime\)\)/)
})
