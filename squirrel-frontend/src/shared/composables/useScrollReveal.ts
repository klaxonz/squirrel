import { onMounted, onUnmounted, watch, type Ref } from 'vue'
import { getMainScrollRoot } from '@/shared/composables/useMainScrollRoot'

export interface UseScrollRevealOptions {
  selector?: string
  rootMargin?: string
  threshold?: number
  once?: boolean
}

export function useScrollReveal(
  container: Ref<HTMLElement | null>,
  options: UseScrollRevealOptions = {},
): void {
  const {
    selector = '.app-reveal',
    rootMargin = '0px 0px -10% 0px',
    threshold = 0,
    once = true,
  } = options

  let observer: IntersectionObserver | null = null
  let mo: MutationObserver | null = null

  const reveal = (el: Element) => el.classList.add('is-visible')

  const observe = (el: Element) => observer?.observe(el)

  const bind = () => {
    observer?.disconnect()
    observer = null
    mo?.disconnect()
    mo = null

    const root = container.value
    if (!root) return

    observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            reveal(entry.target)
            if (once) observer?.unobserve(entry.target)
          } else if (!once) {
            entry.target.classList.remove('is-visible')
          }
        }
      },
      { root: getMainScrollRoot(), rootMargin, threshold },
    )

    for (const el of root.querySelectorAll<HTMLElement>(selector)) observe(el)

    mo = new MutationObserver((mutations) => {
      for (const m of mutations) {
        for (const node of m.addedNodes) {
          if (!(node instanceof HTMLElement)) continue
          if (node.matches?.(selector)) observe(node)
          for (const el of node.querySelectorAll<HTMLElement>(selector)) observe(el)
        }
      }
    })
    mo.observe(root, { childList: true, subtree: true })
  }

  onMounted(bind)
  watch(container, bind)
  onUnmounted(() => {
    observer?.disconnect()
    mo?.disconnect()
  })
}
