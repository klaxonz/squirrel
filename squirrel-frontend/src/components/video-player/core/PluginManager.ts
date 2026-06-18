/**
 * 插件管理器
 * 负责插件的注册、生命周期管理和通信
 */

import type {
  PlayerPlugin,
  PluginContext,
  IPluginManager,
  PlayerEvents
} from './types'
import { EventEmitter } from './EventEmitter'
import { playerLogger, type PlayerLogger } from './logger'

export class PluginManager implements IPluginManager {
  private plugins: Map<string, PlayerPlugin> = new Map()
  private context: PluginContext | null = null
  private events: EventEmitter<PlayerEvents>
  private logger: PlayerLogger

  constructor(events: EventEmitter<PlayerEvents>) {
    this.events = events
    this.logger = playerLogger
    this.setupEventForwarding()
  }

  /**
   * 设置插件上下文
   */
  setContext(context: PluginContext): void {
    this.context = context
  }

  /**
   * 设置事件转发到插件钩子
   */
  private setupEventForwarding(): void {
    this.events.on('play', () => this.callHook('onPlay'))
    this.events.on('pause', () => this.callHook('onPause'))
    this.events.on('seeking', (time) => this.callHook('onSeek', time))
    this.events.on('timeupdate', ({ currentTime, duration }) => 
      this.callHook('onTimeUpdate', currentTime, duration)
    )
    this.events.on('volumechange', ({ volume, muted }) => 
      this.callHook('onVolumeChange', volume, muted)
    )
    this.events.on('qualitychange', ({ quality }) => 
      this.callHook('onQualityChange', quality)
    )
    this.events.on('ratechange', (rate) => this.callHook('onRateChange', rate))
    this.events.on('error', (error) => this.callHook('onError', error))
    this.events.on('sourcechange', (source) => this.callHook('onSourceChange', source))
    this.events.on('fullscreenchange', (isFs) => this.callHook('onFullscreenChange', isFs))
  }

  /**
   * 调用所有插件的指定钩子
   */
  private callHook(hookName: keyof PlayerPlugin, ...args: unknown[]): void {
    this.plugins.forEach(plugin => {
      const hook = plugin[hookName]
      if (typeof hook === 'function') {
        try {
          (hook as (...a: unknown[]) => void).apply(plugin, args)
        } catch (err) {
          this.logger.error(`[PluginManager] Error in ${plugin.name}.${hookName}`, err)
        }
      }
    })
  }

  /**
   * 注册插件
   */
  async register(plugin: PlayerPlugin, options?: unknown): Promise<void> {
    if (this.plugins.has(plugin.name)) {
      this.logger.warn(`[PluginManager] Plugin "${plugin.name}" already registered, skipping`)
      return
    }

    if (!this.context) {
      throw new Error('[PluginManager] Context not set. Call setContext() first.')
    }

    try {
      // 安装插件
      await plugin.install(this.context, options)

      // 调用初始化钩子
      if (plugin.onInit) {
        await plugin.onInit()
      }

      this.plugins.set(plugin.name, plugin)
      this.events.emit('pluginregistered', { name: plugin.name, plugin })

      this.logger.debug(`[PluginManager] Plugin "${plugin.name}" registered`)
    } catch (err) {
      this.logger.error(`[PluginManager] Failed to register plugin "${plugin.name}"`, err)
      throw err
    }
  }

  /**
   * 注销插件
   */
  unregister(name: string): void {
    const plugin = this.plugins.get(name)
    if (!plugin) {
      this.logger.warn(`[PluginManager] Plugin "${name}" not found`)
      return
    }

    try {
      // 调用销毁钩子
      if (plugin.onDestroy) {
        plugin.onDestroy()
      }

      // 调用插件自身的销毁方法
      if (plugin.destroy) {
        plugin.destroy()
      }

      this.plugins.delete(name)
      this.events.emit('pluginunregistered', name)

      this.logger.debug(`[PluginManager] Plugin "${name}" unregistered`)
    } catch (err) {
      this.logger.error(`[PluginManager] Error unregistering plugin "${name}"`, err)
    }
  }

  /**
   * 获取插件实例
   */
  // ponytail: T is unconstrained (not `extends PlayerPlugin`) because callers
  // often want a structural view of a plugin (e.g. QualityController,
  // SubtitleController) that exposes engine-facing methods beyond the base
  // PlayerPlugin interface. The cast is the whole point of get().
  get<T = PlayerPlugin>(name: string): T | null {
    return (this.plugins.get(name) as T) || null
  }

  /**
   * 获取所有插件
   */
  getAll(): PlayerPlugin[] {
    return Array.from(this.plugins.values())
  }

  /**
   * 检查插件是否已注册
   */
  has(name: string): boolean {
    return this.plugins.has(name)
  }

  /**
   * 销毁所有插件
   */
  destroy(): void {
    // 按注册顺序的逆序销毁
    const names = Array.from(this.plugins.keys()).reverse()
    names.forEach(name => this.unregister(name))
    this.context = null
  }
}

export default PluginManager
