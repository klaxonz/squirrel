import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const videoPlayerPath = new URL('../src/components/video-player/VideoPlayer.vue', import.meta.url)

test('progress hover preview does not reuse the active scrub path', async () => {
  const source = await readFile(videoPlayerPath, 'utf8')

  assert.match(source, /ref="progressAreaRef"/)
  assert.match(source, /window\.addEventListener\('pointermove', onWindowProgressPointerMove\)/)
  assert.match(source, /window\.addEventListener\('pointercancel', onWindowProgressPointerUp\)/)
  assert.match(
    source,
    /const onProgressPointerMove = \(e: PointerEvent\) => \{\s*if \(isScrubbing\.value\) return\s*updateProgressPreview\(e\)\s*\}/s
  )
  assert.match(source, /const stopProgressScrub = \(pointerId\?: number\) => \{/)
})
