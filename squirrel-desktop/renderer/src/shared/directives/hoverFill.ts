import type { Directive, DirectiveBinding } from 'vue'

/**
 * `v-hover-fill` — the shared hover wash ("跳跃").
 *
 * One absolutely-positioned layer travels between sibling items instead of
 * every item painting its own background. The layer is decoration only:
 * pointer-events are disabled, keyboard focus keeps its own ring, and
 * `prefers-reduced-motion` falls back to the items' static hover styles.
 *
 * Usage:
 *   <nav v-hover-fill>                       <!-- [data-hover-fill-item] -->
 *   <div v-hover-fill="{ item: 'a.row' }">
 *
 * The directive listens once on the scope, measures only on pointer movement,
 * and hides on scroll/resize so recycled virtual-list rows cannot leave a ghost.
 */

export interface HoverFillOptions {
  /** Item selector. Defaults to `[data-hover-fill-item]`. */
  item?: string
  /** Leave grace in ms. Defaults to 200. */
  leaveMs?: number
  /** Scale bump when the fill lands on a new item. Defaults to 1.02. */
  scale?: number
}

const DEFAULT_ITEM = '[data-hover-fill-item]'
const FILL_CLASS = 'app-hover-fill'
const ACTIVE_ATTR = 'data-hover-fill-active'

type Timer = ReturnType<typeof setTimeout>

interface HoverFillState {
  fill: HTMLElement
  itemSelector: string
  leaveMs: number
  scale: number
  activeItem: HTMLElement | null
  hideTimer: Timer | null
  scaleTimer: Timer | null
  hasShown: boolean
  observer: ResizeObserver | null
  onPointerOver: (event: PointerEvent) => void
  onPointerLeave: () => void
  onScroll: () => void
  onFocusIn: () => void
}

const states = new WeakMap<HTMLElement, HoverFillState>()

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value))

const reducedMotion = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false

const hide = (scope: HTMLElement, state: HoverFillState, immediate = false) => {
  if (state.hideTimer) {
    clearTimeout(state.hideTimer)
    state.hideTimer = null
  }
  if (immediate) {
    state.fill.classList.remove('is-visible')
    scope.removeAttribute(ACTIVE_ATTR)
    state.activeItem = null
    return
  }
  state.hideTimer = setTimeout(() => {
    state.fill.classList.remove('is-visible')
    scope.removeAttribute(ACTIVE_ATTR)
    state.activeItem = null
    state.hideTimer = null
  }, state.leaveMs)
}

const measure = (scope: HTMLElement, state: HoverFillState, item: HTMLElement, event: PointerEvent) => {
  const scopeRect = scope.getBoundingClientRect()
  const itemRect = item.getBoundingClientRect()
  if (itemRect.width === 0 || itemRect.height === 0) return

  const fill = state.fill
  const x = itemRect.left - scopeRect.left
  const y = itemRect.top - scopeRect.top
  const originX = clamp(((event.clientX - itemRect.left) / itemRect.width) * 100, 0, 100)
  const originY = clamp(((event.clientY - itemRect.top) / itemRect.height) * 100, 0, 100)

  fill.style.setProperty('--hf-x', `${x}px`)
  fill.style.setProperty('--hf-y', `${y}px`)
  fill.style.setProperty('--hf-w', `${itemRect.width}px`)
  fill.style.setProperty('--hf-h', `${itemRect.height}px`)
  fill.style.setProperty('--hf-origin-x', `${originX}%`)
  fill.style.setProperty('--hf-origin-y', `${originY}%`)
  fill.style.borderRadius = getComputedStyle(item).borderRadius || ''

  if (!state.hasShown) {
    // First reveal: place the layer without animating in from the top-left.
    fill.style.transition = 'none'
    void fill.offsetWidth
    fill.style.transition = ''
    state.hasShown = true
  }

  fill.style.setProperty('--hf-scale', String(state.scale))
  if (state.scaleTimer) clearTimeout(state.scaleTimer)
  state.scaleTimer = setTimeout(() => {
    fill.style.setProperty('--hf-scale', '1')
    state.scaleTimer = null
  }, 220)

  fill.classList.add('is-visible')
  scope.setAttribute(ACTIVE_ATTR, '')
  state.activeItem = item
}

const setup = (scope: HTMLElement, binding: DirectiveBinding<HoverFillOptions | undefined>) => {
  scope.classList.add('app-hover-fill-scope')

  if (reducedMotion()) return

  const fill = document.createElement('span')
  fill.className = FILL_CLASS
  fill.setAttribute('aria-hidden', 'true')
  scope.prepend(fill)

  const state: HoverFillState = {
    fill,
    itemSelector: binding.value?.item || DEFAULT_ITEM,
    leaveMs: binding.value?.leaveMs ?? 200,
    scale: binding.value?.scale ?? 1.02,
    activeItem: null,
    hideTimer: null,
    scaleTimer: null,
    hasShown: false,
    observer: null,
    onPointerOver: (event) => {
      if (event.pointerType !== 'mouse') return
      const target = event.target
      if (!(target instanceof Element)) return
      const item = target.closest<HTMLElement>(state.itemSelector)
      if (!item || !scope.contains(item) || item === state.activeItem) return
      if (state.hideTimer) {
        clearTimeout(state.hideTimer)
        state.hideTimer = null
      }
      measure(scope, state, item, event)
    },
    onPointerLeave: () => hide(scope, state),
    onScroll: () => hide(scope, state, true),
    onFocusIn: () => {
      // Keyboard focus gets the item's focus ring, not the pointer wash.
      if (!scope.matches(':hover')) hide(scope, state, true)
    },
  }

  scope.addEventListener('pointerover', state.onPointerOver)
  scope.addEventListener('pointerleave', state.onPointerLeave)
  scope.addEventListener('focusin', state.onFocusIn)
  window.addEventListener('scroll', state.onScroll, { capture: true, passive: true })

  if (typeof ResizeObserver !== 'undefined') {
    state.observer = new ResizeObserver(() => hide(scope, state, true))
    state.observer.observe(scope)
  }

  states.set(scope, state)
}

const teardown = (scope: HTMLElement) => {
  const state = states.get(scope)
  if (!state) return

  scope.removeEventListener('pointerover', state.onPointerOver)
  scope.removeEventListener('pointerleave', state.onPointerLeave)
  scope.removeEventListener('focusin', state.onFocusIn)
  window.removeEventListener('scroll', state.onScroll, { capture: true })
  state.observer?.disconnect()
  if (state.hideTimer) clearTimeout(state.hideTimer)
  if (state.scaleTimer) clearTimeout(state.scaleTimer)
  state.fill.remove()
  scope.removeAttribute(ACTIVE_ATTR)
  scope.classList.remove('app-hover-fill-scope')
  states.delete(scope)
}

export const hoverFill: Directive<HTMLElement, HoverFillOptions | undefined> = {
  mounted(scope, binding) {
    setup(scope, binding)
  },
  updated(scope, binding) {
    const previous = states.get(scope)
    const nextSelector = binding.value?.item || DEFAULT_ITEM
    if (previous && previous.itemSelector !== nextSelector) {
      teardown(scope)
      setup(scope, binding)
    }
  },
  unmounted(scope) {
    teardown(scope)
  },
}

declare module 'vue' {
  export interface GlobalDirectives {
    vHoverFill: typeof hoverFill
  }
}
