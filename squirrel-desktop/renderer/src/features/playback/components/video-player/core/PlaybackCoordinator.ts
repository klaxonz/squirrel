import type { PlayerError } from './types'

export type PlaybackPhase =
  | 'idle'
  | 'resolving'
  | 'loading'
  | 'ready'
  | 'playing'
  | 'paused'
  | 'seeking'
  | 'buffering'
  | 'recovering'
  | 'ended'
  | 'error'

export type PlaybackIntent = 'play' | 'pause'
export type PlaybackOperationKind = 'resolve' | 'load' | 'seek' | 'recover'
export type PlaybackLoadingStage = 'idle' | 'resolving' | 'fetching' | 'buffering' | 'recovering' | 'ready'

export interface PlaybackLifecycleSnapshot {
  phase: PlaybackPhase
  intent: PlaybackIntent
  loading: boolean
  loadingStage: PlaybackLoadingStage
  generation: number
  operationId: number
  operationKind: PlaybackOperationKind | null
  sourceKey: string
  seekTarget: number | null
  currentTime: number
  duration: number
  bufferedPercent: number
  error: PlayerError | null
}

export interface PlaybackOperationToken {
  readonly generation: number
  readonly operationId: number
  readonly kind: PlaybackOperationKind
  readonly signal: AbortSignal
}

export interface PlaybackOperationResult {
  readonly generation: number
  readonly operationId: number
  readonly kind: PlaybackOperationKind
  readonly phase: PlaybackPhase
  readonly currentTime: number
}

export type PlaybackStateListener = (
  state: Readonly<PlaybackLifecycleSnapshot>,
  previous: Readonly<PlaybackLifecycleSnapshot>,
) => void

const loadingStageForPhase = (phase: PlaybackPhase): PlaybackLoadingStage => {
  if (phase === 'resolving') return 'resolving'
  if (phase === 'loading') return 'fetching'
  if (phase === 'seeking' || phase === 'buffering') return 'buffering'
  if (phase === 'recovering') return 'recovering'
  if (phase === 'ready' || phase === 'playing' || phase === 'paused' || phase === 'ended') return 'ready'
  return 'idle'
}

const isLoadingPhase = (phase: PlaybackPhase): boolean => (
  phase === 'resolving'
  || phase === 'loading'
  || phase === 'seeking'
  || phase === 'buffering'
  || phase === 'recovering'
)

const abortError = (message: string): DOMException => new DOMException(message, 'AbortError')

/**
 * The single lifecycle authority for one app-scoped playback session.
 *
 * Provider resolution, media loading, seeking and recovery all share the same
 * generation/operation clock. Starting a newer source aborts every older async
 * completion, so stale provider or media events cannot resurrect old state.
 */
export class PlaybackCoordinator {
  private state: PlaybackLifecycleSnapshot = {
    phase: 'idle',
    intent: 'pause',
    loading: false,
    loadingStage: 'idle',
    generation: 0,
    operationId: 0,
    operationKind: null,
    sourceKey: '',
    seekTarget: null,
    currentTime: 0,
    duration: 0,
    bufferedPercent: 0,
    error: null,
  }

  private sourceController = new AbortController()
  private operationController = new AbortController()
  private listeners = new Set<PlaybackStateListener>()

  getSnapshot(): Readonly<PlaybackLifecycleSnapshot> {
    return this.state
  }

  subscribe(listener: PlaybackStateListener, emitCurrent = false): () => void {
    this.listeners.add(listener)
    if (emitCurrent) listener(this.state, this.state)
    return () => this.listeners.delete(listener)
  }

  beginResolving(sourceKey: string, intent: PlaybackIntent = 'play'): PlaybackOperationToken {
    this.abortSource('Playback source was superseded')
    const generation = this.state.generation + 1
    this.sourceController = new AbortController()
    this.patch({
      phase: 'resolving',
      intent,
      generation,
      sourceKey: String(sourceKey || ''),
      seekTarget: null,
      currentTime: 0,
      duration: 0,
      bufferedPercent: 0,
      error: null,
    })
    return this.beginOperation('resolve')
  }

  beginLoading(sourceKey: string, intent: PlaybackIntent = this.state.intent): PlaybackOperationToken {
    // A resolver hands its generation to the media pipeline. Direct engine use
    // (no resolver phase) starts a fresh source generation itself.
    if (this.state.phase !== 'resolving') {
      this.abortSource('Playback source was superseded')
      this.sourceController = new AbortController()
      this.patch({ generation: this.state.generation + 1 })
    }
    this.patch({
      phase: 'loading',
      intent,
      sourceKey: String(sourceKey || ''),
      seekTarget: null,
      currentTime: 0,
      duration: 0,
      bufferedPercent: 0,
      error: null,
    })
    return this.beginOperation('load')
  }

  beginSeek(target: number, shouldResume: boolean): PlaybackOperationToken {
    const seekTarget = Number.isFinite(target) ? Math.max(0, target) : this.state.currentTime
    this.patch({
      phase: 'seeking',
      intent: shouldResume ? 'play' : 'pause',
      seekTarget,
      currentTime: seekTarget,
      error: null,
    })
    return this.beginOperation('seek')
  }

  beginRecovery(): PlaybackOperationToken {
    this.patch({ phase: 'recovering', error: null })
    return this.beginOperation('recover')
  }

  setIntent(intent: PlaybackIntent): void {
    this.patch({ intent })
  }

  markBuffering(): void {
    if (
      this.state.phase === 'idle'
      || this.state.phase === 'resolving'
      || this.state.phase === 'error'
      || this.state.phase === 'ended'
    ) return
    this.patch({ phase: 'buffering' })
  }

  markReady(isActuallyPlaying = false): void {
    if (this.state.phase === 'idle' || this.state.phase === 'resolving') return
    const phase: PlaybackPhase = isActuallyPlaying
      ? 'playing'
      : (this.state.intent === 'pause' ? 'paused' : 'ready')
    this.patch({ phase, seekTarget: null, error: null })
  }

  markPlaying(): void {
    if (this.state.phase === 'idle' || this.state.phase === 'resolving') return
    this.patch({ phase: 'playing', intent: 'play', seekTarget: null, error: null })
  }

  markPaused(): void {
    if (this.state.phase === 'idle' || this.state.phase === 'resolving') return
    this.patch({ phase: 'paused', intent: 'pause', seekTarget: null })
  }

  markEnded(): void {
    if (this.state.phase === 'idle' || this.state.phase === 'resolving') return
    this.patch({ phase: 'ended', intent: 'pause', seekTarget: null })
  }

  updateMedia(values: Partial<Pick<PlaybackLifecycleSnapshot, 'currentTime' | 'duration' | 'bufferedPercent'>>): void {
    if (this.state.phase === 'idle' || this.state.phase === 'resolving') return
    const patch: Partial<PlaybackLifecycleSnapshot> = {}
    if (Number.isFinite(values.currentTime)) patch.currentTime = Math.max(0, Number(values.currentTime))
    if (Number.isFinite(values.duration)) patch.duration = Math.max(0, Number(values.duration))
    if (Number.isFinite(values.bufferedPercent)) {
      patch.bufferedPercent = Math.max(0, Math.min(100, Number(values.bufferedPercent)))
    }
    if (Object.keys(patch).length > 0) this.patch(patch)
  }

  fail(error: PlayerError): void {
    this.patch({ phase: 'error', error: { ...error }, seekTarget: null })
  }

  isCurrent(token: PlaybackOperationToken): boolean {
    return (
      !token.signal.aborted
      && token.generation === this.state.generation
      && token.operationId === this.state.operationId
    )
  }

  async waitFor(
    token: PlaybackOperationToken,
    predicate: (state: Readonly<PlaybackLifecycleSnapshot>) => boolean,
    timeoutMs: number,
  ): Promise<PlaybackOperationResult> {
    if (!this.isCurrent(token)) throw abortError('Playback operation is no longer current')
    if (predicate(this.state)) return this.resultFor(token)

    return await new Promise<PlaybackOperationResult>((resolve, reject) => {
      let timeoutId: ReturnType<typeof setTimeout> | null = null
      const cleanup = () => {
        unsubscribe()
        token.signal.removeEventListener('abort', onAbort)
        if (timeoutId) clearTimeout(timeoutId)
      }
      const finish = () => {
        cleanup()
        resolve(this.resultFor(token))
      }
      const onAbort = () => {
        cleanup()
        reject(abortError('Playback operation was aborted'))
      }
      const unsubscribe = this.subscribe((state) => {
        if (!this.isCurrent(token)) {
          onAbort()
          return
        }
        if (predicate(state)) finish()
      })

      token.signal.addEventListener('abort', onAbort, { once: true })
      timeoutId = setTimeout(() => {
        cleanup()
        reject(new Error(`Playback ${token.kind} operation timed out after ${timeoutMs}ms`))
      }, Math.max(1, timeoutMs))
    })
  }

  reset(): void {
    this.abortSource('Playback session was reset')
    this.sourceController = new AbortController()
    this.operationController = new AbortController()
    this.patch({
      phase: 'idle',
      intent: 'pause',
      generation: this.state.generation + 1,
      operationKind: null,
      sourceKey: '',
      seekTarget: null,
      currentTime: 0,
      duration: 0,
      bufferedPercent: 0,
      error: null,
    })
  }

  destroy(): void {
    this.reset()
    this.listeners.clear()
  }

  private beginOperation(kind: PlaybackOperationKind): PlaybackOperationToken {
    this.operationController.abort('Playback operation was superseded')
    this.operationController = new AbortController()
    const operationId = this.state.operationId + 1
    const sourceSignal = this.sourceController.signal
    const operationController = this.operationController
    if (sourceSignal.aborted) {
      operationController.abort(sourceSignal.reason)
    } else {
      sourceSignal.addEventListener('abort', () => operationController.abort(sourceSignal.reason), { once: true })
    }
    this.patch({ operationId, operationKind: kind })
    return {
      generation: this.state.generation,
      operationId,
      kind,
      signal: operationController.signal,
    }
  }

  private abortSource(reason: string): void {
    this.operationController.abort(reason)
    this.sourceController.abort(reason)
  }

  private resultFor(token: PlaybackOperationToken): PlaybackOperationResult {
    return {
      generation: token.generation,
      operationId: token.operationId,
      kind: token.kind,
      phase: this.state.phase,
      currentTime: this.state.currentTime,
    }
  }

  private patch(patch: Partial<PlaybackLifecycleSnapshot>): void {
    const previous = this.state
    const phase = patch.phase ?? previous.phase
    const next: PlaybackLifecycleSnapshot = {
      ...previous,
      ...patch,
      phase,
      loading: isLoadingPhase(phase),
      loadingStage: loadingStageForPhase(phase),
    }
    if (
      Object.keys(next).every((key) => (
        next[key as keyof PlaybackLifecycleSnapshot] === previous[key as keyof PlaybackLifecycleSnapshot]
      ))
    ) {
      return
    }
    this.state = next
    for (const listener of [...this.listeners]) listener(next, previous)
  }
}
