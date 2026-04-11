import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const read = async (relativePath) => {
  return readFile(new URL(relativePath, import.meta.url), 'utf8')
}

test('history item uses an explicit loaded class for thumbnail visibility', async () => {
  const historyItemSource = await read('../src/components/history/HistoryItem.vue')

  assert.match(historyItemSource, /:class="\{\s*'image-loaded': imageLoaded\s*\}"/)
  assert.match(historyItemSource, /\.thumbnail-image\.image-loaded\s*\{/)
  assert.doesNotMatch(historyItemSource, /'opacity-100': imageLoaded/)
})
