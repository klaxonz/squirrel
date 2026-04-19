import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

test('video list pauses its resize observer while keep-alive is deactivated', async () => {
  const source = await readFile(new URL('../src/components/feed/VideoList.vue', import.meta.url), 'utf8')

  assert.match(source, /onActivated, onDeactivated/)
  assert.match(source, /const stopResizeObserver = \(\) =>/)
  assert.match(source, /onDeactivated\(stopResizeObserver\)/)
})

test('virtual list disconnects its resize observer while keep-alive is deactivated', async () => {
  const source = await readFile(new URL('../src/components/feed/VirtualList.vue', import.meta.url), 'utf8')

  assert.match(source, /onDeactivated/)
  assert.match(source, /const stopObservingContainer = \(\) =>/)
  assert.match(source, /onDeactivated\(\(\) => \{\s*stopObservingContainer\(\);\s*\}\);/s)
  assert.match(source, /onActivated\(\(\) => \{\s*nextTick\(\(\) => \{\s*observeContainer\(\)/s)
})
