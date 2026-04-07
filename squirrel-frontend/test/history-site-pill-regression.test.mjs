import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const historyItemPath = resolve(process.cwd(), 'src/components/history/HistoryItem.vue')
const historyItemSource = readFileSync(historyItemPath, 'utf8')

test('history item no longer renders the site pill ahead of channel avatars', () => {
  assert.doesNotMatch(historyItemSource, /\{\{\s*displaySite\s*\}\}/)
  assert.doesNotMatch(historyItemSource, /const displaySite = computed\(/)
})
