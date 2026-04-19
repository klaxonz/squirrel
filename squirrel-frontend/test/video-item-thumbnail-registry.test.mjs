import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const filePath = new URL('../src/components/feed/VideoItem.vue', import.meta.url)

test('video item reuses thumbnail registry state across remounts', async () => {
  const source = await readFile(filePath, 'utf8')

  assert.match(source, /import \{ useThumbnailRegistry \} from '\.\/useThumbnailRegistry'/)
  assert.match(source, /showFallback:\s*showThumbnailFallback/)
  assert.match(source, /const thumbnailSrc = computed\(\(\) =>/)
  assert.match(source, /useThumbnailRegistry\(thumbnailSrc\)/)
  assert.match(source, /v-if="thumbnailSrc && !showThumbnailFallback"/)
})

test('thumbnail registry only persists successful loads', async () => {
  const source = await readFile(new URL('../src/components/feed/useThumbnailRegistry.ts', import.meta.url), 'utf8')

  assert.match(source, /const loadedThumbnailRegistry = new Set<string>\(\)/)
  assert.match(source, /showFallback\.value = false/)
  assert.doesNotMatch(source, /'error'/)
})

test('video item uses native lazy image loading for feed thumbnails', async () => {
  const source = await readFile(filePath, 'utf8')

  assert.match(source, /loading="lazy"/)
  assert.match(source, /decoding="async"/)
  assert.match(source, /fetchpriority="low"/)
  assert.doesNotMatch(source, /\/api\/video\/thumbnail\?video_id=/)
})
