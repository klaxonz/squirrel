import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const read = async (relativePath) => {
  return readFile(new URL(relativePath, import.meta.url), 'utf8')
}

test('feed toolbar keeps primary actions on the left and filters on the right', async () => {
  const [toolbarSource, subscribedSource] = await Promise.all([
    read('../src/components/feed/FeedToolbar.vue'),
    read('../src/views/Subscribed.vue'),
  ])

  assert.ok(subscribedSource.includes('<template #actions>'))
  assert.ok(toolbarSource.includes('class="toolbar-primary"'))
  assert.ok(toolbarSource.includes('<slot name="actions"'))
  assert.ok(toolbarSource.includes('class="toolbar-actions"'))
  assert.ok(toolbarSource.indexOf('class="toolbar-primary"') < toolbarSource.indexOf('class="toolbar-actions"'))
})
