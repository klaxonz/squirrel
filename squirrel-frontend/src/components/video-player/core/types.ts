/**
 * 播放器插件系统类型定义
 */

import type { EventEmitter } from './EventEmitter'

// 播放器事件类型
export interface PlayerEvents {
  // 播放状态
  play: void
  pause: void
  ended: void
  waiting: void
  canplay: void
  canplaythrough: void

  // 时间相关
  timeupdate: { currentTime: number; duration: number }
  durationchange: number
  seeking: number
  seeked: number
  progress: { buffered: TimeRanges; duration: number }

  // 音量
  volumechange: { volume: number; muted: boolean }

  // 质量
  qualitychange: { quality: string; auto: boolean; id?: number }
  qualitiesloaded: QualityLevel[]

  // 播放速率
  ratechange: number

  // 错误
  error: PlayerError

  // 源相关
  sourcechange: MediaSource
  loadsstart: void
  loadedmetadata: { duration: number; videoWidth: number; videoHeight: number }
  loadeddata: void

  // 全屏/画中画
  fullscreenchange: boolean
  enterpictureinpicture: void
  leavepictureinpicture: void

  // 插件生命周期
  pluginregistered: { name: string; plugin: PlayerPlugin }
  pluginunregistered: string

  // 通用
  statechange: PlayerState
  destroy: void
}

// 质量级别
export interface QualityLevel {
  id: string | number
  label: string
  width?: number
  height?: number
  bitrate?: number
  codec?: string
}

// 媒体源配置
export interface MediaSource {
  src: string
  type?: 'auto' | 'native' | 'hls' | 'dash'
  poster?: string
  title?: string
}

// 播放器错误
export interface PlayerError {
  code: string
  message: string
  fatal: boolean
  details?: any
}

// 播放器状态
export interface PlayerState {
  playing: boolean
  paused: boolean
  ended: boolean
  waiting: boolean
  seeking: boolean
  currentTime: number
  duration: number
  buffered: number
  volume: number
  muted: boolean
  playbackRate: number
  fullscreen: boolean
  pip: boolean
  quality: string | null
  autoQuality: boolean
}

// 插件上下文 - 暴露给插件的 API
export interface PluginContext {
  // 播放器核心
  readonly videoElement: HTMLVideoElement | null
  readonly state: PlayerState

  // 事件系统
  on: EventEmitter<PlayerEvents>['on']
  off: EventEmitter<PlayerEvents>['off']
  emit: EventEmitter<PlayerEvents>['emit']
  once: EventEmitter<PlayerEvents>['once']

  // 播放控制
  play(): Promise<void>
  pause(): void
  seek(time: number): void
  setVolume(volume: number): void
  setMuted(muted: boolean): void
  setPlaybackRate(rate: number): void

  // 质量控制
  setQuality(quality: string | number): void
  getQualities(): QualityLevel[]
  registerQualities(qualities: QualityLevel[]): void
  registerCurrentQualityId(id?: number): void


  // 媒体源
  setSource(source: MediaSource): void
  getSource(): MediaSource | null

  // 全屏/画中画
  requestFullscreen(): Promise<void>
  exitFullscreen(): Promise<void>
  requestPictureInPicture(): Promise<void>
  exitPictureInPicture(): Promise<void>

  // 错误处理
  reportError(error: PlayerError): void

  // 插件间通信
  getPlugin<T extends PlayerPlugin>(name: string): T | null
}

// 插件生命周期钩子
export interface PluginHooks {
  onInit?(): void | Promise<void>
  onReady?(): void
  onPlay?(): void
  onPause?(): void
  onSeek?(time: number): void
  onTimeUpdate?(currentTime: number, duration: number): void
  onVolumeChange?(volume: number, muted: boolean): void
  onQualityChange?(quality: string): void
  onRateChange?(rate: number): void
  onError?(error: PlayerError): void
  onSourceChange?(source: MediaSource): void
  onFullscreenChange?(isFullscreen: boolean): void
  onDestroy?(): void
}

// 插件接口
export interface PlayerPlugin extends PluginHooks {
  readonly name: string
  readonly version?: string

  install(context: PluginContext, options?: any): void | Promise<void>
  destroy?(): void
}

// 插件配置
export interface PluginConfig<T = any> {
  plugin: PlayerPlugin | (() => PlayerPlugin)
  options?: T
  enabled?: boolean
}

// 插件管理器接口
export interface IPluginManager {
  register(plugin: PlayerPlugin, options?: any): Promise<void>
  unregister(name: string): void
  get<T extends PlayerPlugin>(name: string): T | null
  getAll(): PlayerPlugin[]
  has(name: string): boolean
  destroy(): void
}

// 媒体类型检测结果
export interface MediaTypeDetection {
  type: 'native' | 'hls' | 'dash' | 'unknown'
  isSupported: boolean
  requiresPlugin: boolean
  pluginName?: string
}
