import { ref, onMounted, onActivated, onBeforeUnmount, nextTick } from 'vue'
import { Logger } from '@/utils/logger'

const scrollPositions = new Map<string, number>()

export function useScrollPosition(key: string) {
  const scrollContainer = ref<HTMLElement | null>(null)

  // 保存滚动位置
  const saveScrollPosition = () => {
    if (scrollContainer.value) {
      const scrollTop = scrollContainer.value.scrollTop
      scrollPositions.set(key, scrollTop)
      try {
        localStorage.setItem(`scroll-${key}`, scrollTop.toString())
        Logger.debug(`[ScrollPosition] Saved position for ${key}`, scrollTop)
      } catch (_) {
      }
    }
  }
  
  const restoreScrollPosition = () => {
    if (!scrollContainer.value) return

    let position = 0

    if (scrollPositions.has(key)) {
      position = scrollPositions.get(key)
    } else {
      try {
        const saved = localStorage.getItem(`scroll-${key}`)
        if (saved) {
          position = parseInt(saved, 10)
        }
      } catch (_) {
      }
    }

    if (position > 0) {
      Logger.debug(`[ScrollPosition] Restoring position for ${key}`, position)
      const setScrollPosition = () => {
        if (scrollContainer.value) {
          scrollContainer.value.scrollTop = position
          Logger.debug(
            `[ScrollPosition] Set scroll position for ${key}`,
            { expected: position, actual: scrollContainer.value.scrollTop }
          )
        }
      }

      setScrollPosition()

      requestAnimationFrame(() => {
        setScrollPosition()
        requestAnimationFrame(() => {
          setScrollPosition()
          setTimeout(setScrollPosition, 50)
          setTimeout(setScrollPosition, 200)
          setTimeout(setScrollPosition, 500)
        })
      })
    }
  }
  
  const handleScroll = () => {
    saveScrollPosition()
  }
  
  const clearScrollPosition = () => {
    scrollPositions.delete(key)
  }
  
  onMounted(() => {
    nextTick(() => {
      restoreScrollPosition()
    })
  })
  
  onActivated(() => {
    nextTick(() => {
      restoreScrollPosition()
    })
  })
  
  onBeforeUnmount(() => {
    saveScrollPosition()
  })
  
  return {
    scrollContainer,
    handleScroll,
    saveScrollPosition,
    restoreScrollPosition,
    clearScrollPosition
  }
}
