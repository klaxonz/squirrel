import assert from 'node:assert/strict'
import test from 'node:test'

import { loadFileCache } from '../src/shared/file-cache.mjs'

test('desktop file cache treats missing files as cache misses without debug noise', async () => {
  const debug = console.debug
  const messages = []
  console.debug = (...args) => messages.push(args)

  try {
    const value = await loadFileCache(`missing-cache-${Date.now()}-${Math.random()}`)

    assert.equal(value, null)
    assert.deepEqual(messages, [])
  } finally {
    console.debug = debug
  }
})
