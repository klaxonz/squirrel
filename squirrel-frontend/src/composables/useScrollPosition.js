import { ref, onMounted, onActivated, onBeforeUnmount, nextTick } from 'vue'
import { Logger } from '../utils/logger'

// 全局存储滚动位置
const scrollPositions = new Map()

/**
 * 滚动位置保持 composable
 * @param {string} key - 唯一标识符，用于区分不同的滚动容器
 * @returns {Object} 包含滚动容器ref和相关方法的对象
 */
export function useScrollPosition(key) {
  const scrollContainer = ref(null)

  // 保存滚动位置
  const saveScrollPosition = () => {
    if (scrollContainer.value) {
      const scrollTop = scrollContainer.value.scrollTop
      scrollPositions.set(key, scrollTop)
      // 同时保存到 localStorage 作为备份
      try {
        localStorage.setItem(`scroll-${key}`, scrollTop.toString())
        Logger.debug(`[ScrollPosition] Saved position for ${key}`, scrollTop)
      } catch (e) {
        // 忽略 localStorage 错误
      }
    }
  }
  
  // 恢复滚动位置
  const restoreScrollPosition = () => {
    if (!scrollContainer.value) return

    let position = 0

    // 优先从内存中获取位置
    if (scrollPositions.has(key)) {
      position = scrollPositions.get(key)
    } else {
      // 从 localStorage 获取备份位置
      try {
        const saved = localStorage.getItem(`scroll-${key}`)
        if (saved) {
          position = parseInt(saved, 10)
        }
      } catch (e) {
        // 忽略 localStorage 错误
      }
    }

    if (position > 0) {
      Logger.debug(`[ScrollPosition] Restoring position for ${key}`, position)
      // 多次尝试设置滚动位置，确保内容加载完成后能正确恢复
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

      // 使用多个 requestAnimationFrame 确保位置正确设置
      requestAnimationFrame(() => {
        setScrollPosition()
        requestAnimationFrame(() => {
          setScrollPosition()
          // 再延迟一点时间确保设置成功
          setTimeout(setScrollPosition, 50)
          setTimeout(setScrollPosition, 200)
          setTimeout(setScrollPosition, 500)
        })
      })
    }
  }
  
  // 滚动事件处理函数
  const handleScroll = () => {
    saveScrollPosition()
  }
  
  // 清除保存的滚动位置
  const clearScrollPosition = () => {
    scrollPositions.delete(key)
  }
  
  // 组件挂载时恢复滚动位置
  onMounted(() => {
    nextTick(() => {
      restoreScrollPosition()
    })
  })
  
  // 组件激活时恢复滚动位置（用于 keep-alive）
  onActivated(() => {
    nextTick(() => {
      restoreScrollPosition()
    })
  })
  
  // 组件卸载前保存滚动位置
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
