import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const read = async (relativePath) => {
  return readFile(new URL(relativePath, import.meta.url), 'utf8')
}

test('video tab only reloads when filters actually change after activation', async () => {
  const source = await read('../src/components/feed/VideoTab.vue')

  assert.match(source, /const lastAppliedFilterSignature = ref\(''\)/)
  assert.match(source, /const createFilterSignature = \(filters\) =>/)
  assert.match(
    source,
    /if \(!lastAppliedFilterSignature\.value\) \{[\s\S]*lastAppliedFilterSignature\.value = nextSignature[\s\S]*handleSearch\(\)[\s\S]*return[\s\S]*\}/,
  )
  assert.match(
    source,
    /if \(nextSignature === lastAppliedFilterSignature\.value\) \{[\s\S]*return[\s\S]*\}/,
  )
  assert.match(
    source,
    /lastAppliedFilterSignature\.value = nextSignature[\s\S]*handleSearch\(\)/,
  )
})
