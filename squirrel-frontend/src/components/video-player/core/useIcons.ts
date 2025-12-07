/**
 * 图标系统
 * 支持自定义图标、图标集切换
 */

import { ref, computed, type Ref, type Component, h, type VNode } from 'vue'

// 图标名称
export type IconName =
  | 'play'
  | 'pause'
  | 'stop'
  | 'replay'
  | 'skipForward'
  | 'skipBackward'
  | 'previous'
  | 'next'
  | 'volumeHigh'
  | 'volumeLow'
  | 'volumeMute'
  | 'volumeOff'
  | 'fullscreen'
  | 'fullscreenExit'
  | 'pip'
  | 'pipExit'
  | 'settings'
  | 'subtitles'
  | 'subtitlesOff'
  | 'quality'
  | 'speed'
  | 'check'
  | 'chevronLeft'
  | 'chevronRight'
  | 'close'
  | 'error'
  | 'loading'

// 图标定义
export interface IconDefinition {
  // SVG 路径 (d 属性)
  path?: string
  // 多路径
  paths?: string[]
  // 视图框
  viewBox?: string
  // 完整 SVG 字符串
  svg?: string
  // Vue 组件
  component?: Component
  // 渲染函数
  render?: () => VNode
}

// 图标集
export type IconSet = Partial<Record<IconName, IconDefinition>>

// 内置 Material Design 图标
const MATERIAL_ICONS: IconSet = {
  play: {
    viewBox: '0 0 24 24',
    path: 'M8 5v14l11-7z'
  },
  pause: {
    viewBox: '0 0 24 24',
    path: 'M6 19h4V5H6v14zm8-14v14h4V5h-4z'
  },
  stop: {
    viewBox: '0 0 24 24',
    path: 'M6 6h12v12H6z'
  },
  replay: {
    viewBox: '0 0 24 24',
    path: 'M12 5V1L7 6l5 5V7c3.31 0 6 2.69 6 6s-2.69 6-6 6-6-2.69-6-6H4c0 4.42 3.58 8 8 8s8-3.58 8-8-3.58-8-8-8z'
  },
  skipForward: {
    viewBox: '0 0 24 24',
    path: 'M4 18l8.5-6L4 6v12zm9-12v12l8.5-6L13 6z'
  },
  skipBackward: {
    viewBox: '0 0 24 24',
    path: 'M11 18V6l-8.5 6 8.5 6zm.5-6l8.5 6V6l-8.5 6z'
  },
  previous: {
    viewBox: '0 0 24 24',
    path: 'M6 6h2v12H6zm3.5 6l8.5 6V6z'
  },
  next: {
    viewBox: '0 0 24 24',
    path: 'M6 18l8.5-6L6 6v12zM16 6v12h2V6h-2z'
  },
  volumeHigh: {
    viewBox: '0 0 24 24',
    path: 'M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z'
  },
  volumeLow: {
    viewBox: '0 0 24 24',
    path: 'M18.5 12c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM5 9v6h4l5 5V4L9 9H5z'
  },
  volumeMute: {
    viewBox: '0 0 24 24',
    path: 'M7 9v6h4l5 5V4l-5 5H7z'
  },
  volumeOff: {
    viewBox: '0 0 24 24',
    path: 'M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z'
  },
  fullscreen: {
    viewBox: '0 0 24 24',
    path: 'M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z'
  },
  fullscreenExit: {
    viewBox: '0 0 24 24',
    path: 'M5 16h3v3h2v-5H5v2zm3-8H5v2h5V5H8v3zm6 11h2v-3h3v-2h-5v5zm2-11V5h-2v5h5V8h-3z'
  },
  pip: {
    viewBox: '0 0 24 24',
    path: 'M19 7h-8v6h8V7zm2-4H3c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h18c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H3V5h18v14z'
  },
  pipExit: {
    viewBox: '0 0 24 24',
    path: 'M21 3H3c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h18c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H3V5h18v14zM9 7v10l7-5-7-5z'
  },
  settings: {
    viewBox: '0 0 24 24',
    path: 'M19.14 12.94c.04-.31.06-.63.06-.94 0-.31-.02-.63-.06-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.04.31-.06.63-.06.94s.02.63.06.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z'
  },
  subtitles: {
    viewBox: '0 0 24 24',
    path: 'M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zM4 12h4v2H4v-2zm10 6H4v-2h10v2zm6 0h-4v-2h4v2zm0-4H10v-2h10v2z'
  },
  subtitlesOff: {
    viewBox: '0 0 24 24',
    path: 'M20 4H6.83l2 2H20v11.17l1.76 1.76c.15-.28.24-.59.24-.93V6c0-1.1-.9-2-2-2zM1.04 3.87l1.2 1.2C2.09 5.35 2 5.66 2 6v12c0 1.1.9 2 2 2h13.17l2.96 2.96 1.41-1.41L2.45 2.45 1.04 3.87zM4 12h4v2H4v-2zm0 4h9.17l.83.83V16H4v2zm10 0h.17l1.83 1.83V16H14v2z'
  },
  quality: {
    viewBox: '0 0 24 24',
    path: 'M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-8 12H9.5v-2h-2v2H6V9h1.5v2.5h2V9H11v6zm2-6h4c.55 0 1 .45 1 1v4c0 .55-.45 1-1 1h-4V9zm1.5 4.5h2v-3h-2v3z'
  },
  speed: {
    viewBox: '0 0 24 24',
    path: 'M20.38 8.57l-1.23 1.85a8 8 0 0 1-.22 7.58H5.07A8 8 0 0 1 15.58 6.85l1.85-1.23A10 10 0 0 0 3.35 19a2 2 0 0 0 1.72 1h13.85a2 2 0 0 0 1.74-1 10 10 0 0 0-.27-10.44zm-9.79 6.84a2 2 0 0 0 2.83 0l5.66-8.49-8.49 5.66a2 2 0 0 0 0 2.83z'
  },
  check: {
    viewBox: '0 0 24 24',
    path: 'M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z'
  },
  chevronLeft: {
    viewBox: '0 0 24 24',
    path: 'M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z'
  },
  chevronRight: {
    viewBox: '0 0 24 24',
    path: 'M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z'
  },
  close: {
    viewBox: '0 0 24 24',
    path: 'M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z'
  },
  error: {
    viewBox: '0 0 24 24',
    path: 'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z'
  },
  loading: {
    viewBox: '0 0 24 24',
    path: 'M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46C19.54 15.03 20 13.57 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74C4.46 8.97 4 10.43 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z'
  }
}

export interface UseIconsOptions {
  /** 初始图标集 */
  iconSet?: IconSet
  /** 默认图标大小 */
  defaultSize?: number
  /** 默认图标颜色 */
  defaultColor?: string
}

export interface UseIconsReturn {
  /** 获取图标 */
  getIcon: (name: IconName) => IconDefinition | null
  
  /** 渲染图标为 VNode */
  renderIcon: (name: IconName, props?: IconRenderProps) => VNode | null
  
  /** 注册自定义图标 */
  registerIcon: (name: IconName, definition: IconDefinition) => void
  
  /** 批量注册图标 */
  registerIcons: (icons: IconSet) => void
  
  /** 设置图标集 */
  setIconSet: (iconSet: IconSet) => void
  
  /** 重置为默认图标 */
  resetIcons: () => void
  
  /** 当前图标集 */
  iconSet: Ref<IconSet>
}

export interface IconRenderProps {
  size?: number | string
  color?: string
  class?: string
  style?: Record<string, string>
}

/**
 * 图标系统 Composable
 */
export function useIcons(options: UseIconsOptions = {}): UseIconsReturn {
  const { 
    iconSet: initialIconSet,
    defaultSize = 24,
    defaultColor = 'currentColor'
  } = options

  // 图标集
  const iconSet = ref<IconSet>({
    ...MATERIAL_ICONS,
    ...initialIconSet
  })

  /**
   * 获取图标定义
   */
  const getIcon = (name: IconName): IconDefinition | null => {
    return iconSet.value[name] || null
  }

  /**
   * 渲染图标
   */
  const renderIcon = (name: IconName, props: IconRenderProps = {}): VNode | null => {
    const icon = getIcon(name)
    if (!icon) return null

    const {
      size = defaultSize,
      color = defaultColor,
      class: className = '',
      style = {}
    } = props

    const sizeStr = typeof size === 'number' ? `${size}px` : size

    // 如果有自定义组件
    if (icon.component) {
      return h(icon.component, {
        class: `sp-icon sp-icon-${name} ${className}`,
        style: { width: sizeStr, height: sizeStr, color, ...style }
      })
    }

    // 如果有渲染函数
    if (icon.render) {
      return icon.render()
    }

    // 如果有完整 SVG
    if (icon.svg) {
      return h('span', {
        class: `sp-icon sp-icon-${name} ${className}`,
        style: { width: sizeStr, height: sizeStr, color, ...style },
        innerHTML: icon.svg
      })
    }

    // 默认 SVG 渲染
    const viewBox = icon.viewBox || '0 0 24 24'
    const paths = icon.paths || (icon.path ? [icon.path] : [])

    return h('svg', {
      class: `sp-icon sp-icon-${name} ${className}`,
      style: { width: sizeStr, height: sizeStr, ...style },
      viewBox,
      fill: color,
      xmlns: 'http://www.w3.org/2000/svg'
    }, paths.map((d, i) => h('path', { key: i, d })))
  }

  /**
   * 注册单个图标
   */
  const registerIcon = (name: IconName, definition: IconDefinition): void => {
    iconSet.value = {
      ...iconSet.value,
      [name]: definition
    }
  }

  /**
   * 批量注册图标
   */
  const registerIcons = (icons: IconSet): void => {
    iconSet.value = {
      ...iconSet.value,
      ...icons
    }
  }

  /**
   * 设置完整图标集
   */
  const setIconSet = (newIconSet: IconSet): void => {
    iconSet.value = { ...newIconSet }
  }

  /**
   * 重置为默认图标
   */
  const resetIcons = (): void => {
    iconSet.value = { ...MATERIAL_ICONS }
  }

  return {
    getIcon,
    renderIcon,
    registerIcon,
    registerIcons,
    setIconSet,
    resetIcons,
    iconSet
  }
}

export default useIcons
