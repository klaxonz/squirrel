import assert from 'node:assert/strict'
import test from 'node:test'

import {
  buildSyncCenterMountPlan,
  buildSyncCenterRefreshPlan,
  shouldLoadExtractionDashboard,
} from './syncCenterPageLoadPlan.js'

test('buildSyncCenterMountPlan keeps default feed entrypoint lean', () => {
  assert.deepEqual(buildSyncCenterMountPlan(), {
    loadFeedDashboard: true,
    loadFeedItems: false,
    loadExtractionDashboard: false,
    loadHistoryOptions: false,
    loadSiteOptions: false,
  })
})

test('buildSyncCenterRefreshPlan only refreshes selected run detail for feed pipeline', () => {
  assert.deepEqual(
    buildSyncCenterRefreshPlan({
      pipeline: 'feed',
      hasSelectedRun: true,
    }),
    {
      loadFeedDashboard: true,
      loadFeedItems: false,
      loadExtractionDashboard: false,
      refreshSelectedRun: true,
    },
  )
})

test('shouldLoadExtractionDashboard only loads extract data on first extract entry', () => {
  assert.equal(
    shouldLoadExtractionDashboard({
      pipeline: 'feed',
      hasLoadedOnce: false,
    }),
    false,
  )
  assert.equal(
    shouldLoadExtractionDashboard({
      pipeline: 'extract',
      hasLoadedOnce: false,
    }),
    true,
  )
  assert.equal(
    shouldLoadExtractionDashboard({
      pipeline: 'extract',
      hasLoadedOnce: true,
    }),
    false,
  )
})
