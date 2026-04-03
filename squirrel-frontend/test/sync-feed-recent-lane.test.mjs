import test from 'node:test'
import assert from 'node:assert/strict'
import { resolveFeedRecentLaneSnapshot } from '../src/utils/syncFeedRecentLane.js'

test('feed recent lane starts empty on the first snapshot and only accepts runs exiting the active lane', () => {
  const firstSnapshot = resolveFeedRecentLaneSnapshot({
    nextActiveItems: [
      { run_id: 'run-active-1' },
      { run_id: 'run-active-2' },
    ],
    snapshotRecentRuns: [
      { run_id: 'run-active-1' },
      { run_id: 'run-old-1' },
    ],
    hasBaseline: false,
  })

  assert.deepEqual(firstSnapshot.nextActiveRunIds, ['run-active-1', 'run-active-2'])
  assert.deepEqual(firstSnapshot.nextLaneRuns, [])
  assert.equal(firstSnapshot.hasBaseline, true)

  const secondSnapshot = resolveFeedRecentLaneSnapshot({
    previousActiveRunIds: firstSnapshot.nextActiveRunIds,
    nextActiveItems: [
      { run_id: 'run-active-2' },
      { run_id: 'run-active-3' },
    ],
    snapshotRecentRuns: [
      { run_id: 'run-old-1' },
      { run_id: 'run-active-1', status: 'running', current_phase: 'extracting' },
      { run_id: 'run-unrelated-latest', status: 'success', current_phase: 'completed' },
    ],
    currentLaneRuns: firstSnapshot.nextLaneRuns,
    hasBaseline: firstSnapshot.hasBaseline,
  })

  assert.deepEqual(secondSnapshot.nextActiveRunIds, ['run-active-2', 'run-active-3'])
  assert.deepEqual(
    secondSnapshot.nextLaneRuns.map((run) => run.run_id),
    ['run-active-1'],
  )
})
