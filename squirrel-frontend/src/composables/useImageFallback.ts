import { ref } from 'vue'

type Identifier = string | number
type MaybeIdentifier = Identifier | null | undefined

export function useImageFallback(defaultImage = '/squirrel-icon.svg') {
  const failedImages = ref(new Set<Identifier>())

  const handleImageError = (event: Event | null | undefined, identifier?: MaybeIdentifier) => {
    if (identifier !== undefined && identifier !== null) {
      failedImages.value.add(identifier)
    }

    const target = event?.target
    if (target instanceof HTMLImageElement) {
      target.src = defaultImage
    }
  }

  const getImageSrc = (src: unknown, identifier?: MaybeIdentifier) => {
    if (identifier !== undefined && identifier !== null && failedImages.value.has(identifier)) {
      return defaultImage
    }

    if (typeof src !== 'string') {
      return src ? String(src) : defaultImage
    }

    const trimmed = src.trim()
    return trimmed ? trimmed : defaultImage
  }

  const hasError = (identifier: Identifier) => {
    return failedImages.value.has(identifier)
  }

  const reset = () => {
    failedImages.value.clear()
  }

  return {
    failedImages,
    handleImageError,
    getImageSrc,
    hasError,
    reset,
  }
}
