import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

test('video play clip tab only uses persisted clip preview urls from the backend', async () => {
  const viewSource = await readFile(new URL('../src/views/VideoPlay.vue', import.meta.url), 'utf8')
  const typeSource = await readFile(new URL('../src/types/videoClipMarker.ts', import.meta.url), 'utf8')

  assert.match(typeSource, /preview_image_url\?: string \| null/)
  assert.match(viewSource, /v-if="marker\.preview_image_url"/)
  assert.match(viewSource, /:src="marker\.preview_image_url"/)
  assert.match(viewSource, /class="clip-row__thumb-fallback"/)
  assert.doesNotMatch(viewSource, /v-if="video\.value\?\.thumbnail"/)
  assert.doesNotMatch(viewSource, /v-if="playbackSource\.value\?\.poster"/)
})

test('video play clip tab supports renaming markers inline from the list', async () => {
  const viewSource = await readFile(new URL('../src/views/VideoPlay.vue', import.meta.url), 'utf8')

  assert.match(viewSource, /import \{ deleteVideoClipMarker, updateVideoClipMarker \} from '@\/api\/videoClipMarkers'/)
  assert.match(viewSource, /const startClipMarkerTitleEdit = async \(marker\) => \{/)
  assert.match(viewSource, /const commitClipMarkerTitle = async \(marker\) => \{/)
  assert.match(viewSource, /updateVideoClipMarker\(marker\.id, \{ title: nextTitle \}\)/)
  assert.match(viewSource, /data-clip-title-input="\$\{markerId\}"/)
  assert.match(viewSource, /Icon icon="lucide:pencil-line"/)
  assert.match(viewSource, /class="clip-row__title-input"/)
  assert.match(viewSource, /placeholder="命名片段"/)
  assert.doesNotMatch(viewSource, /getDefaultClipMarkerTitle/)
  assert.doesNotMatch(viewSource, /clip-row__thumb-dot/)
})
