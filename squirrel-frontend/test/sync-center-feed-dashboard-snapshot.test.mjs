import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const read = async (relativePath) => {
  return readFile(new URL(relativePath, import.meta.url), 'utf8')
}

test('sync center feed lane data is loaded from one dashboard snapshot endpoint', async () => {
  const apiSource = await read('../src/api/subscriptionSyncCenter.ts')
  const centerSource = await read('../src/composables/useSyncCenter.ts')
  const viewSource = await read('../src/views/SyncCenter.vue')

  assert.match(apiSource, /export const getFeedDashboardSnapshot = async/)
  assert.match(apiSource, /\/api\/subscription\/sync-center\/feed-snapshot/)

  assert.match(centerSource, /getFeedDashboardSnapshot/)
  assert.match(centerSource, /const recentRuns = ref<SyncRunItem\[\]>\(\[\]\)/)
  assert.match(centerSource, /setRecentDateRange/)
  assert.match(centerSource, /recentRuns\.value = data\.recentRuns \|\| \[\]/)

  assert.match(viewSource, /recentRuns: feedRecentRuns/)
  assert.match(viewSource, /const feedRecentLaneRuns = ref/)
  assert.match(viewSource, /return \[\.\.\.feedRecentLaneRuns\.value\]/)
  assert.match(viewSource, /resolveFeedRecentLaneSnapshot\(/)
  assert.match(viewSource, /const syncFeedRecentWindow = \(\) => \{/)
  assert.match(viewSource, /syncFeedRecentWindow\(\)\s+await Promise\.all\(\[\s+overviewRefreshAll\(\),/)
  assert.doesNotMatch(viewSource, /historyLoadRuns/)
  assert.doesNotMatch(viewSource, /historyRefreshAll/)
})
