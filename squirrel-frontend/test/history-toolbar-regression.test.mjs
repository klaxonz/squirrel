import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const read = async (relativePath) => {
  return readFile(new URL(relativePath, import.meta.url), 'utf8')
}

test('history view relies on global search instead of rendering a local toolbar search input', async () => {
  const source = await read('../src/views/History.vue')

  assert.doesNotMatch(source, /placeholder="搜索历史\.\.\."/)
  assert.doesNotMatch(source, /aria-label="搜索历史记录"/)
  assert.doesNotMatch(source, /const clearSearch = \(\) =>/)
  assert.match(source, /emitter\?\.on\?\.\('search:history', \(query\) =>/)
  assert.match(source, /query: searchQuery\.value/)
})

test('history date header keeps the same base style for every day group', async () => {
  const source = await read('../src/views/History.vue')

  assert.match(source, /\.history-date-header\s*\{[\s\S]*?background: hsl\(var\(--background\)\);/)
  assert.doesNotMatch(source, /:class="\{ 'is-today': group\.isToday, 'is-yesterday': group\.isYesterday \}"/)
  assert.doesNotMatch(source, /\.history-date-header\.is-today/)
  assert.doesNotMatch(source, /\.history-date-header\.is-yesterday/)
})
