export const getSyncCenterHistoryWindow = (lens = '6h', now = new Date()) => {
  const end = new Date(now)
  const start = new Date(now)

  if (lens === '7d') {
    start.setDate(start.getDate() - 7)
    return { dateFrom: start.toISOString(), dateTo: end.toISOString() }
  }

  if (lens === '24h') {
    start.setHours(start.getHours() - 24)
    return { dateFrom: start.toISOString(), dateTo: end.toISOString() }
  }

  start.setHours(start.getHours() - 6)
  return { dateFrom: start.toISOString(), dateTo: end.toISOString() }
}
