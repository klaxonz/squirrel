import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const read = async (relativePath) => {
  return readFile(new URL(relativePath, import.meta.url), 'utf8')
}

test('sync center drives all boards from one shared page-level refresh timer', async () => {
  const source = await read('../src/views/SyncCenter.vue')

  assert.match(source, /const DASHBOARD_POLL_INTERVAL = 15000/)
  assert.match(source, /let dashboardPollTimer: ReturnType<typeof setInterval> \| null = null/)
  assert.match(source, /setPollingEnabled\(false\)/)
  assert.match(source, /setHistoryPollingEnabled\(false\)/)
  assert.match(source, /setExtractionPollingEnabled\(false\)/)
  assert.match(source, /dashboardPollTimer = setInterval\(\(\) => \{\s+handleRefreshAll\(\)\s+\}, DASHBOARD_POLL_INTERVAL\)/)
})
