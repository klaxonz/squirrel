import { beforeEach, describe, expect, it } from 'vitest'

import {
  __clearPendingPositionsForTests,
  consumePendingPosition,
  peekPendingPosition,
  rememberPendingPosition,
} from './playbackPositionBuffer'

describe('playbackPositionBuffer', () => {
  beforeEach(() => {
    __clearPendingPositionsForTests()
  })

  it('remembers the highest position per video id (string/number normalized)', () => {
    rememberPendingPosition(1, 5)
    rememberPendingPosition('1', 12)
    rememberPendingPosition(1, 3)

    expect(peekPendingPosition(1)).toBe(12)
    expect(peekPendingPosition('1')).toBe(12)
  })

  it('ignores missing ids and non-positive positions', () => {
    rememberPendingPosition(null, 10)
    rememberPendingPosition(undefined, 10)
    rememberPendingPosition(1, 0)
    rememberPendingPosition(1, -1)

    expect(peekPendingPosition(1)).toBeNull()
  })

  it('consumes an entry exactly once', () => {
    rememberPendingPosition(1, 10)

    expect(consumePendingPosition(1)).toBe(10)
    expect(consumePendingPosition(1)).toBeNull()
    expect(peekPendingPosition(1)).toBeNull()
  })

  it('evicts the oldest entries beyond the cap', () => {
    for (let i = 1; i <= 25; i += 1) {
      rememberPendingPosition(i, i)
    }

    expect(peekPendingPosition(1)).toBeNull()
    expect(peekPendingPosition(6)).toBe(6)
    expect(peekPendingPosition(25)).toBe(25)
  })
})
