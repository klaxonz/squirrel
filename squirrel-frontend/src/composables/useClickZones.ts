import { ref, type Ref } from 'vue'

/**
 * 点击区域事件发射器类型
 */
export interface ClickZoneEmit {
  (event: 'skip-forward'): void
  (event: 'skip-backward'): void
}

/**
 * useClickZones 返回类型
 */
export interface UseClickZonesReturn {
  showLeftSkip: Ref<boolean>
  showRightSkip: Ref<boolean>
  handleLeftClick: () => void
  handleRightClick: () => void
  handleLeftDoubleClick: () => void
  handleRightDoubleClick: () => void
  cleanup: () => void
}

// 常量配置
const DOUBLE_CLICK_DELAY = 300
const SKIP_INDICATOR_DURATION = 500

/**
 * 处理视频播放器的点击区域逻辑
 * - 左侧区域：双击快退
 * - 右侧区域：双击快进
 * - 中间区域：单击播放/暂停
 * 
 * @param emit - 事件发射器
 */
export default function useClickZones(emit: ClickZoneEmit): UseClickZonesReturn {
  const showLeftSkip: Ref<boolean> = ref(false)
  const showRightSkip: Ref<boolean> = ref(false)

  let leftClickTimer: ReturnType<typeof setTimeout> | null = null
  let rightClickTimer: ReturnType<typeof setTimeout> | null = null

  /**
   * 处理左侧区域单击
   */
  const handleLeftClick = (): void => {
    if (leftClickTimer) {
      clearTimeout(leftClickTimer)
      leftClickTimer = null
      return
    }

    leftClickTimer = setTimeout(() => {
      leftClickTimer = null
    }, DOUBLE_CLICK_DELAY)
  }

  /**
   * 处理右侧区域单击
   */
  const handleRightClick = (): void => {
    if (rightClickTimer) {
      clearTimeout(rightClickTimer)
      rightClickTimer = null
      return
    }

    rightClickTimer = setTimeout(() => {
      rightClickTimer = null
    }, DOUBLE_CLICK_DELAY)
  }

  /**
   * 处理左侧区域双击（快退）
   */
  const handleLeftDoubleClick = (): void => {
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

  /**
   * 处理右侧区域双击（快进）
   */
  const handleRightDoubleClick = (): void => {
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

  /**
   * 清理定时器
   */
  const cleanup = (): void => {
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
