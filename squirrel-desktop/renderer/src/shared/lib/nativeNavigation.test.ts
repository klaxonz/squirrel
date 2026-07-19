import { describe, expect, it } from 'vitest'

import {
  createNativeNavigationDeduper,
  navigationDirectionForMouseButton,
} from './nativeNavigation'

describe('native navigation input', () => {
  it('maps standard mouse back and forward buttons', () => {
    expect(navigationDirectionForMouseButton(3)).toBe('back')
    expect(navigationDirectionForMouseButton(4)).toBe('forward')
    expect(navigationDirectionForMouseButton(0)).toBeNull()
    expect(navigationDirectionForMouseButton(1)).toBeNull()
    expect(navigationDirectionForMouseButton(2)).toBeNull()
  })

  it('deduplicates one physical press reported by Electron and the DOM', () => {
    const shouldHandle = createNativeNavigationDeduper(150)

    expect(shouldHandle('back', 'electron', 1_000)).toBe(true)
    expect(shouldHandle('back', 'keyboard', 1_010)).toBe(false)
    expect(shouldHandle('back', 'mouseup', 1_020)).toBe(false)
    expect(shouldHandle('back', 'auxclick', 1_030)).toBe(false)
  })

  it('keeps repeated events from the same source and later presses', () => {
    const shouldHandle = createNativeNavigationDeduper(150)

    expect(shouldHandle('back', 'mouseup', 1_000)).toBe(true)
    expect(shouldHandle('back', 'mouseup', 1_040)).toBe(true)
    expect(shouldHandle('forward', 'electron', 1_060)).toBe(true)
    expect(shouldHandle('back', 'electron', 1_300)).toBe(true)
  })
})
