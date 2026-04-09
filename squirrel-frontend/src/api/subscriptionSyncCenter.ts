export const getSyncCenterStreamUrl = (selectedRunId?: string | null) => {
  const params = new URLSearchParams()
  if (selectedRunId) {
    params.set('selectedRunId', selectedRunId)
  }
  const query = params.toString()
  return query ? `/api/subscription/sync-center/stream?${query}` : '/api/subscription/sync-center/stream'
}
