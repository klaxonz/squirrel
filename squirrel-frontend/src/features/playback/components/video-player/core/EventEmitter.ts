/**
 * 类型安全的事件发射器
 * 支持泛型事件类型定义
 */

import { playerLogger, type PlayerLogger } from './logger'

// EventMap is the constraint for user-supplied event→payload maps. The default
// `Record<string, unknown>` keeps the untyped fallback sound, while the class
// constraint is `object` (not `Record<string, unknown>`) so concrete interfaces
// like PlayerEvents satisfy it — interfaces don't carry a string index signature,
// so `extends Record<string, unknown>` rejects them. Every concrete emitter in
// this codebase is instantiated with a typed Events map (e.g. PlayerEvents), so
// the untyped default is only the fallback. `unknown` (not `any`) propagates:
// callers of `on`/`emit` get checked payloads for typed maps, and the untyped
// fallback forces the consumer to narrow rather than silently accepting anything.
export type EventHandler<T = unknown> = (data: T) => void
export type EventMap = Record<string, unknown>

// Erased handler storage. A single `Map<keyof Events, Set<EventHandler<Events[K]>>>`
// isn't expressible in TypeScript (a heterogeneous Map can't be parameterised per
// key), so storage holds the type-erased union and each `on`/`emit`/`off` site is
// the single, well-typed (de)serialisation boundary. This is the standard pattern
// used by strongly-typed TS emitters (mitt, nanoevents): the public API is fully
// generic; only the internal Set is erased. The cast is the soundness seam, not a
// lossy `any` — handlers are always read back through the same `Events[K]` lens.
type StoredHandler<Events extends object> = EventHandler<Events[keyof Events]>

export class EventEmitter<Events extends object = EventMap> {
  private listeners: Map<keyof Events, Set<StoredHandler<Events>>> = new Map()
  private onceListeners: Map<keyof Events, Set<StoredHandler<Events>>> = new Map()
  private logger: PlayerLogger

  constructor() {
    this.logger = playerLogger
  }

  /**
   * 注册事件监听器
   */
  on<K extends keyof Events>(event: K, handler: EventHandler<Events[K]>): this {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set())
    }
    this.listeners.get(event)!.add(handler as StoredHandler<Events>)
    return this
  }

  /**
   * 注册一次性事件监听器
   */
  once<K extends keyof Events>(event: K, handler: EventHandler<Events[K]>): this {
    if (!this.onceListeners.has(event)) {
      this.onceListeners.set(event, new Set())
    }
    this.onceListeners.get(event)!.add(handler as StoredHandler<Events>)
    return this
  }

  /**
   * 移除事件监听器
   */
  off<K extends keyof Events>(event: K, handler?: EventHandler<Events[K]>): this {
    if (handler) {
      this.listeners.get(event)?.delete(handler as StoredHandler<Events>)
      this.onceListeners.get(event)?.delete(handler as StoredHandler<Events>)
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
    // `data?` widens to `Events[K] | undefined`; for void-payload events (e.g.
    // `play: void`) callers legitimately omit it. Dispatch through the same
    // erased handler lens used at registration so the optional-ness stays inside
    // this single seam rather than leaking into the stored-handler type.
    const dispatch = (handler: StoredHandler<Events>) =>
      (handler as EventHandler<Events[K]>)(data as Events[K])

    // 执行普通监听器
    this.listeners.get(event)?.forEach(handler => {
      try {
        dispatch(handler)
      } catch (err) {
        this.logger.error(`[EventEmitter] Error in handler for "${String(event)}"`, err)
      }
    })

    // 执行一次性监听器
    const onceHandlers = this.onceListeners.get(event)
    if (onceHandlers) {
      onceHandlers.forEach(handler => {
        try {
          dispatch(handler)
        } catch (err) {
          this.logger.error(`[EventEmitter] Error in once handler for "${String(event)}"`, err)
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
