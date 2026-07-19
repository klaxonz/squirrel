export const MAIN_ROUTE_SCROLL_KEY = 'main'

export type RouteScrollPositions = Record<string, number>

const scrollElements = (root: HTMLElement): HTMLElement[] => {
  const elements = root.matches('[data-route-scroll]')
    ? [root]
    : []
  return [
    ...elements,
    ...Array.from(root.querySelectorAll<HTMLElement>('[data-route-scroll]')),
  ]
}

export function collectRouteScrollPositions(root: HTMLElement): RouteScrollPositions {
  const positions: RouteScrollPositions = {}
  for (const element of scrollElements(root)) {
    const key = element.dataset.routeScroll
    if (!key) continue
    positions[key] = element.scrollTop
  }
  return positions
}

/**
 * Apply every currently available position and report whether all targets are
 * reachable. A false result means async content has not made the scroll range
 * tall enough yet; the caller should retry after the DOM grows.
 */
export function applyRouteScrollPositions(
  root: HTMLElement,
  positions: RouteScrollPositions,
): boolean {
  const elementsByKey = new Map<string, HTMLElement>()
  for (const element of scrollElements(root)) {
    const key = element.dataset.routeScroll
    if (key && !elementsByKey.has(key)) elementsByKey.set(key, element)
  }

  let complete = true
  for (const [key, rawPosition] of Object.entries(positions)) {
    const element = elementsByKey.get(key)
    if (!element) {
      complete = false
      continue
    }

    const target = Math.max(0, rawPosition)
    element.scrollTop = target
    if (Math.abs(element.scrollTop - target) > 1) complete = false
  }
  return complete
}
