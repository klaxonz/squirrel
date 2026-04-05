import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const read = async (relativePath) => {
  return readFile(new URL(relativePath, import.meta.url), 'utf8')
}

test('history view and item render playback time instead of video creation time', async () => {
  const historyViewSource = await read('../src/views/History.vue')
  const historyItemSource = await read('../src/components/history/HistoryItem.vue')

  assert.match(historyViewSource, /const timestamp = video\.played_at/)
  assert.doesNotMatch(historyViewSource, /const timestamp = video\.updated_at \|\| video\.created_at/)

  assert.match(historyItemSource, /formatLastWatchTime\(video\.played_at\)/)
  assert.doesNotMatch(historyItemSource, /formatLastWatchTime\(video\.updated_at \|\| video\.created_at\)/)
})
