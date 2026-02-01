/**
 * 控制栏布局插槽系统
 * 允许自定义控制栏组件的排列和显示
 */

import { ref, computed, type Ref, type Component, type VNode } from 'vue'

// 预定义的控件 ID
export type BuiltInControl =
  | 'play'
  | 'prev'
  | 'next'
  | 'progress'
  | 'time'
  | 'volume'
  | 'quality'
  | 'playbackRate'
  | 'subtitles'
  | 'settings'
  | 'pip'
  | 'fullscreen'
  | 'spacer'

// 控件定义
export interface ControlDefinition {
  id: string
  component?: Component
  render?: () => VNode
  props?: Record<string, any>
  visible?: boolean | (() => boolean)
  order?: number
  group?: 'left' | 'center' | 'right'
}

// 布局配置
export interface ControlsLayoutConfig {
  // 顶部区域控件
  top?: (BuiltInControl | ControlDefinition)[]
  // 进度条区域
  progress?: boolean
  // 底部左侧
  left?: (BuiltInControl | ControlDefinition)[]
  // 底部中间
  center?: (BuiltInControl | ControlDefinition)[]
  // 底部右侧
  right?: (BuiltInControl | ControlDefinition)[]
}

// 预设布局
export type PresetLayout = 'default' | 'minimal' | 'simple' | 'compact' | 'custom'

export interface UseControlsLayoutOptions {
  layout?: ControlsLayoutConfig | PresetLayout
}

export interface UseControlsLayoutReturn {
  // 当前布局
  layout: Ref<ControlsLayoutConfig>
  
  // 控件管理
  registerControl: (control: ControlDefinition) => void
  unregisterControl: (id: string) => void
  updateControl: (id: string, updates: Partial<ControlDefinition>) => void
  
  // 布局切换
  setLayout: (layout: ControlsLayoutConfig | PresetLayout) => void
  setPreset: (preset: PresetLayout) => void
  
  // 控件可见性
  showControl: (id: string) => void
  hideControl: (id: string) => void
  toggleControl: (id: string) => void
  isControlVisible: (id: string) => boolean
  
  // 获取区域控件
  getTopControls: Ref<ControlDefinition[]>
  getLeftControls: Ref<ControlDefinition[]>
  getCenterControls: Ref<ControlDefinition[]>
  getRightControls: Ref<ControlDefinition[]>
}

// 预设布局定义
const PRESET_LAYOUTS: Record<PresetLayout, ControlsLayoutConfig> = {
  default: {
    progress: true,
    left: ['play', 'prev', 'next', 'volume', 'time'],
    center: [],
    right: ['subtitles', 'quality', 'settings', 'pip', 'fullscreen']
  },
  
  minimal: {
    progress: true,
    left: ['play', 'volume'],
    center: ['time'],
    right: ['fullscreen']
  },
  
  simple: {
    progress: true,
    left: ['play', 'prev', 'next', 'volume', 'time'],
    center: [],
    right: ['subtitles', 'settings', 'pip', 'fullscreen']
  },
  
  compact: {
    progress: true,
    left: ['play', 'prev', 'next', 'time'],
    center: [],
    right: ['volume', 'quality', 'subtitles', 'settings', 'pip', 'fullscreen']
  },
  
  custom: {
    progress: true,
    left: [],
    center: [],
    right: []
  }
}

/**
 * 控制栏布局 Composable
 */
export function useControlsLayout(options: UseControlsLayoutOptions = {}): UseControlsLayoutReturn {
  const { layout: initialLayout = 'default' } = options

  // 自定义控件注册表
  const customControls = ref<Map<string, ControlDefinition>>(new Map())
  
  // 隐藏的控件 ID
  const hiddenControls = ref<Set<string>>(new Set())

  // 当前布局配置
  const layout = ref<ControlsLayoutConfig>(
    typeof initialLayout === 'string' 
      ? { ...PRESET_LAYOUTS[initialLayout] }
      : { ...initialLayout }
  )

  /**
   * 解析控件定义
   */
  const resolveControl = (item: BuiltInControl | ControlDefinition): ControlDefinition => {
    if (typeof item === 'string') {
      // 检查是否有自定义覆盖
      const custom = customControls.value.get(item)
      if (custom) return custom
      
      // 返回内置控件定义
      return {
        id: item,
        visible: true
      }
    }
    return item
  }

  /**
   * 获取区域控件列表
   */
  const getControlsForArea = (area: (BuiltInControl | ControlDefinition)[] | undefined): ControlDefinition[] => {
    if (!area) return []
    
    return area
      .map(resolveControl)
      .filter(control => {
        // 检查是否被隐藏
        if (hiddenControls.value.has(control.id)) return false
        
        // 检查 visible 属性
        if (typeof control.visible === 'function') {
          return control.visible()
        }
        return control.visible !== false
      })
      .sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
  }

  // 计算各区域控件
  const getTopControls = computed(() => getControlsForArea(layout.value.top))
  const getLeftControls = computed(() => getControlsForArea(layout.value.left))
  const getCenterControls = computed(() => getControlsForArea(layout.value.center))
  const getRightControls = computed(() => getControlsForArea(layout.value.right))

  /**
   * 注册自定义控件
   */
  const registerControl = (control: ControlDefinition): void => {
    customControls.value.set(control.id, control)
  }

  /**
   * 注销控件
   */
  const unregisterControl = (id: string): void => {
    customControls.value.delete(id)
  }

  /**
   * 更新控件
   */
  const updateControl = (id: string, updates: Partial<ControlDefinition>): void => {
    const existing = customControls.value.get(id)
    if (existing) {
      customControls.value.set(id, { ...existing, ...updates })
    } else {
      customControls.value.set(id, { id, ...updates })
    }
  }

  /**
   * 设置布局
   */
  const setLayout = (newLayout: ControlsLayoutConfig | PresetLayout): void => {
    if (typeof newLayout === 'string') {
      layout.value = { ...PRESET_LAYOUTS[newLayout] }
    } else {
      layout.value = { ...newLayout }
    }
  }

  /**
   * 设置预设
   */
  const setPreset = (preset: PresetLayout): void => {
    layout.value = { ...PRESET_LAYOUTS[preset] }
  }

  /**
   * 显示控件
   */
  const showControl = (id: string): void => {
    hiddenControls.value.delete(id)
  }

  /**
   * 隐藏控件
   */
  const hideControl = (id: string): void => {
    hiddenControls.value.add(id)
  }

  /**
   * 切换控件可见性
   */
  const toggleControl = (id: string): void => {
    if (hiddenControls.value.has(id)) {
      hiddenControls.value.delete(id)
    } else {
      hiddenControls.value.add(id)
    }
  }

  /**
   * 检查控件是否可见
   */
  const isControlVisible = (id: string): boolean => {
    return !hiddenControls.value.has(id)
  }

  return {
    layout,
    registerControl,
    unregisterControl,
    updateControl,
    setLayout,
    setPreset,
    showControl,
    hideControl,
    toggleControl,
    isControlVisible,
    getTopControls,
    getLeftControls,
    getCenterControls,
    getRightControls
  }
}

export default useControlsLayout
