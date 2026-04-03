/**
 * @typedef {import('@/composables/useSyncCenter').SyncCenterItem} SyncCenterItem
 * @typedef {import('@/composables/useSyncHistory').SyncRunItem} SyncRunItem
 */

/**
 * @param {{
 *   previousActiveRunIds?: string[]
 *   nextActiveItems?: SyncCenterItem[]
 *   snapshotRecentRuns?: SyncRunItem[]
 *   currentLaneRuns?: SyncRunItem[]
 *   hasBaseline?: boolean
 *   maxRuns?: number
 * }} params
 * @returns {{
 *   nextActiveRunIds: string[]
 *   nextLaneRuns: SyncRunItem[]
 *   hasBaseline: boolean
 * }}
 */
export const resolveFeedRecentLaneSnapshot = ({
  previousActiveRunIds = [],
  nextActiveItems = [],
  snapshotRecentRuns = [],
  currentLaneRuns = [],
  hasBaseline = false,
  maxRuns = 8,
} = {}) => {
  if (!hasBaseline) {
    return {
      nextActiveRunIds: nextActiveItems.map((item) => item?.run_id).filter(Boolean),
      nextLaneRuns: [],
      hasBaseline: true,
    }
  }

  const nextActiveRunIdSet = new Set(nextActiveItems.map((item) => item?.run_id).filter(Boolean))
  const exitedRunIds = previousActiveRunIds.filter((runId) => runId && !nextActiveRunIdSet.has(runId))
  const snapshotRunById = new Map(snapshotRecentRuns.map((run) => [run.run_id, run]))
  const handoffRuns = exitedRunIds
    .map((runId) => snapshotRunById.get(runId))
    .filter(Boolean)

  const handoffRunIdSet = new Set(handoffRuns.map((run) => run.run_id))
  const nextLaneRuns = [
    ...handoffRuns,
    ...currentLaneRuns.filter((run) => run?.run_id && !handoffRunIdSet.has(run.run_id)),
  ].slice(0, maxRuns)

  return {
    nextActiveRunIds: Array.from(nextActiveRunIdSet),
    nextLaneRuns,
    hasBaseline: true,
  }
}
