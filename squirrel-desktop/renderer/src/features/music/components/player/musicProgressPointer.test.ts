import { describe, expect, it } from 'vitest'
import { pointerProgress } from './musicProgressPointer'

describe('music progress pointer geometry', () => {
  const rect = { left: 100, width: 200 }

  it('maps the left edge to 0 and the right edge to 1', () => {
    expect(pointerProgress(100, rect)).toBe(0)
    expect(pointerProgress(300, rect)).toBe(1)
  })

  it('clamps outside the rail and rejects empty geometry', () => {
    expect(pointerProgress(50, rect)).toBe(0)
    expect(pointerProgress(400, rect)).toBe(1)
    expect(pointerProgress(150, { left: 0, width: 0 })).toBe(0)
  })

  it('interpolates the mid-point of the rail', () => {
    expect(pointerProgress(200, rect)).toBe(0.5)
  })
})
