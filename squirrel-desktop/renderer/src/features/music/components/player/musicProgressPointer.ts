/**
 * Pure geometry helper for music progress scrubbing.
 * Kept free of DOM listeners so pointer handlers and tests share one formula.
 */
export function pointerProgress(clientX: number, rect: { left: number; width: number }): number {
  if (!Number.isFinite(clientX) || !Number.isFinite(rect.left) || !Number.isFinite(rect.width) || rect.width <= 0) {
    return 0
  }
  return Math.max(0, Math.min(1, (clientX - rect.left) / rect.width))
}
