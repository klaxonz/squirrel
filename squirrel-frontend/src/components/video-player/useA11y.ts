/**
 * 无障碍支持 Composable
 * 提供 ARIA 属性、键盘导航、屏幕阅读器支持
 */

import { ref, computed, onMounted, onUnmounted, type Ref } from 'vue'
import type { LocaleMessages } from './i18n/types'

export interface UseA11yOptions {
  videoElement: Ref<HTMLVideoElement | null>
  containerElement: Ref<HTMLElement | null>
  t: (key: keyof LocaleMessages, params?: Record<string, string | number>) => string
  onPlay?: () => void
  onPause?: () => void
  onSeek?: (time: number) => void
  onVolumeChange?: (volume: number) => void
  onMuteToggle?: () => void
  onFullscreenToggle?: () => void
  enableGlobalListeners?: boolean
  enablePreferencesObserver?: boolean
}

export interface UseA11yReturn {
  // ARIA 属性
  playerAriaLabel: Ref<string>
  progressAriaLabel: Ref<string>
  volumeAriaLabel: Ref<string>
  playButtonAriaLabel: Ref<string>
  
  // 屏幕阅读器公告
  announce: (message: string, priority?: 'polite' | 'assertive') => void
  
  // 焦点管理
  focusPlayer: () => void
  trapFocus: (enable: boolean) => void
  
  // 键盘导航状态
  isKeyboardUser: Ref<boolean>
  
  // 高对比度模式
  isHighContrast: Ref<boolean>
  
  // 减少动画模式
  prefersReducedMotion: Ref<boolean>
}

/**
 * 格式化时间为可读文本
 */
function formatTimeForScreen(seconds: number): string {
  if (!isFinite(seconds) || isNaN(seconds) || seconds < 0) return '0:00'

  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)

  if (h > 0) {
    return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  }

  return `${m}:${s.toString().padStart(2, '0')}`
}

/**
 * 无障碍支持 Composable
 */
export function useA11y(options: UseA11yOptions): UseA11yReturn {
  const { videoElement, containerElement, t, enableGlobalListeners = false, enablePreferencesObserver = false } = options
  
  // 状态
  const isKeyboardUser = ref(false)
  const isHighContrast = ref(false)
  const prefersReducedMotion = ref(false)
  
  // 屏幕阅读器公告区域
  let announceElement: HTMLElement | null = null
  let highContrastQuery: MediaQueryList | null = null
  let reducedMotionQuery: MediaQueryList | null = null
  let handleHighContrastChange: ((e: MediaQueryListEvent) => void) | null = null
  let handleReducedMotionChange: ((e: MediaQueryListEvent) => void) | null = null
  
  // ARIA 标签
  const playerAriaLabel = computed(() => t('videoPlayer'))
  
  const progressAriaLabel = computed(() => {
    const video = videoElement.value
    if (!video) return t('progressBar')
    
    const current = formatTimeForScreen(video.currentTime)
    const total = formatTimeForScreen(video.duration || 0)
    return `${t('progressBar')}, ${current} / ${total}`
  })
  
  const volumeAriaLabel = computed(() => {
    const video = videoElement.value
    if (!video) return t('volumeSlider')
    
    const percent = Math.round(video.volume * 100)
    return video.muted ? t('mute') : t('volumePercent', { percent })
  })
  
  const playButtonAriaLabel = computed(() => {
    const video = videoElement.value
    if (!video) return t('play')
    return video.paused ? t('play') : t('pause')
  })

  /**
   * 创建屏幕阅读器公告区域
   */
  const createAnnounceElement = (): void => {
    if (typeof document === 'undefined') return
    
    announceElement = document.createElement('div')
    announceElement.setAttribute('role', 'status')
    announceElement.setAttribute('aria-live', 'polite')
    announceElement.setAttribute('aria-atomic', 'true')
    announceElement.className = 'sr-only'
    announceElement.style.cssText = `
      position: absolute;
      width: 1px;
      height: 1px;
      padding: 0;
      margin: -1px;
      overflow: hidden;
      clip: rect(0, 0, 0, 0);
      white-space: nowrap;
      border: 0;
    `

    const parent = containerElement.value ?? document.body
    parent.appendChild(announceElement)
  }

  /**
   * 屏幕阅读器公告
   */
  const announce = (message: string, priority: 'polite' | 'assertive' = 'polite'): void => {
    if (!announceElement) {
      createAnnounceElement()
    }
    if (!announceElement) return
    
    announceElement.setAttribute('aria-live', priority)
    announceElement.textContent = ''
    
    // 强制重绘以确保公告被读取
    requestAnimationFrame(() => {
      if (announceElement) {
        announceElement.textContent = message
      }
    })
  }

  /**
   * 聚焦到播放器
   */
  const focusPlayer = (): void => {
    containerElement.value?.focus()
  }

  /**
   * 焦点陷阱（用于模态对话框等）
   */
  const trapFocus = (enable: boolean): void => {
    const container = containerElement.value
    if (!container) return
    
    if (enable) {
      container.setAttribute('aria-modal', 'true')
      // 查找所有可聚焦元素
      const focusableElements = container.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      )
      
      if (focusableElements.length > 0) {
        (focusableElements[0] as HTMLElement).focus()
      }
    } else {
      container.removeAttribute('aria-modal')
    }
  }

  /**
   * 检测键盘用户
   */
  const handleKeyDown = (e: KeyboardEvent): void => {
    if (e.key === 'Tab') {
      isKeyboardUser.value = true
    }
  }

  const handleMouseDown = (): void => {
    isKeyboardUser.value = false
  }

  /**
   * 检测系统偏好
   */
  const detectPreferences = (): void => {
    if (typeof window === 'undefined') return
    
    // 高对比度
    highContrastQuery = window.matchMedia('(forced-colors: active)')
    isHighContrast.value = highContrastQuery.matches
    handleHighContrastChange = (e: MediaQueryListEvent) => {
      isHighContrast.value = e.matches
    }
    highContrastQuery.addEventListener('change', handleHighContrastChange)
    
    // 减少动画
    reducedMotionQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
    prefersReducedMotion.value = reducedMotionQuery.matches
    handleReducedMotionChange = (e: MediaQueryListEvent) => {
      prefersReducedMotion.value = e.matches
    }
    reducedMotionQuery.addEventListener('change', handleReducedMotionChange)
  }

  onMounted(() => {
    if (enablePreferencesObserver) {
      detectPreferences()
    }

    if (!enableGlobalListeners) return
    if (typeof document === 'undefined') return
    document.addEventListener('keydown', handleKeyDown)
    document.addEventListener('mousedown', handleMouseDown)
  })

  onUnmounted(() => {
    if (announceElement) {
      announceElement.remove()
      announceElement = null
    }
    
    if (enableGlobalListeners && typeof document !== 'undefined') {
      document.removeEventListener('keydown', handleKeyDown)
      document.removeEventListener('mousedown', handleMouseDown)
    }

    if (enablePreferencesObserver) {
      if (highContrastQuery && handleHighContrastChange) {
        highContrastQuery.removeEventListener('change', handleHighContrastChange)
      }
      if (reducedMotionQuery && handleReducedMotionChange) {
        reducedMotionQuery.removeEventListener('change', handleReducedMotionChange)
      }
    }

    highContrastQuery = null
    reducedMotionQuery = null
    handleHighContrastChange = null
    handleReducedMotionChange = null
  })

  return {
    playerAriaLabel,
    progressAriaLabel,
    volumeAriaLabel,
    playButtonAriaLabel,
    announce,
    focusPlayer,
    trapFocus,
    isKeyboardUser,
    isHighContrast,
    prefersReducedMotion
  }
}

export default useA11y
