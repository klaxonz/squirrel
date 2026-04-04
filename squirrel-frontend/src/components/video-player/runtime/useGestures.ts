/**
 * 移动端手势支持
 * 滑动调节进度/音量、双击快进快退、捏合缩放
 */

import { ref, onUnmounted, watch, type Ref } from 'vue'
import { isPlayerInteractiveTarget } from './mobileControls'

export interface GestureCallbacks {
  onSeek?: (deltaSeconds: number) => void
  onVolumeChange?: (deltaPercent: number) => void
  onBrightnessChange?: (deltaPercent: number) => void
  onTap?: (zone: 'left' | 'center' | 'right') => void
  onDoubleTapLeft?: () => void
  onDoubleTapRight?: () => void
  onDoubleTapCenter?: () => void
  onPinchZoom?: (scale: number) => void
  onSwipeUp?: () => void
  onSwipeDown?: () => void
}

export interface UseGesturesOptions {
  element: Ref<HTMLElement | null>
  callbacks: GestureCallbacks
  /** 是否启用 */
  enabled?: boolean
  /** 滑动灵敏度 */
  sensitivity?: number
  /** 双击间隔(ms) */
  doubleTapDelay?: number
  /** 单击最大时长(ms) */
  tapMaxDuration?: number
  /** 双击最大位移(px) */
  doubleTapMaxDistance?: number
  /** 滑动阈值(px) */
  swipeThreshold?: number
}

export interface UseGesturesReturn {
  isGesturing: Ref<boolean>
  gestureType: Ref<GestureType | null>
  gestureProgress: Ref<number>
  enable: () => void
  disable: () => void
}

export type GestureType = 'seek' | 'volume' | 'brightness' | 'zoom' | 'none'

interface TouchState {
  startX: number
  startY: number
  startTime: number
  lastTapTime: number
  lastTapX: number
  lastTapY: number
  lastTapZone: 'left' | 'center' | 'right' | null
  isMultiTouch: boolean
  initialDistance: number
  ignoreGesture: boolean
}

/**
 * 手势支持 Composable
 */
export function useGestures(options: UseGesturesOptions): UseGesturesReturn {
  const { 
    element, 
    callbacks,
    sensitivity = 1,
    doubleTapDelay = 240,
    tapMaxDuration = 180,
    doubleTapMaxDistance = 48,
    swipeThreshold = 50
  } = options

  const isEnabled = ref(options.enabled !== false)
  const isGesturing = ref(false)
  const gestureType = ref<GestureType | null>(null)
  const gestureProgress = ref(0)

  const touchState: TouchState = {
    startX: 0,
    startY: 0,
    startTime: 0,
    lastTapTime: 0,
    lastTapX: 0,
    lastTapY: 0,
    lastTapZone: null,
    isMultiTouch: false,
    initialDistance: 0,
    ignoreGesture: false
  }

  let singleTapTimer: ReturnType<typeof setTimeout> | null = null
  let boundElement: HTMLElement | null = null

  const clearSingleTapTimer = (): void => {
    if (singleTapTimer) {
      clearTimeout(singleTapTimer)
      singleTapTimer = null
    }
  }

  const resetTapState = (): void => {
    touchState.lastTapTime = 0
    touchState.lastTapX = 0
    touchState.lastTapY = 0
    touchState.lastTapZone = null
  }

  /**
   * 计算两点之间的距离
   */
  const getDistance = (touches: TouchList): number => {
    if (touches.length < 2) return 0
    const dx = touches[0].clientX - touches[1].clientX
    const dy = touches[0].clientY - touches[1].clientY
    return Math.sqrt(dx * dx + dy * dy)
  }

  /**
   * 获取触摸区域 (left/center/right)
   */
  const getTouchZone = (x: number, width: number): 'left' | 'center' | 'right' => {
    const third = width / 3
    if (x < third) return 'left'
    if (x > third * 2) return 'right'
    return 'center'
  }

  /**
   * 处理触摸开始
   */
  const handleTouchStart = (e: TouchEvent): void => {
    if (!isEnabled.value) return

    const touch = e.touches[0]
    const now = Date.now()

    touchState.startX = touch.clientX
    touchState.startY = touch.clientY
    touchState.startTime = now
    touchState.isMultiTouch = e.touches.length > 1
    touchState.ignoreGesture = isPlayerInteractiveTarget(e.target as HTMLElement | null)

    // 捏合手势初始化
    if (e.touches.length === 2) {
      touchState.initialDistance = getDistance(e.touches)
    }
  }

  /**
   * 处理触摸移动
   */
  const handleTouchMove = (e: TouchEvent): void => {
    if (!isEnabled.value) return
    if (touchState.ignoreGesture) return

    // 捏合缩放
    if (e.touches.length === 2) {
      const currentDistance = getDistance(e.touches)
      const scale = currentDistance / touchState.initialDistance
      
      if (Math.abs(scale - 1) > 0.1) {
        isGesturing.value = true
        gestureType.value = 'zoom'
        callbacks.onPinchZoom?.(scale)
      }
      return
    }

    if (e.touches.length !== 1) return

    const touch = e.touches[0]
    const deltaX = touch.clientX - touchState.startX
    const deltaY = touch.clientY - touchState.startY
    const absDeltaX = Math.abs(deltaX)
    const absDeltaY = Math.abs(deltaY)

    // 确定手势类型
    if (!isGesturing.value && (absDeltaX > 10 || absDeltaY > 10)) {
      isGesturing.value = true
      
      // 水平滑动 -> 调节进度
      if (absDeltaX > absDeltaY * 1.5) {
        gestureType.value = 'seek'
      }
      // 垂直滑动 -> 根据位置调节音量/亮度
      else if (absDeltaY > absDeltaX * 1.5) {
        const rect = element.value?.getBoundingClientRect()
        if (rect) {
          const zone = getTouchZone(touchState.startX - rect.left, rect.width)
          gestureType.value = zone === 'left' ? 'brightness' : 'volume'
        }
      }
    }

    // 执行手势
    if (isGesturing.value) {
      e.preventDefault()

      switch (gestureType.value) {
        case 'seek': {
          // 每 10px 对应 1 秒
          const seconds = (deltaX / 10) * sensitivity
          gestureProgress.value = seconds
          callbacks.onSeek?.(seconds)
          break
        }
        
        case 'volume': {
          // 每 100px 对应 100% 音量
          const percent = (-deltaY / 100) * sensitivity * 100
          gestureProgress.value = percent
          callbacks.onVolumeChange?.(percent)
          break
        }
        
        case 'brightness': {
          const percent = (-deltaY / 100) * sensitivity * 100
          gestureProgress.value = percent
          callbacks.onBrightnessChange?.(percent)
          break
        }
      }
    }
  }

  /**
   * 处理触摸结束
   */
  const handleTouchEnd = (e: TouchEvent): void => {
    if (!isEnabled.value) return

    const now = Date.now()
    const touchDuration = now - touchState.startTime
    const shouldIgnoreGesture = touchState.ignoreGesture

    // 检测双击
    if (!shouldIgnoreGesture && !isGesturing.value && touchDuration < tapMaxDuration) {
      const touch = e.changedTouches[0]
      const tapX = touch.clientX
      const tapY = touch.clientY
      const rect = element.value?.getBoundingClientRect()
      const zone = rect ? getTouchZone(tapX - rect.left, rect.width) : 'center'
      const tapDistance = Math.hypot(tapX - touchState.lastTapX, tapY - touchState.lastTapY)
      const isSameZone = touchState.lastTapZone === zone
      
      // 检查是否为双击
      if (now - touchState.lastTapTime < doubleTapDelay && isSameZone && tapDistance <= doubleTapMaxDistance) {
        clearSingleTapTimer()

        switch (zone) {
          case 'left':
            callbacks.onDoubleTapLeft?.()
            break
          case 'right':
            callbacks.onDoubleTapRight?.()
            break
          case 'center':
            callbacks.onDoubleTapCenter?.()
            break
        }

        resetTapState()
      } else {
        touchState.lastTapTime = now
        touchState.lastTapX = tapX
        touchState.lastTapY = tapY
        touchState.lastTapZone = zone
        clearSingleTapTimer()
        singleTapTimer = setTimeout(() => {
          callbacks.onTap?.(zone)
          resetTapState()
          singleTapTimer = null
        }, doubleTapDelay)
      }
    }

    // 检测上下滑动（快速滑动）
    if (isGesturing.value && touchDuration < 300) {
      const deltaY = e.changedTouches[0].clientY - touchState.startY
      
      if (Math.abs(deltaY) > swipeThreshold) {
        if (deltaY < 0) {
          callbacks.onSwipeUp?.()
        } else {
          callbacks.onSwipeDown?.()
        }
      }
    }

    // 重置状态
    isGesturing.value = false
    gestureType.value = null
    gestureProgress.value = 0
    touchState.isMultiTouch = false
    touchState.ignoreGesture = false
  }

  /**
   * 启用手势
   */
  const enable = (): void => {
    isEnabled.value = true
  }

  /**
   * 禁用手势
   */
  const disable = (): void => {
    isEnabled.value = false
    clearSingleTapTimer()
    isGesturing.value = false
    gestureType.value = null
    gestureProgress.value = 0
  }

  const attachListeners = (el: HTMLElement): void => {
    el.addEventListener('touchstart', handleTouchStart, { passive: true })
    el.addEventListener('touchmove', handleTouchMove, { passive: false })
    el.addEventListener('touchend', handleTouchEnd, { passive: true })
    el.addEventListener('touchcancel', handleTouchEnd, { passive: true })
  }

  const detachListeners = (el: HTMLElement): void => {
    el.removeEventListener('touchstart', handleTouchStart)
    el.removeEventListener('touchmove', handleTouchMove)
    el.removeEventListener('touchend', handleTouchEnd)
    el.removeEventListener('touchcancel', handleTouchEnd)
  }

  watch(element, (el, prevEl) => {
    if (prevEl && prevEl !== el) {
      detachListeners(prevEl)
      if (boundElement === prevEl) boundElement = null
    }

    if (!el || boundElement === el) return

    attachListeners(el)
    boundElement = el
  }, { immediate: true })

  onUnmounted(() => {
    clearSingleTapTimer()
    if (!boundElement) return

    detachListeners(boundElement)
    boundElement = null
  })

  return {
    isGesturing,
    gestureType,
    gestureProgress,
    enable,
    disable
  }
}

export default useGestures
