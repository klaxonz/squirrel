import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const read = async (relativePath) => {
  return readFile(new URL(relativePath, import.meta.url), 'utf8')
}

test('filter modal only applies local selections when confirm is clicked', async () => {
  const source = await read('../src/components/feed/FilterModal.vue')

  assert.ok(!source.includes("watch(localTimeRange, (v) => emit('update:timeRange', v))"))
  assert.ok(!source.includes("watch(localDuration, (v) => emit('update:duration', v))"))
  assert.ok(!source.includes("watch(localContentType, (v) => emit('update:contentType', v))"))
  assert.ok(!source.includes("watch(localNsfw, (v) => emit('update:nsfw', v))"))
  assert.ok(!source.includes("watch(localSite, (v) => emit('update:site', v))"))
  assert.ok(!source.includes("watch(localSortBy, (v) => emit('update:sortBy', v))"))
  assert.match(
    source,
    /const confirm = \(\) => \{[\s\S]*emit\('update:timeRange', localTimeRange\.value\)[\s\S]*emit\('update:duration', localDuration\.value\)[\s\S]*emit\('update:contentType', localContentType\.value\)[\s\S]*emit\('update:nsfw', localNsfw\.value\)[\s\S]*emit\('update:site', localSite\.value\)[\s\S]*emit\('update:sortBy', localSortBy\.value\)[\s\S]*emit\('update:modelValue', false\)[\s\S]*\}/,
  )
})
