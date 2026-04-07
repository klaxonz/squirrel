import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const read = async (relativePath) => {
  return readFile(new URL(relativePath, import.meta.url), 'utf8')
}

test('history view keeps empty state hidden until the first load finishes', async () => {
  const source = await read('../src/views/History.vue')

  assert.match(source, /const hasLoadedOnce = ref\(false\);/)
  assert.match(source, /v-else-if="hasLoadedOnce && groupedVideos.length === 0"/)
  assert.match(source, /hasLoadedOnce\.value = true;/)
})

test('history view resets the first-load guard before refetching the list', async () => {
  const source = await read('../src/views/History.vue')

  assert.match(source, /const resetHistoryList = \(\) => \{[\s\S]*?hasLoadedOnce\.value = false;/)
  assert.match(source, /const refreshList = async \(\) => \{[\s\S]*?resetHistoryList\(\)[\s\S]*?await loadMore\(\);/)
})

test('history view swaps content without out-in transition lag', async () => {
  const source = await read('../src/views/History.vue')

  assert.doesNotMatch(source, /<Transition name="fade-list" mode="out-in">/)
  assert.match(source, /<Transition name="fade-list">/)
})
