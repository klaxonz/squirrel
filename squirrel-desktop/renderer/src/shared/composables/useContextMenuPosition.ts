import { nextTick, ref } from 'vue'

type Position = { x: number; y: number }

/**
 * Shared right-click / "…" menu positioning. Two pieces of behavior every context
 * menu in the app needed, previously copy-pasted byte-for-byte:
 *
 *  1. Clamp the menu inside the viewport horizontally (so a click near the right
 *     edge doesn't push the 200px-wide menu off-screen).
 *  2. After it renders, flip it up if it would overflow the bottom edge.
 *
 * The caller still owns its own visibility flag and target item ref — this only
 * owns the position math, which is the part that was duplicated.
 */
export function useContextMenuPosition(menuWidth = 200) {
  const position = ref<Position>({ x: 0, y: 0 })

  /**
   * Compute the initial position from a mouse event, then schedule the
   * bottom-overflow correction once the menu element is mounted.
   *
   * @param event  the click event that opened the menu
   * @param menuEl a ref to (or getter for) the menu element — needed to measure
   *               height for the overflow flip. May be null on the first tick;
   *               we re-read it inside `nextTick`.
   */
  const positionMenu = (event: MouseEvent, menuEl: (() => HTMLElement | null) | { value: HTMLElement | null }) => {
    let x = event.clientX
    const y = event.clientY

    if (x + menuWidth > window.innerWidth) {
      x = window.innerWidth - menuWidth - 8
    }
    position.value = { x, y }

    nextTick(() => {
      const el = typeof menuEl === 'function' ? menuEl() : menuEl.value
      if (!el) return
      const rect = el.getBoundingClientRect()
      if (rect.bottom > window.innerHeight) {
        position.value = { x, y: window.innerHeight - rect.height - 8 }
      }
    })
  }

  return { position, positionMenu }
}
