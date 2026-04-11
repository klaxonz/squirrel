import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const read = async (relativePath) => {
  return readFile(new URL(relativePath, import.meta.url), 'utf8')
}

test('history items keep title content top-aligned instead of vertically centered', async () => {
  const source = await read('../src/components/history/HistoryItem.vue')

  assert.match(source, /\.history-item\s*\{[\s\S]*?align-items:\s*flex-start;/)
  assert.match(source, /\.actions-container\s*\{[\s\S]*?align-self:\s*flex-start;/)
})
