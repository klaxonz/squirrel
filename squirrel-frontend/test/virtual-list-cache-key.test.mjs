import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const filePath = new URL('../src/components/feed/VirtualList.vue', import.meta.url)

test('virtual list supports explicit cache keys for scroll restoration', async () => {
  const source = await readFile(filePath, 'utf8')

  assert.match(source, /cacheKey:\s*\{\s*type:\s*String,/)
  assert.match(source, /const scrollPositions = new Map\(\)/)
  assert.match(source, /const getScrollCacheKey = \(\) =>/)
  assert.match(source, /if \(!props\.cacheKey\) \{\s*scrollPositions\.delete\(instanceId\.value\);/s)
})
