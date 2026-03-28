import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const filePath = new URL('../src/components/feed/VirtualList.vue', import.meta.url)

test('VirtualList does not animate visible window with transition-group', async () => {
  const source = await readFile(filePath, 'utf8')

  assert.ok(source.includes('class="visible-items"'))
  assert.ok(!source.includes('<transition-group'))
  assert.ok(!source.includes('.terminal-stagger-move'))
})
