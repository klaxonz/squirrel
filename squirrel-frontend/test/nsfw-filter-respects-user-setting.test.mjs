import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const read = async (relativePath) => {
  return readFile(new URL(relativePath, import.meta.url), 'utf8')
}

test('nsfw filter hides itself and clears stale yes state when showNsfw is disabled', async () => {
  const source = await read('../src/components/feed/NsfwFilter.vue')

  assert.match(source, /v-if="loaded && settings\.showNsfw"/)
  assert.match(source, /modelValue === 'yes'/)
  assert.match(source, /emit\('update:modelValue', 'all'\)/)
})
