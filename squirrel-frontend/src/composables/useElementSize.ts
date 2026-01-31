import { onMounted, onUnmounted, ref, watch } from 'vue'
import type { Ref } from 'vue'

export function useElementSize(targetRef: Ref<HTMLElement | null>) {
  const width = ref(0)
  const height = ref(0)
  let observer: ResizeObserver | null = null

  const observe = () => {
    if (!targetRef.value) return
    observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const box = entry.contentRect
        width.value = Math.max(0, Math.floor(box.width))
        height.value = Math.max(0, Math.floor(box.height))
      }
    })
    observer.observe(targetRef.value)
  }

  onMounted(() => {
    observe()
  })

  onUnmounted(() => {
    if (observer) {
      observer.disconnect()
      observer = null
    }
  })

  watch(
    () => targetRef.value,
    () => {
      if (observer) {
        observer.disconnect()
        observer = null
      }
      observe()
    }
  )

  return { width, height }
}


