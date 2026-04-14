import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

import {
  CLIP_MARKER_ACTIVE_TOLERANCE,
  createPointMarkerDraft,
  createSegmentMarkerDraft,
  isClipMarkerActive,
  isPointMarker,
  normalizeClipMarkerBounds,
  resolveClipMarkerVideoId,
} from '../src/components/video-player/runtime/clipMarkers.js'

test('clip marker runtime prefers explicit video id and falls back to source metadata', () => {
  assert.equal(resolveClipMarkerVideoId('42', { id: 7 }), '42')
  assert.equal(resolveClipMarkerVideoId(null, { id: 7 }), 7)
  assert.equal(resolveClipMarkerVideoId(null, { video_id: 'abc' }), 'abc')
  assert.equal(resolveClipMarkerVideoId(null, null), null)
})

test('point marker draft keeps the current time as a single time point', () => {
  assert.deepEqual(
    createPointMarkerDraft({ currentTime: 12, duration: 100 }),
    { startTime: 12, endTime: 12 }
  )
})

test('segment marker draft sorts and clamps its bounds', () => {
  assert.deepEqual(
    createSegmentMarkerDraft({ startTime: 98, currentTime: 102, duration: 100 }),
    { startTime: 98, endTime: 100 }
  )

  assert.deepEqual(
    normalizeClipMarkerBounds({ startTime: 40, endTime: 12, duration: 100 }),
    { startTime: 12, endTime: 40 }
  )
})

test('point marker detection distinguishes point and segment markers', () => {
  assert.equal(CLIP_MARKER_ACTIVE_TOLERANCE > 0, true)
  assert.equal(isPointMarker({ start_time: 12, end_time: 12 }), true)
  assert.equal(isPointMarker({ start_time: 12, end_time: 18 }), false)
  assert.equal(isClipMarkerActive({ start_time: 12, end_time: 12 }, 12.5), true)
  assert.equal(isClipMarkerActive({ start_time: 12, end_time: 12 }, 13), false)
  assert.equal(isClipMarkerActive({ start_time: 12, end_time: 18 }, 15), true)
})

test('player integration forwards video id and clip marker update events through the global host', async () => {
  const hostSource = await readFile(new URL('../src/components/video-player/GlobalVideoPlayerHost.vue', import.meta.url), 'utf8')
  assert.match(hostSource, /:video-id="globalVideoPlayerSession\.currentVideoId \|\| null"/)
  assert.match(hostSource, /@clipmarkersupdated="globalVideoPlayerSession\.handlers\.onClipMarkersUpdated\?\.\(\$event\)"/)

  const sessionSource = await readFile(new URL('../src/composables/useGlobalVideoPlayer.js', import.meta.url), 'utf8')
  assert.match(sessionSource, /onClipMarkersUpdated:\s*null/)

  const playerSource = await readFile(new URL('../src/components/video-player/VideoPlayer.vue', import.meta.url), 'utf8')
  assert.match(playerSource, /if \(e\.shiftKey\) \{/)
  assert.match(playerSource, /finishSegmentCapture\(\)/)
  assert.match(playerSource, /startSegmentCapture\(\)/)
  assert.match(playerSource, /markCurrentPoint\(\)/)
})

test('clip marker dragging uses window pointer events and keeps preview in reactive state', async () => {
  const playerSource = await readFile(new URL('../src/components/video-player/VideoPlayer.vue', import.meta.url), 'utf8')

  assert.match(playerSource, /pointerId: number/)
  assert.match(playerSource, /previewStart: number/)
  assert.match(playerSource, /previewEnd: number/)
  assert.match(playerSource, /window\.addEventListener\('pointermove', onWindowMarkerPointerMove\)/)
  assert.match(playerSource, /window\.addEventListener\('pointerup', onWindowMarkerPointerUp\)/)
  assert.match(playerSource, /window\.addEventListener\('pointercancel', onWindowMarkerPointerUp\)/)
  assert.match(playerSource, /d\.previewStart = newStart/)
  assert.match(playerSource, /d\.previewEnd = newEnd/)
  assert.match(playerSource, /const newStart = Math\.max\(0, Math\.min\(duration\.value, d\.previewStart\)\)/)
  assert.match(playerSource, /const dragPreview = draggingMarker\.value\?\.markerId === marker\.id/)
})

test('segment capture uses submit protection and no longer emits dead creation events', async () => {
  const playerSource = await readFile(new URL('../src/components/video-player/VideoPlayer.vue', import.meta.url), 'utf8')

  assert.match(
    playerSource,
    /const finishSegmentCapture = async \(\) => \{[\s\S]*isSavingMarker\.value = true[\s\S]*createVideoClipMarker\([\s\S]*finally \{[\s\S]*isSavingMarker\.value = false[\s\S]*\}/
  )
  assert.doesNotMatch(playerSource, /clipmarkercreated/)
  assert.match(playerSource, /isClipMarkerActive\(marker, currentTime\.value\)/)
})
