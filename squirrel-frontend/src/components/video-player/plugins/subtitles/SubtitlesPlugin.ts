/**
 * 字幕插件
 * 支持 VTT/SRT 格式、样式自定义、多轨道切换
 */

import type { PlayerPlugin, PluginContext, SubtitleTrack as CoreSubtitleTrack } from '../../core/types'

export type SubtitleTrack = CoreSubtitleTrack

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

export interface SubtitlePreset {
  id: string
  label: string
  style: Partial<SubtitleStyle>
}

export const BUILT_IN_PRESETS: SubtitlePreset[] = [
  {
    id: 'default',
    label: '默认',
    style: { fontSize: 'medium', color: '#ffffff', backgroundColor: 'rgba(0,0,0,0.8)', backgroundOpacity: 0.8, position: 'bottom', textShadow: true },
  },
  {
    id: 'high-contrast',
    label: '高对比',
    style: { fontSize: 'large', color: '#ffff00', backgroundColor: '#000000', backgroundOpacity: 1, position: 'bottom', textShadow: false },
  },
  {
    id: 'subtle',
    label: '柔和',
    style: { fontSize: 'small', color: 'rgba(255,255,255,0.8)', backgroundColor: 'rgba(0,0,0,0.5)', backgroundOpacity: 0.5, position: 'bottom', textShadow: false },
  },
  {
    id: 'top-outline',
    label: '顶部描边',
    style: { fontSize: 'medium', color: '#ffffff', backgroundColor: 'transparent', backgroundOpacity: 0, position: 'top', textShadow: true },
  },
]

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
  private subtitleOffset: number = 0
  private scopeId: string
  private style: SubtitleStyle
  private styleElement: HTMLStyleElement | null = null
  private containerElement: HTMLElement | null = null
  private syncAnimationFrameId: number | null = null
  private syncVideoFrameId: number | null = null
  private loadRequestId: number = 0
  private unavailableTrackIds = new Set<string>()

  constructor() {
    this.options = {}
    this.scopeId = `sp-subtitles-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
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

  onPlay(): void {
    this.startSyncLoop()
  }

  onPause(): void {
    this.stopSyncLoop()
    if (this.enabled) {
      this.refreshCurrentCue()
    }
  }

  onSeek(): void {
    // 重置活动字幕索引，让 timeupdate 重新计算
    this.activeCueIndex = -1
    this.refreshCurrentCue()
  }

  /**
   * 创建样式元素
   */
  private createStyleElement(): void {
    if (typeof document === 'undefined') return
    
    this.styleElement = document.createElement('style')
    this.styleElement.dataset.spSubtitlesOwner = this.scopeId
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
    this.containerElement.dataset.spSubtitlesOwner = this.scopeId
    this.containerElement.setAttribute('aria-live', 'polite')
    this.containerElement.setAttribute('aria-atomic', 'true')
    parent.appendChild(this.containerElement)
  }

  /**
   * 更新样式
   */
  private updateStyles(): void {
    if (!this.styleElement) return

    const scope = `.sp-subtitles[data-sp-subtitles-owner="${this.scopeId}"]`
    const fontSizeMap: Record<string, string> = {
      small: '16px',
      medium: '18px',
      large: '24px',
      xlarge: '32px'
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
      ${scope} {
        position: absolute;
        left: 50%;
        transform: translateX(-50%);
        ${position}
        max-width: 80%;
        text-align: center;
        z-index: 15;
        pointer-events: none;
      }
      
      ${scope} .sp-subtitle-text {
        display: inline-block;
        padding: 4px 8px;
        background: ${background};
        border-radius: 2px;
        font-size: ${fontSize};
        font-weight: 500;
        color: ${color};
        text-shadow: ${shadow};
        line-height: 1.4;
        white-space: pre-wrap;
        font-family: ${fontFamily};
      }
      
      ${scope}:empty {
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

    const adjustedTime = currentTime + this.subtitleOffset
    let foundIndex = this.findCueIndex(adjustedTime)

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

  private findCueIndex(currentTime: number): number {
    const activeCue = this.activeCueIndex >= 0 ? this.cues[this.activeCueIndex] : null
    if (activeCue && currentTime >= activeCue.startTime && currentTime <= activeCue.endTime) {
      return this.activeCueIndex
    }

    if (this.activeCueIndex >= 0) {
      if (activeCue && currentTime > activeCue.endTime) {
        return this.findCueIndexForward(this.activeCueIndex + 1, currentTime)
      }

      if (activeCue && currentTime < activeCue.startTime) {
        return this.findCueIndexBackward(this.activeCueIndex - 1, currentTime)
      }
    }

    return this.findCueIndexByBinarySearch(currentTime)
  }

  private findCueIndexForward(startIndex: number, currentTime: number): number {
    for (let i = startIndex; i < this.cues.length; i++) {
      const cue = this.cues[i]
      if (currentTime < cue.startTime) {
        return -1
      }
      if (currentTime <= cue.endTime) {
        return i
      }
    }

    return -1
  }

  private findCueIndexBackward(startIndex: number, currentTime: number): number {
    for (let i = startIndex; i >= 0; i--) {
      const cue = this.cues[i]
      if (currentTime > cue.endTime) {
        return -1
      }
      if (currentTime >= cue.startTime) {
        return i
      }
    }

    return -1
  }

  private findCueIndexByBinarySearch(currentTime: number): number {
    let left = 0
    let right = this.cues.length - 1

    while (left <= right) {
      const mid = Math.floor((left + right) / 2)
      const cue = this.cues[mid]

      if (currentTime < cue.startTime) {
        right = mid - 1
        continue
      }

      if (currentTime > cue.endTime) {
        left = mid + 1
        continue
      }

      return mid
    }

    return -1
  }

  /**
   * 清空当前渲染的字幕文本
   */
  private clearRenderedCue(): void {
    if (!this.containerElement) return
    this.containerElement.innerHTML = ''
  }

  /**
   * 按当前播放时间立即刷新字幕
   */
  private refreshCurrentCue(): void {
    const currentTime = this.context?.videoElement?.currentTime ?? this.context?.state.currentTime ?? 0
    this.updateActiveCue(currentTime)
  }

  private startSyncLoop(): void {
    const video = this.context?.videoElement
    if (!this.enabled || !video || this.cues.length === 0) return
    if (video.paused || video.ended) return

    const enhancedVideo = video as HTMLVideoElement & {
      requestVideoFrameCallback?: (callback: () => void) => number
    }

    if (typeof enhancedVideo.requestVideoFrameCallback === 'function') {
      this.scheduleVideoFrameSync(enhancedVideo)
      return
    }

    this.scheduleAnimationFrameSync(video)
  }

  private stopSyncLoop(): void {
    if (this.syncAnimationFrameId !== null && typeof cancelAnimationFrame === 'function') {
      cancelAnimationFrame(this.syncAnimationFrameId)
    }
    this.syncAnimationFrameId = null

    const video = this.context?.videoElement as (HTMLVideoElement & {
      cancelVideoFrameCallback?: (handle: number) => void
    }) | null
    if (this.syncVideoFrameId !== null && typeof video?.cancelVideoFrameCallback === 'function') {
      video.cancelVideoFrameCallback(this.syncVideoFrameId)
    }
    this.syncVideoFrameId = null
  }

  private scheduleVideoFrameSync(video: HTMLVideoElement & {
    requestVideoFrameCallback?: (callback: () => void) => number
  }): void {
    if (this.syncVideoFrameId !== null || typeof video.requestVideoFrameCallback !== 'function') return

    this.syncVideoFrameId = video.requestVideoFrameCallback(() => {
      this.syncVideoFrameId = null
      if (!this.enabled) return

      this.refreshCurrentCue()
      if (!video.paused && !video.ended) {
        this.scheduleVideoFrameSync(video)
      }
    })
  }

  private scheduleAnimationFrameSync(video: HTMLVideoElement): void {
    if (this.syncAnimationFrameId !== null || typeof requestAnimationFrame !== 'function') return

    const tick = () => {
      this.syncAnimationFrameId = null
      if (!this.enabled) return

      this.refreshCurrentCue()
      if (!video.paused && !video.ended) {
        this.syncAnimationFrameId = requestAnimationFrame(tick)
      }
    }

    this.syncAnimationFrameId = requestAnimationFrame(tick)
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
  async loadTrack(track: SubtitleTrack): Promise<boolean> {
    const requestId = ++this.loadRequestId
    this.currentTrack = track
    this.cues = []
    this.activeCueIndex = -1
    this.clearRenderedCue()
    this.stopSyncLoop()

    let content = track.content

    // 从 URL 加载
    if (!content && track.url) {
      if (this.unavailableTrackIds.has(track.id)) {
        this.context?.logger.debug('[SubtitlesPlugin] Skipping known unavailable subtitle track', { trackId: track.id })
        return false
      }

      try {
        const response = await fetch(track.url)
        if (!response.ok) {
          if (response.status === 404) {
            this.unavailableTrackIds.add(track.id)
            this.context?.logger.warn('[SubtitlesPlugin] Subtitle track returned 404, degrading subtitles only', {
              trackId: track.id,
              url: track.url,
            })
            return false
          }
          throw new Error(`HTTP ${response.status}`)
        }
        content = await response.text()
        if (requestId !== this.loadRequestId) {
          return false
        }
        if (content) {
          track.content = content
        }
      } catch (e) {
        this.context?.logger.warn('[SubtitlesPlugin] Failed to load subtitle, degrading without interrupting playback', e)
        return false
      }
    }

    if (requestId !== this.loadRequestId) {
      return false
    }

    if (!content) return false

    // 解析字幕
    const isVtt = content.trimStart().startsWith('WEBVTT')
    this.cues = isVtt ? this.parseVTT(content) : this.parseSRT(content)

    if (this.cues.length === 0) {
      this.context?.logger.warn('[SubtitlesPlugin] Subtitle track parsed with no cues, degrading subtitles only', {
        trackId: track.id,
      })
      return false
    }

    if (this.enabled) {
      this.refreshCurrentCue()
      this.startSyncLoop()
    }
    
    this.context?.logger.debug(`[SubtitlesPlugin] Loaded ${this.cues.length} cues from ${track.label}`)
    return true
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
          textLines.push(lines[i])
          i++
        }
        
        if (textLines.length > 0) {
          const expandedCues = this.expandTimedVttCue(startTime, endTime, textLines.join('\n'))
          if (expandedCues.length > 0) {
            cues.push(...expandedCues.map((cue, index) => ({
              ...cue,
              id: `cue-${cues.length + index}`,
            })))
          } else {
            cues.push({
              id: `cue-${cues.length}`,
              startTime,
              endTime,
              text: this.sanitizeSubtitleText(textLines.join('\n'))
            })
          }
        }
      }
      i++
    }

    return cues
  }

  private expandTimedVttCue(startTime: number, endTime: number, rawText: string): Array<Omit<SubtitleCue, 'id'>> {
    const timestampPattern = /<(\d{2}:\d{2}:\d{2}\.\d{3})>/g
    if (!timestampPattern.test(rawText)) {
      return []
    }
    timestampPattern.lastIndex = 0

    const cues: Array<Omit<SubtitleCue, 'id'>> = []
    let currentStart = startTime
    let currentText = ''
    let lastIndex = 0
    let match: RegExpExecArray | null

    while ((match = timestampPattern.exec(rawText)) !== null) {
      const fragment = rawText.slice(lastIndex, match.index)
      currentText += this.sanitizeVttFragment(fragment)

      const nextStart = this.parseTime(match[1])
      const sanitizedText = this.sanitizeSubtitleText(currentText)
      if (sanitizedText && nextStart > currentStart) {
        cues.push({
          startTime: currentStart,
          endTime: nextStart,
          text: sanitizedText,
        })
      }

      currentStart = Math.max(currentStart, nextStart)
      lastIndex = match.index + match[0].length
    }

    currentText += this.sanitizeVttFragment(rawText.slice(lastIndex))
    const finalText = this.sanitizeSubtitleText(currentText)
    if (finalText && endTime > currentStart) {
      cues.push({
        startTime: currentStart,
        endTime,
        text: finalText,
      })
    }

    return cues
  }

  private sanitizeVttFragment(text: string): string {
    return text.replace(/<\/?c(?:\.[^>]*)?>/g, '')
  }

  private sanitizeSubtitleText(text: string): string {
    return text
      .replace(/<[^>]+>/g, '')
      .replace(/\r/g, '')
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean)
      .join('\n')
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
  async setTracks(tracks: SubtitleTrack[]): Promise<void> {
    this.tracks = tracks
    this.unavailableTrackIds.clear()

    if (tracks.length === 0) {
      this.loadRequestId += 1
      this.currentTrack = null
      this.cues = []
      this.activeCueIndex = -1
      this.disable()
      return
    }

    if (this.options.autoLoad) {
      const defaultTrack = tracks.find(t => t.default) || tracks[0]
      const loaded = await this.loadTrack(defaultTrack)
      if (loaded) {
        this.enable()
      } else {
        this.disable()
      }
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
      const loaded = await this.loadTrack(track)
      if (loaded) {
        this.enable()
      } else {
        this.disable()
      }
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
    const loaded = await this.loadTrack(this.tracks[nextIndex])
    if (loaded) {
      this.enable()
    } else {
      this.disable()
    }
  }

  /**
   * 启用字幕
   */
  enable(): void {
    this.enabled = true
    if (this.containerElement) {
      this.containerElement.style.display = ''
    }
    this.refreshCurrentCue()
    this.startSyncLoop()
  }

  /**
   * 禁用字幕
   */
  disable(): void {
    this.enabled = false
    this.stopSyncLoop()
    if (this.containerElement) {
      this.clearRenderedCue()
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

  /**
   * 导出样式配置（供外部存储）
   */
  exportStyle(): SubtitleStyle {
    return { ...this.style }
  }

  /**
   * 导入样式配置（从外部存储恢复）
   */
  importStyle(style: Partial<SubtitleStyle>): void {
    this.style = { ...this.style, ...style }
    this.updateStyles()
  }

  /**
   * 应用预设样式
   */
  applyPreset(presetId: string): void {
    const preset = BUILT_IN_PRESETS.find(p => p.id === presetId)
    if (preset) {
      this.importStyle(preset.style)
    }
  }

  setSubtitleOffset(offsetSeconds: number): void {
    this.subtitleOffset = offsetSeconds
    this.refreshCurrentCue()
  }

  getSubtitleOffset(): number {
    return this.subtitleOffset
  }

  onDestroy(): void {
    this.stopSyncLoop()
    this.containerElement?.remove()
    this.styleElement?.remove()
  }

  destroy(): void {
    this.loadRequestId += 1
    this.onDestroy()
    this.context = null
    this.tracks = []
    this.cues = []
    this.currentTrack = null
  }
}

export default SubtitlesPlugin
