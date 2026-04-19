import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const read = async (relativePath) => {
  return readFile(new URL(relativePath, import.meta.url), 'utf8')
}

test('latest videos no longer retains count-loading logic', async () => {
  const source = await read('../src/composables/useLatestVideos.ts')

  assert.doesNotMatch(source, /getVideoCounts/)
  assert.doesNotMatch(source, /videoCounts/)
  assert.doesNotMatch(source, /countsLoading/)
  assert.doesNotMatch(source, /loadVideoCounts/)
})

test('global search bar uses a slower debounce to avoid eager backend refreshes', async () => {
  const source = await read('../src/components/layout/GlobalSearchBar.vue')

  assert.match(source, /default:\s*500/)
})
