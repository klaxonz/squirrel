import { beforeEach, describe, expect, it } from 'vitest'

import {
  currentEntry,
  patchEntry,
  pushEntry,
  reset,
  stepBack,
} from './navigationHistory'

const makeEntry = (fullPath: string, name: string) => ({
  fullPath,
  name,
  title: name,
  breadcrumbs: [],
  sectionLabel: '',
  scrollY: 0,
})

describe('navigation history scroll positions', () => {
  beforeEach(() => {
    reset()
  })

  it('can save a list offset after navigation without overwriting the player entry', () => {
    const listEntry = pushEntry(makeEntry('/videos/all', 'AllVideos'))
    const playerEntry = pushEntry(makeEntry('/video/42', 'VideoPlay'))

    expect(patchEntry(listEntry.id, { scrollY: 1280 })).toBe(true)
    expect(currentEntry()).toMatchObject({ id: playerEntry.id, scrollY: 0 })

    expect(stepBack()).toMatchObject({ id: listEntry.id, scrollY: 1280 })
  })

  it('keeps nested list positions on the originating history entry', () => {
    const listEntry = pushEntry(makeEntry('/subscribed', 'Subscribed'))
    pushEntry(makeEntry('/video/42', 'VideoPlay'))

    expect(patchEntry(listEntry.id, {
      scrollY: 0,
      scrollPositions: {
        main: 0,
        'subscribed-content': 960,
      },
    })).toBe(true)

    expect(stepBack()).toMatchObject({
      id: listEntry.id,
      scrollPositions: {
        main: 0,
        'subscribed-content': 960,
      },
    })
  })

  it('ignores a targeted save after its entry has been discarded', () => {
    const discardedEntry = pushEntry(makeEntry('/videos/all', 'AllVideos'))
    reset()

    expect(patchEntry(discardedEntry.id, { scrollY: 1280 })).toBe(false)
    expect(currentEntry()).toBeNull()
  })
})
