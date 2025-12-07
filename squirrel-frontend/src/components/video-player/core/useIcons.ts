/**
 * 图标系统
 * 使用 @iconify/vue 和 Material Symbols 图标集
 * 
 * 注意：实际图标渲染由 PlayerIcon.vue 组件处理
 * 此文件仅保留类型定义，用于向后兼容
 */

// 图标名称类型定义
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
  | 'widescreen'
  | 'widescreenExit'
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

/**
 * 空的 useIcons 函数，保持向后兼容
 * 现在使用 @iconify/vue 的 Icon 组件代替
 */
export function useIcons() {
  return {
    getIcon: () => null,
    renderIcon: () => null,
    registerIcon: () => {},
    registerIcons: () => {},
    setIconSet: () => {},
    resetIcons: () => {},
    iconSet: { value: {} }
  }
}

export default useIcons
