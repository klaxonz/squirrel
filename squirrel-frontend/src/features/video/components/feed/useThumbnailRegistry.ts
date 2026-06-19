import { ref, watch, type MaybeRefOrGetter } from 'vue'
import { toValue } from '@vueuse/core'

const MAX_ENTRIES = 500
const loadedThumbnailRegistry = new Set<string>()

const rememberLoadedThumbnail = (src: string): void => {
  if (!src) {
    return
  }

  if (loadedThumbnailRegistry.has(src)) {
    loadedThumbnailRegistry.delete(src)
  }

  loadedThumbnailRegistry.add(src)

  if (loadedThumbnailRegistry.size > MAX_ENTRIES) {
    const oldestKey = loadedThumbnailRegistry.values().next().value
    if (oldestKey) {
      loadedThumbnailRegistry.delete(oldestKey)
    }
  }
}

export const useThumbnailRegistry = (src: MaybeRefOrGetter<string | null | undefined>) => {
  const imageLoaded = ref(false)
  const showFallback = ref(false)

  const syncFromRegistry = (nextSrc: string | null | undefined): void => {
    imageLoaded.value = !!nextSrc && loadedThumbnailRegistry.has(nextSrc)
    showFallback.value = false
  }

  const handleLoad = (): void => {
    const currentSrc = toValue(src)
    imageLoaded.value = true
    showFallback.value = false
    if (currentSrc) {
      rememberLoadedThumbnail(currentSrc)
    }
  }

  const handleError = (): void => {
    imageLoaded.value = false
    showFallback.value = true
  }

  watch(
    () => toValue(src),
    (nextSrc) => {
      syncFromRegistry(nextSrc)
    },
    { immediate: true },
  )

  return {
    imageLoaded,
    showFallback,
    handleLoad,
    handleError,
  }
}
