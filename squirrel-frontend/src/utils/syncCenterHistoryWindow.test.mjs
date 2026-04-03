import test from 'node:test'
import assert from 'node:assert/strict'

import { getSyncCenterHistoryWindow } from './syncCenterHistoryWindow.js'

test('builds a rolling 6h window from current time', () => {
  const now = new Date('2026-04-03T00:30:00+08:00')
  const result = getSyncCenterHistoryWindow('6h', now)

  assert.equal(result.dateTo, '2026-04-02T16:30:00.000Z')
  assert.equal(result.dateFrom, '2026-04-02T10:30:00.000Z')
})

test('builds a rolling 24h window from current time', () => {
  const now = new Date('2026-04-03T00:30:00+08:00')
  const result = getSyncCenterHistoryWindow('24h', now)

  assert.equal(result.dateTo, '2026-04-02T16:30:00.000Z')
  assert.equal(result.dateFrom, '2026-04-01T16:30:00.000Z')
})

test('recomputes the window when now moves forward', () => {
  const first = getSyncCenterHistoryWindow('6h', new Date('2026-04-03T00:30:00+08:00'))
  const second = getSyncCenterHistoryWindow('6h', new Date('2026-04-03T00:45:00+08:00'))

  assert.notEqual(first.dateTo, second.dateTo)
  assert.equal(second.dateTo, '2026-04-02T16:45:00.000Z')
  assert.equal(second.dateFrom, '2026-04-02T10:45:00.000Z')
})
