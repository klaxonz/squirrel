import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const read = async (relativePath) => {
  return readFile(new URL(relativePath, import.meta.url), 'utf8')
}

test('history date header stays above thumbnail progress bars while scrolling', async () => {
  const [historyViewSource, historyItemSource] = await Promise.all([
    read('../src/views/History.vue'),
    read('../src/components/history/HistoryItem.vue'),
  ])

  assert.match(historyViewSource, /\.history-date-header\s*\{[\s\S]*?z-index:\s*10;/)
  assert.match(historyItemSource, /\.progress-bar\s*\{[\s\S]*?z-index:\s*1;/)
})
