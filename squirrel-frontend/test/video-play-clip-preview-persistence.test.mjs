import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

test('video play clip tab only uses persisted clip preview urls from the backend', async () => {
  const viewSource = await readFile(new URL('../src/views/VideoPlay.vue', import.meta.url), 'utf8')
  const typeSource = await readFile(new URL('../src/types/videoClipMarker.ts', import.meta.url), 'utf8')

  assert.match(typeSource, /preview_image_url\?: string \| null/)
  assert.match(viewSource, /v-if="marker\.preview_image_url"/)
  assert.match(viewSource, /:src="marker\.preview_image_url"/)
  assert.match(viewSource, /Icon icon="lucide:image-off"/)
  assert.doesNotMatch(viewSource, /v-if="video\.value\?\.thumbnail"/)
  assert.doesNotMatch(viewSource, /v-if="playbackSource\.value\?\.poster"/)
})
