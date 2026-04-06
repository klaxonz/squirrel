import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const videoPlayerPath = new URL('../src/components/video-player/VideoPlayer.vue', import.meta.url)

test('video player hides the poster for the current source after playback has started once', async () => {
  const source = await readFile(videoPlayerPath, 'utf8')

  assert.match(source, /const hidePosterForCurrentSource = ref\(false\)/)
  assert.match(source, /const effectivePoster = computed\(\(\) => hidePosterForCurrentSource\.value \? '' : \(props\.source\?\.poster \|\| props\.poster \|\| ''\)\)/)
  assert.match(source, /:poster="effectivePoster"/)
  assert.match(source, /if \(sourceChanged\) \{[\s\S]*hidePosterForCurrentSource\.value = false/)
  assert.match(source, /watch\(isPlaying, \(playing\) => \{[\s\S]*if \(playing\) \{\s*hidePosterForCurrentSource\.value = true/)
})
