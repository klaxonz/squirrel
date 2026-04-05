import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const read = async (relativePath) => readFile(new URL(relativePath, import.meta.url), 'utf8')

test('sync center is driven by one EventSource stream instead of a polling timer', async () => {
  const apiSource = await read('../src/api/subscriptionSyncCenter.ts')
  const viewSource = await read('../src/views/SyncCenter.vue')

  assert.match(apiSource, /export const getSyncCenterStreamUrl = \(/)
  assert.match(apiSource, /\/api\/subscription\/sync-center\/stream/)
  assert.match(viewSource, /let dashboardStream: EventSource \| null = null/)
  assert.match(viewSource, /new EventSource\(getSyncCenterStreamUrl\(/)
  assert.match(viewSource, /dashboardStream\.addEventListener\('feed_snapshot'/)
  assert.match(viewSource, /dashboardStream\.addEventListener\('extract_snapshot'/)
  assert.match(viewSource, /dashboardStream\.addEventListener\('run_detail'/)
  assert.doesNotMatch(viewSource, /const DASHBOARD_POLL_INTERVAL = 15000/)
  assert.doesNotMatch(viewSource, /setInterval\(/)
})
