export function buildSyncCenterMountPlan(pipeline = 'feed') {
  const normalizedPipeline = pipeline === 'extract' ? 'extract' : 'feed'

  return {
    loadFeedDashboard: normalizedPipeline === 'feed',
    loadFeedItems: false,
    loadExtractionDashboard: normalizedPipeline === 'extract',
    loadHistoryOptions: false,
    loadSiteOptions: false,
  }
}

export function buildSyncCenterRefreshPlan({
  pipeline = 'feed',
  hasSelectedRun = false,
} = {}) {
  const normalizedPipeline = pipeline === 'extract' ? 'extract' : 'feed'

  return {
    loadFeedDashboard: normalizedPipeline === 'feed',
    loadFeedItems: false,
    loadExtractionDashboard: normalizedPipeline === 'extract',
    refreshSelectedRun: normalizedPipeline === 'feed' && Boolean(hasSelectedRun),
  }
}

export function shouldLoadExtractionDashboard({
  pipeline = 'feed',
  hasLoadedOnce = false,
} = {}) {
  return pipeline === 'extract' && !hasLoadedOnce
}
