/**
 * 字幕插件
 * 支持 VTT/SRT 格式、样式自定义、多轨道切换
 */

import type { PlayerPlugin, PluginContext } from '../../core/types'

export interface SubtitleTrack {
  id: string
  label: string
  language: string
  url?: string
  content?: string
  default?: boolean
}

export interface SubtitleCue {
  id: string
  startTime: number
  endTime: number
  text: string
}

export interface SubtitleStyle {
  fontSize?: 'small' | 'medium' | 'large' | 'xlarge'
  fontFamily?: string
  color?: string
  backgroundColor?: string
  backgroundOpacity?: number
  position?: 'top' | 'bottom'
  textShadow?: boolean
}

export interface SubtitlesPluginOptions {
  /** 默认样式 */
  defaultStyle?: SubtitleStyle
  /** 是否自动加载第一个字幕 */
  autoLoad?: boolean
  /** 字幕解析器 */
  parsers?: Record<string, SubtitleParser>
}

export type SubtitleParser = (content: string) => SubtitleCue[]

export class SubtitlesPlugin implements PlayerPlugin {
  readonly name = 'subtitles'
  readonly version = '1.0.0'

  private context: PluginContext | null = null
  private options: SubtitlesPluginOptions
  private tracks: SubtitleTrack[] = []
  private currentTrack: SubtitleTrack | null = null
  private cues: SubtitleCue[] = []
  private activeCueIndex: number = -1
  private enabled: boolean = false
  private style: SubtitleStyle
  private styleElement: HTMLStyleElement | null = null
  private containerElement: HTMLElement | null = null

  constructor() {
    this.options = {}
    this.style = {
      fontSize: 'medium',
      position: 'bottom',
      textShadow: true
    }
  }

  install(context: PluginContext, options?: SubtitlesPluginOptions): void {
    this.context = context
    this.options = { autoLoad: true, ...options }
    
    if (options?.defaultStyle) {
      this.style = { ...this.style, ...options.defaultStyle }
    }

    this.createStyleElement()
    this.createContainer()
    this.updateStyles()
  }

  onTimeUpdate(currentTime: number): void {
    if (!this.enabled || this.cues.length === 0) return
    this.updateActiveCue(currentTime)
  }

  onSeek(): void {
    // 重置活动字幕索引，让 timeupdate 重新计算
    this.activeCueIndex = -1
  }

  /**
   * 创建样式元素
   */
  private createStyleElement(): void {
    if (typeof document === 'undefined') return
    
    this.styleElement = document.createElement('style')
    this.styleElement.id = 'sp-subtitles-style'
    document.head.appendChild(this.styleElement)
  }

  /**
   * 创建字幕容器
   */
  private createContainer(): void {
    if (!this.context?.videoElement) return

    const video = this.context.videoElement
    const parent = video.parentElement
    if (!parent) return

    this.containerElement = document.createElement('div')
    this.containerElement.className = 'sp-subtitles'
    this.containerElement.setAttribute('aria-live', 'polite')
    this.containerElement.setAttribute('aria-atomic', 'true')
    parent.appendChild(this.containerElement)
  }

  /**
   * 更新样式
   */
  private updateStyles(): void {
    if (!this.styleElement) return

    const fontSizeMap: Record<string, string> = {
      small: '14px',
      medium: '20px',
      large: '28px',
      xlarge: '36px'
    }

    const fontSize = fontSizeMap[this.style.fontSize || 'medium']
    const color = this.style.color || 'var(--sp-subtitle-color)'
    const bgOpacity = this.style.backgroundOpacity
    const bgColor = this.style.backgroundColor
    let background = 'var(--sp-subtitle-bg)'
    if (bgColor) {
      background = this.hexToRgba(bgColor, bgOpacity ?? 1)
    } else if (typeof bgOpacity === 'number') {
      background = `rgba(var(--sp-subtitle-bg-rgb), ${bgOpacity})`
    }
    const position = this.style.position === 'top' ? 'top: 10%;' : 'bottom: 60px;'
    const shadow = this.style.textShadow ? 'var(--sp-subtitle-text-shadow)' : 'none'
    const fontFamily = this.style.fontFamily || 'var(--sp-font-family)'

    this.styleElement.textContent = `
      .sp-subtitles {
        position: absolute;
        left: 50%;
        transform: translateX(-50%);
        ${position}
        max-width: 80%;
        text-align: center;
        z-index: 15;
        pointer-events: none;
      }
      
      .sp-subtitle-text {
        display: inline-block;
        padding: 4px 12px;
        background: ${background};
        border-radius: 4px;
        font-size: ${fontSize};
        font-weight: 500;
        color: ${color};
        text-shadow: ${shadow};
        line-height: 1.4;
        white-space: pre-wrap;
        font-family: ${fontFamily};
      }
      
      .sp-subtitles:empty {
        display: none;
      }
    `
  }

  /**
   * HEX 转 RGBA
   */
  private hexToRgba(hex: string, alpha: number): string {
    const r = parseInt(hex.slice(1, 3), 16)
    const g = parseInt(hex.slice(3, 5), 16)
    const b = parseInt(hex.slice(5, 7), 16)
    return `rgba(${r}, ${g}, ${b}, ${alpha})`
  }

  /**
   * 更新活动字幕
   */
  private updateActiveCue(currentTime: number): void {
    if (!this.containerElement) return

    // 查找当前时间对应的字幕
    let foundIndex = -1
    for (let i = 0; i < this.cues.length; i++) {
      const cue = this.cues[i]
      if (currentTime >= cue.startTime && currentTime <= cue.endTime) {
        foundIndex = i
        break
      }
    }

    // 如果变化了，更新显示
    if (foundIndex !== this.activeCueIndex) {
      this.activeCueIndex = foundIndex
      
      if (foundIndex >= 0) {
        const cue = this.cues[foundIndex]
        this.containerElement.innerHTML = `<span class="sp-subtitle-text">${this.escapeHtml(cue.text)}</span>`
      } else {
        this.containerElement.innerHTML = ''
      }
    }
  }

  /**
   * HTML 转义
   */
  private escapeHtml(text: string): string {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\n/g, '<br>')
  }

  /**
   * 加载字幕轨道
   */
  async loadTrack(track: SubtitleTrack): Promise<void> {
    this.currentTrack = track
    this.cues = []
    this.activeCueIndex = -1

    let content = track.content

    // 从 URL 加载
    if (!content && track.url) {
      try {
        const response = await fetch(track.url)
        content = await response.text()
      } catch (e) {
        console.error('[SubtitlesPlugin] Failed to load subtitle:', e)
        return
      }
    }

    if (!content) return

    // 解析字幕
    const isVtt = content.trimStart().startsWith('WEBVTT')
    this.cues = isVtt ? this.parseVTT(content) : this.parseSRT(content)
    
    console.log(`[SubtitlesPlugin] Loaded ${this.cues.length} cues from ${track.label}`)
  }

  /**
   * 解析 VTT 格式
   */
  private parseVTT(content: string): SubtitleCue[] {
    const cues: SubtitleCue[] = []
    const lines = content.split(/\r?\n/)
    let i = 0

    // 跳过头部
    while (i < lines.length && !lines[i].includes('-->')) {
      i++
    }

    while (i < lines.length) {
      const line = lines[i].trim()
      
      if (line.includes('-->')) {
        const [startStr, endStr] = line.split('-->').map(s => s.trim().split(' ')[0])
        const startTime = this.parseTime(startStr)
        const endTime = this.parseTime(endStr)
        
        // 收集文本行
        const textLines: string[] = []
        i++
        while (i < lines.length && lines[i].trim() !== '') {
          textLines.push(lines[i].trim())
          i++
        }
        
        if (textLines.length > 0) {
          cues.push({
            id: `cue-${cues.length}`,
            startTime,
            endTime,
            text: textLines.join('\n').replace(/<[^>]+>/g, '') // 移除 HTML 标签
          })
        }
      }
      i++
    }

    return cues
  }

  /**
   * 解析 SRT 格式
   */
  private parseSRT(content: string): SubtitleCue[] {
    const cues: SubtitleCue[] = []
    const blocks = content.trim().split(/\r?\n\r?\n/)

    for (const block of blocks) {
      const lines = block.split(/\r?\n/)
      if (lines.length < 2) continue

      // 查找时间行
      let timeLineIndex = 0
      for (let i = 0; i < lines.length; i++) {
        if (lines[i].includes('-->')) {
          timeLineIndex = i
          break
        }
      }

      const timeLine = lines[timeLineIndex]
      if (!timeLine?.includes('-->')) continue

      const [startStr, endStr] = timeLine.split('-->').map(s => s.trim())
      const startTime = this.parseTime(startStr)
      const endTime = this.parseTime(endStr)

      const textLines = lines.slice(timeLineIndex + 1).filter(l => l.trim())
      if (textLines.length > 0) {
        cues.push({
          id: `cue-${cues.length}`,
          startTime,
          endTime,
          text: textLines.join('\n').replace(/<[^>]+>/g, '')
        })
      }
    }

    return cues
  }

  /**
   * 解析时间字符串
   */
  private parseTime(timeStr: string): number {
    // 支持 HH:MM:SS,mmm 或 HH:MM:SS.mmm 格式
    const parts = timeStr.replace(',', '.').split(':')
    
    if (parts.length === 3) {
      const [h, m, s] = parts
      return parseInt(h) * 3600 + parseInt(m) * 60 + parseFloat(s)
    } else if (parts.length === 2) {
      const [m, s] = parts
      return parseInt(m) * 60 + parseFloat(s)
    }
    
    return parseFloat(timeStr) || 0
  }

  /**
   * 设置可用字幕轨道
   */
  setTracks(tracks: SubtitleTrack[]): void {
    this.tracks = tracks
    
    if (this.options.autoLoad && tracks.length > 0) {
      const defaultTrack = tracks.find(t => t.default) || tracks[0]
      this.loadTrack(defaultTrack)
      this.enable()
    }
  }

  /**
   * 获取可用轨道
   */
  getTracks(): SubtitleTrack[] {
    return this.tracks
  }

  /**
   * 获取当前轨道
   */
  getCurrentTrack(): SubtitleTrack | null {
    return this.currentTrack
  }

  /**
   * 切换到指定轨道
   */
  async switchTrack(trackId: string): Promise<void> {
    const track = this.tracks.find(t => t.id === trackId)
    if (track) {
      await this.loadTrack(track)
      this.enable()
    }
  }

  /**
   * 切换到下一个轨道
   */
  async nextTrack(): Promise<void> {
    if (this.tracks.length === 0) return
    
    const currentIndex = this.currentTrack 
      ? this.tracks.findIndex(t => t.id === this.currentTrack?.id)
      : -1
    
    const nextIndex = (currentIndex + 1) % this.tracks.length
    await this.loadTrack(this.tracks[nextIndex])
    this.enable()
  }

  /**
   * 启用字幕
   */
  enable(): void {
    this.enabled = true
    if (this.containerElement) {
      this.containerElement.style.display = ''
    }
  }

  /**
   * 禁用字幕
   */
  disable(): void {
    this.enabled = false
    if (this.containerElement) {
      this.containerElement.innerHTML = ''
      this.containerElement.style.display = 'none'
    }
  }

  /**
   * 切换启用状态
   */
  toggle(): void {
    if (this.enabled) {
      this.disable()
    } else {
      this.enable()
    }
  }

  /**
   * 是否启用
   */
  isEnabled(): boolean {
    return this.enabled
  }

  /**
   * 设置样式
   */
  setStyle(style: Partial<SubtitleStyle>): void {
    this.style = { ...this.style, ...style }
    this.updateStyles()
  }

  /**
   * 获取样式
   */
  getStyle(): SubtitleStyle {
    return { ...this.style }
  }

  onDestroy(): void {
    this.containerElement?.remove()
    this.styleElement?.remove()
  }

  destroy(): void {
    this.onDestroy()
    this.context = null
    this.tracks = []
    this.cues = []
    this.currentTrack = null
  }
}

export default SubtitlesPlugin
