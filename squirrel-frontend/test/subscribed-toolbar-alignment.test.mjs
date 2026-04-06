import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const filePath = new URL('../src/views/Subscribed.vue', import.meta.url)

test('subscribed toolbar aligns action buttons with the list content', async () => {
  const source = await readFile(filePath, 'utf8')

  assert.match(source, /<FeedToolbar[\s\S]*class="subscribed-toolbar"/)
  assert.match(source, /<Button size="xs" class="subscribed-toolbar__button whitespace-nowrap"/)
  assert.match(source, /<Button size="xs" variant="secondary" class="subscribed-toolbar__button subscribed-toolbar__button--secondary whitespace-nowrap"/)
  assert.match(source, /\.subscribed-toolbar\s*\{[\s\S]*padding:\s*1rem 0;/)
  assert.match(source, /\.subscribed-toolbar\s*:deep\(\.toolbar-slot-actions\)\s*\{[\s\S]*gap:\s*0\.5rem;/)
})
