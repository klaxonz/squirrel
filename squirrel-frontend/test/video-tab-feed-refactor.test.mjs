import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const filePath = new URL('../src/components/feed/VideoTab.vue', import.meta.url)

test('video tab passes raw videos through and derives a stable scroll cache key', async () => {
  const source = await readFile(filePath, 'utf8')

  assert.match(source, /:videos="videos"/)
  assert.match(source, /:scroll-cache-key="listScrollCacheKey"/)
  assert.match(source, /const listScrollCacheKey = computed\(\(\) =>/)
  assert.doesNotMatch(source, /processedVideos/)
  assert.doesNotMatch(source, /markRaw/)
})
