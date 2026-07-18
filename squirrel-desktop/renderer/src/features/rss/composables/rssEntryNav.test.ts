import { describe, expect, it } from 'vitest'
import { nextEntryIndex } from './rssEntryNav'

describe('rss entry list navigation', () => {
  it('starts from the ends when nothing is selected', () => {
    expect(nextEntryIndex(5, -1, 1)).toBe(0)
    expect(nextEntryIndex(5, -1, -1)).toBe(4)
  })

  it('clamps within the list bounds', () => {
    expect(nextEntryIndex(5, 0, -1)).toBe(0)
    expect(nextEntryIndex(5, 4, 1)).toBe(4)
    expect(nextEntryIndex(5, 2, 1)).toBe(3)
  })

  it('returns -1 for empty lists', () => {
    expect(nextEntryIndex(0, -1, 1)).toBe(-1)
  })
})
