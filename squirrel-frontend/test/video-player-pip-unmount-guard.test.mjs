import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const videoPlayPath = new URL('../src/views/VideoPlay.vue', import.meta.url)

test('video play keeps the global playback session alive when native PiP is still attached during unmount', async () => {
  const source = await readFile(videoPlayPath, 'utf8')

  assert.match(source, /const hasActivePictureInPictureSession = \(\) => \{/)
  assert.match(source, /if \(globalVideoPlayerSession\.pictureInPicture\) \{/)
  assert.match(source, /return !!document\.pictureInPictureElement;/)
  assert.match(source, /if \(hasActivePictureInPictureSession\(\)\) \{\s*return;\s*\}/s)
})
