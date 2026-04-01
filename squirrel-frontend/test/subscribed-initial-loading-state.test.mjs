import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const read = async (relativePath) => {
  return readFile(new URL(relativePath, import.meta.url), 'utf8')
}

test('subscribed view keeps empty state hidden until first load finishes', async () => {
  const source = await read('../src/views/Subscribed.vue')

  assert.match(source, /const hasLoadedOnce = ref\(false\)/)
  assert.match(source, /v-else-if="hasLoadedOnce && !loading && !subscriptions\.length"/)
  assert.match(source, /hasLoadedOnce\.value = true/)
})
