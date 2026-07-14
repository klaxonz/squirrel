/** Contract tests for viewport-sized, whole-card rail pagination. */
import { describe, expect, it } from 'vitest'
import { calculateMediaRailPageDistance } from './mediaRail'

describe('calculateMediaRailPageDistance', () => {
  it('advances by the number of whole cards visible in the viewport', () => {
    expect(calculateMediaRailPageDistance({
      viewportWidth: 1000,
      itemWidth: 288,
      gap: 20,
    })).toBe(924)
  })

  it('advances by at least one card when the viewport is narrower than a card', () => {
    expect(calculateMediaRailPageDistance({
      viewportWidth: 240,
      itemWidth: 288,
      gap: 20,
    })).toBe(308)
  })

  it('falls back to one viewport when no rendered item can be measured', () => {
    expect(calculateMediaRailPageDistance({
      viewportWidth: 840,
      itemWidth: 0,
      gap: 20,
    })).toBe(840)
  })
})
