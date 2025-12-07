import type { PlayerStore } from '../stores/playerStore'

/**
 * useProgressBar 返回类型
 */
export interface UseProgressBarReturn {
  handleProgressMouseDown: (e: MouseEvent) => void
  handleProgressTouchStart: (e: TouchEvent) => void
  handleProgressTouchMove: (e: TouchEvent) => void
  handleProgressTouchEnd: () => void
}

/**
 * useProgressBar 配置选项
 */
export interface UseProgressBarOptions {
  store: PlayerStore
  setVideoTime: (time: number) => void
}

/**
 * 进度条与拖拽交互封装
 * 
 * @param options - 配置选项
 */
export default function useProgressBar(options: UseProgressBarOptions): UseProgressBarReturn {
  const { store, setVideoTime } = options

  /**
   * 计算点击位置对应的播放时间
   */
  const calculateSeekTime = (clientX: number, rect: DOMRect): number => {
    const position = (clientX - rect.left) / rect.width
    return store.duration * Math.min(Math.max(position, 0), 1)
  }

  /**
   * 处理鼠标按下事件
   */
  const handleProgressMouseDown = (e: MouseEvent): void => {
    e.preventDefault()
    store.setIsDragging(true)
    
    const target = e.currentTarget as HTMLElement
    const rect = target.getBoundingClientRect()

    const seekTime = calculateSeekTime(e.clientX, rect)
    setVideoTime(seekTime)

    const handleMouseMove = (ev: MouseEvent): void => {
      if (!store.isDragging) return
      const newSeekTime = calculateSeekTime(ev.clientX, rect)
      setVideoTime(newSeekTime)
    }

    const handleMouseUp = (): void => {
      store.setIsDragging(false)
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
  }

  /**
   * 处理触摸开始事件
   */
  const handleProgressTouchStart = (e: TouchEvent): void => {
    e.preventDefault()
    store.setIsDragging(true)
    
    const target = e.currentTarget as HTMLElement
    const rect = target.getBoundingClientRect()
    const seekTime = calculateSeekTime(e.touches[0].clientX, rect)
    setVideoTime(seekTime)
  }

  /**
   * 处理触摸移动事件
   */
  const handleProgressTouchMove = (e: TouchEvent): void => {
    e.preventDefault()
    if (!store.isDragging) return
    
    const target = e.currentTarget as HTMLElement
    const rect = target.getBoundingClientRect()
    const seekTime = calculateSeekTime(e.touches[0].clientX, rect)
    setVideoTime(seekTime)
  }

  /**
   * 处理触摸结束事件
   */
  const handleProgressTouchEnd = (): void => {
    store.setIsDragging(false)
  }

  return {
    handleProgressMouseDown,
    handleProgressTouchStart,
    handleProgressTouchMove,
    handleProgressTouchEnd
  }
}
