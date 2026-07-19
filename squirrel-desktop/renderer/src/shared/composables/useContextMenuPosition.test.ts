// @vitest-environment jsdom
import { afterEach, describe, expect, it } from 'vitest'
import { useContextMenuPosition } from './useContextMenuPosition'

afterEach(() => {
  document.body.replaceChildren()
})

describe('useContextMenuPosition', () => {
  it('focuses the context-menu trigger and records the pointer position', () => {
    const trigger = document.createElement('button')
    document.body.append(trigger)
    const { position, positionMenu } = useContextMenuPosition()

    trigger.addEventListener('contextmenu', (event) => {
      positionMenu(event, { value: null })
    })
    trigger.dispatchEvent(new MouseEvent('contextmenu', {
      bubbles: true,
      clientX: 32,
      clientY: 48,
    }))

    expect(document.activeElement).toBe(trigger)
    expect(position.value).toEqual({ x: 32, y: 48 })
  })
})
