/**
 * 类型安全的事件发射器
 * 支持泛型事件类型定义
 */

export type EventHandler<T = any> = (data: T) => void
export type EventMap = Record<string, any>

export class EventEmitter<Events extends EventMap = EventMap> {
  private listeners: Map<keyof Events, Set<EventHandler>> = new Map()
  private onceListeners: Map<keyof Events, Set<EventHandler>> = new Map()

  /**
   * 注册事件监听器
   */
  on<K extends keyof Events>(event: K, handler: EventHandler<Events[K]>): this {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set())
    }
    this.listeners.get(event)!.add(handler)
    return this
  }

  /**
   * 注册一次性事件监听器
   */
  once<K extends keyof Events>(event: K, handler: EventHandler<Events[K]>): this {
    if (!this.onceListeners.has(event)) {
      this.onceListeners.set(event, new Set())
    }
    this.onceListeners.get(event)!.add(handler)
    return this
  }

  /**
   * 移除事件监听器
   */
  off<K extends keyof Events>(event: K, handler?: EventHandler<Events[K]>): this {
    if (handler) {
      this.listeners.get(event)?.delete(handler)
      this.onceListeners.get(event)?.delete(handler)
    } else {
      this.listeners.delete(event)
      this.onceListeners.delete(event)
    }
    return this
  }

  /**
   * 触发事件
   */
  emit<K extends keyof Events>(event: K, data?: Events[K]): this {
    // 执行普通监听器
    this.listeners.get(event)?.forEach(handler => {
      try {
        handler(data)
      } catch (err) {
        console.error(`[EventEmitter] Error in handler for "${String(event)}":`, err)
      }
    })

    // 执行一次性监听器
    const onceHandlers = this.onceListeners.get(event)
    if (onceHandlers) {
      onceHandlers.forEach(handler => {
        try {
          handler(data)
        } catch (err) {
          console.error(`[EventEmitter] Error in once handler for "${String(event)}":`, err)
        }
      })
      this.onceListeners.delete(event)
    }

    return this
  }

  /**
   * 检查是否有某事件的监听器
   */
  hasListeners<K extends keyof Events>(event: K): boolean {
    return (this.listeners.get(event)?.size ?? 0) > 0 ||
           (this.onceListeners.get(event)?.size ?? 0) > 0
  }

  /**
   * 获取某事件的监听器数量
   */
  listenerCount<K extends keyof Events>(event: K): number {
    return (this.listeners.get(event)?.size ?? 0) +
           (this.onceListeners.get(event)?.size ?? 0)
  }

  /**
   * 移除所有监听器
   */
  removeAllListeners(): this {
    this.listeners.clear()
    this.onceListeners.clear()
    return this
  }

  /**
   * 销毁实例
   */
  destroy(): void {
    this.removeAllListeners()
  }
}

export default EventEmitter
