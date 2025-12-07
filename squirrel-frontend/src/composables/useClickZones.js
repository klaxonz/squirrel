import { ref } from 'vue'

/**
 * 处理视频播放器的点击区域逻辑
 * - 左侧区域：双击快退
 * - 右侧区域：双击快进
 * - 中间区域：单击播放/暂停
 */
export default function useClickZones(emit) {
  const showLeftSkip = ref(false)
  const showRightSkip = ref(false)

  let leftClickTimer = null
  let rightClickTimer = null

  const DOUBLE_CLICK_DELAY = 300
  const SKIP_INDICATOR_DURATION = 500

  const handleLeftClick = () => {
    if (leftClickTimer) {
      clearTimeout(leftClickTimer)
      leftClickTimer = null
      return
    }

    leftClickTimer = setTimeout(() => {
      leftClickTimer = null
    }, DOUBLE_CLICK_DELAY)
  }

  const handleRightClick = () => {
    if (rightClickTimer) {
      clearTimeout(rightClickTimer)
      rightClickTimer = null
      return
    }

    rightClickTimer = setTimeout(() => {
      rightClickTimer = null
    }, DOUBLE_CLICK_DELAY)
  }

  const handleLeftDoubleClick = () => {
    if (leftClickTimer) {
      clearTimeout(leftClickTimer)
      leftClickTimer = null
    }

    showLeftSkip.value = true
    emit('skip-backward')

    setTimeout(() => {
      showLeftSkip.value = false
    }, SKIP_INDICATOR_DURATION)
  }

  const handleRightDoubleClick = () => {
    if (rightClickTimer) {
      clearTimeout(rightClickTimer)
      rightClickTimer = null
    }

    showRightSkip.value = true
    emit('skip-forward')

    setTimeout(() => {
      showRightSkip.value = false
    }, SKIP_INDICATOR_DURATION)
  }

  const cleanup = () => {
    if (leftClickTimer) {
      clearTimeout(leftClickTimer)
      leftClickTimer = null
    }
    if (rightClickTimer) {
      clearTimeout(rightClickTimer)
      rightClickTimer = null
    }
  }

  return {
    showLeftSkip,
    showRightSkip,
    handleLeftClick,
    handleRightClick,
    handleLeftDoubleClick,
    handleRightDoubleClick,
    cleanup
  }
}
