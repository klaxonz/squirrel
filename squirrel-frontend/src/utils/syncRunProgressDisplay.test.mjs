import assert from 'node:assert/strict'
import test from 'node:test'

import {
  formatActiveRunProgress,
  formatRecentRunProgress,
} from './syncRunProgressDisplay.js'

test('formatActiveRunProgress hides feed-stage pseudo percentages', () => {
  assert.deepEqual(
    formatActiveRunProgress(
      {
        current_phase: 'enqueueing',
        progress_percent: 70,
        progress_label: '已入队 3',
      },
      'feed',
    ),
    {
      label: '已入队 3',
      showPercent: false,
      showRail: false,
    },
  )
})

test('formatActiveRunProgress hides percentages and rails for extracting lane too', () => {
  assert.deepEqual(
    formatActiveRunProgress(
      {
        current_phase: 'extracting',
        progress_percent: 60,
        progress_label: '3 / 5',
      },
      'extract',
    ),
    {
      label: '3 / 5',
      showPercent: false,
      showRail: false,
    },
  )
})

test('formatRecentRunProgress shows status result for terminal runs instead of percentages', () => {
  assert.deepEqual(
    formatRecentRunProgress({
      status: 'success',
      current_phase: 'completed',
      progress_percent: 100,
      progress_label: '8 / 8',
    }),
    {
      summaryText: '成功',
      showPercent: false,
    },
  )
})
