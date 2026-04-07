import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const historyItemPath = resolve(process.cwd(), 'src/components/history/HistoryItem.vue')
const historyItemSource = readFileSync(historyItemPath, 'utf8')

test('history item reuses the shared SubscriptionAvatar for channel fallbacks', () => {
  assert.match(historyItemSource, /import SubscriptionAvatar from ['"]@\/components\/common\/SubscriptionAvatar\.vue['"]/)
  assert.match(historyItemSource, /<SubscriptionAvatar[\s\S]*?class="history-item__avatar"/)
  assert.doesNotMatch(historyItemSource, /<img[^>]*class="history-item__avatar"/)
})
