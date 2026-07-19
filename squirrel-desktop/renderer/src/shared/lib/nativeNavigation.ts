export type NativeNavigationDirection = 'back' | 'forward'
export type NativeNavigationSource = 'electron' | 'keyboard' | 'mouseup' | 'auxclick'

export function navigationDirectionForMouseButton(button: number): NativeNavigationDirection | null {
  if (button === 3) return 'back'
  if (button === 4) return 'forward'
  return null
}

/**
 * Chromium/Electron may expose one physical side-button press through both a
 * DOM mouse event and BrowserWindow's `app-command`. Suppress only duplicate
 * cross-source delivery; rapid presses arriving through the same source must
 * remain distinct navigation actions.
 */
export function createNativeNavigationDeduper(windowMs = 150) {
  let lastHandled: {
    direction: NativeNavigationDirection
    source: NativeNavigationSource
    timestamp: number
  } | null = null

  return (
    direction: NativeNavigationDirection,
    source: NativeNavigationSource,
    timestamp = performance.now(),
  ): boolean => {
    const duplicate = Boolean(
      lastHandled
      && lastHandled.direction === direction
      && lastHandled.source !== source
      && timestamp - lastHandled.timestamp >= 0
      && timestamp - lastHandled.timestamp < windowMs,
    )

    if (!duplicate) {
      lastHandled = { direction, source, timestamp }
    }
    return !duplicate
  }
}
