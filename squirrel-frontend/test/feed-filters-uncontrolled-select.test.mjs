import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const read = async (relativePath) => {
  return readFile(new URL(relativePath, import.meta.url), 'utf8')
}

test('feed filters do not force Select open state to false', async () => {
  const [toolbarSelect, nsfwFilter, siteFilter, sortButton] = await Promise.all([
    read('../src/components/feed/ToolbarSelect.vue'),
    read('../src/components/feed/NsfwFilter.vue'),
    read('../src/components/feed/SiteFilter.vue'),
    read('../src/components/feed/SortButton.vue'),
  ])

  assert.ok(!toolbarSelect.includes(':open="open"'))
  assert.ok(!toolbarSelect.includes("@update:open"))
  assert.ok(!nsfwFilter.includes(':open="open"'))
  assert.ok(!siteFilter.includes(':open="open"'))
  assert.ok(!sortButton.includes(':open="open"'))
})
