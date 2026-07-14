/** Shared geometry helpers for token-sized horizontal video rails. */

/** Inputs measured from the rendered horizontal media rail. */
export interface MediaRailGeometry {
  viewportWidth: number
  itemWidth: number
  gap: number
}

/**
 * Returns a whole-card page distance that never leaves a partially advanced
 * first card. CSS owns card width and gap; the component supplies measurements.
 */
export function calculateMediaRailPageDistance({
  viewportWidth,
  itemWidth,
  gap,
}: MediaRailGeometry): number {
  const safeViewport = Math.max(0, viewportWidth)
  const safeItemWidth = Math.max(0, itemWidth)
  const safeGap = Math.max(0, gap)

  if (safeItemWidth === 0) return safeViewport

  const itemStep = safeItemWidth + safeGap
  const visibleItems = Math.max(1, Math.floor((safeViewport + safeGap) / itemStep))
  return visibleItems * itemStep
}
