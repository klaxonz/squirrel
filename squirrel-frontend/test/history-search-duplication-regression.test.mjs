import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const read = async (relativePath) => {
  return readFile(new URL(relativePath, import.meta.url), 'utf8')
}

test('history view invalidates stale search loads and blocks concurrent loadMore calls', async () => {
  const source = await read('../src/views/History.vue')

  assert.match(source, /const loading = ref\(false\);/)
  assert.match(source, /const historyLoadVersion = ref\(0\);/)
  assert.match(source, /if \(allLoaded\.value \|\| loading\.value\) return;/)
  assert.match(source, /const requestedPage = currentPage\.value;/)
  assert.match(source, /const requestVersion = historyLoadVersion\.value;/)
  assert.match(source, /if \(requestVersion !== historyLoadVersion\.value\) \{\s*return;\s*\}/)
  assert.match(source, /historyLoadVersion\.value \+= 1;/)
  assert.match(source, /currentPage\.value = requestedPage \+ 1;/)
})
