/**
 * Resolve the app's primary vertical scroll container.
 *
 * Defined once in `AppLayout.vue` as `<div id="app-main-scroll">`, this is the
 * element that IntersectionObserver-based infinite lists must pass as `root` so
 * their sentinel triggers on the right viewport rather than the window.
 *
 * Centralizing the lookup here means only one place in the codebase knows the
 * element id — call sites read as intent (`getMainScrollRoot()`) instead of a
 * magic-string `getElementById`. Returns `null` if the layout isn't mounted
 * (e.g. during SSR / tests); callers should treat that as "observe the window".
 */
export const MAIN_SCROLL_ID = 'app-main-scroll'

export function getMainScrollRoot(): HTMLElement | null {
  return document.getElementById(MAIN_SCROLL_ID)
}
