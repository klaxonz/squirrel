/**
 * Stream adapter seam — see docs/adr/0001-stream-adapter-and-sink.md.
 *
 * A StreamAdapter is an independent module that knows how to load and control
 * one streaming technology (HLS via hls.js, DASH via dashjs, DASH via shaka).
 * The engine instantiates one adapter per source and drives it through this
 * interface; it never reaches into a library by name. Stream adapters are NOT
 * PlayerPlugins — they do not register with PluginManager and do not
 * implement lifecycle hooks.
 *
 * The adapter drives the engine only through the StreamSink passed to
 * onSourceChange (qualitiesResolved / qualityChanged / loadingStateChanged /
 * error). StreamContext is a narrow read-only input (the <video> element,
 * playback state, logger) — it carries no reverse-driving methods.
 */

import type { PlayerLogger } from './logger'
import type { StreamSink } from './StreamSink'
import type {
  MediaSource,
  PlayerError,
  PlayerState,
  PlaybackRecoveryAction,
  PlaybackRecoveryContext,
  QualityLevel,
  QualitySelectionRequest,
} from './types'

/**
 * Engine → adapter input (read-only). The adapter reads the <video> element
 * and current playback state from here; it has no way to mutate engine state
 * except by calling back through the StreamSink handed to onSourceChange.
 */
export interface StreamContext {
  /** Lazy read of the engine's <video> element (may be null until attached). */
  readonly videoElement: () => HTMLVideoElement | null
  /** Engine playback state snapshot (adapters read .quality / .playing). */
  readonly getState: () => PlayerState
  readonly logger: PlayerLogger
}

export interface StreamSeekResult {
  /** True only when the adapter observed a frame from the seek destination. */
  visuallyReady: boolean
}

/**
 * Engine → adapter control. The four optional codec-family methods are present
 * only on the DASH adapters; the runtime probes with `adapter.getAvailableCodecFamilies?.()`
 * rather than branching on source type.
 */
export interface StreamAdapter {
  /** Load a source and deliver resolved state through the sink. */
  onSourceChange(source: MediaSource, sink: StreamSink): void
  /** Apply a quality selection (id, label, or runtime selection). */
  setQuality(quality: QualitySelectionRequest): void
  /** Recovery strategy for a playback error (HLS level fallback, DASH track switch, etc.). */
  recoverPlayback(error: PlayerError, context: PlaybackRecoveryContext): PlaybackRecoveryAction | Promise<PlaybackRecoveryAction>

  /**
   * Optional EARLY recovery hook, consulted by error-recovery BEFORE the generic
   * retry/quality chain. Provider adapters use it for errors the generic chain
   * cannot fix (e.g. a seek-triggered HTTP 400/403 on a session-bound SABR
   * stream: refresh the session, then degrade to the bundled DASH fallback).
   * Return 'handled' to take over; return null (or any other value) to fall
   * through to the generic strategy untouched.
   */
  handleProviderRecovery?(error: PlayerError, context: PlaybackRecoveryContext): PlaybackRecoveryAction | Promise<PlaybackRecoveryAction | null> | null

  /**
   * The quality rung actually being played/rendered (ABR may have moved away
   * from the engine's last registered selection). Used by error recovery to
   * step down ONE rung from the real position instead of guessing from a
   * stale or auto-mode (null) selection id.
   */
  getActiveQuality?(): QualityLevel | null
  /** Release the underlying library instance (hls.js / dashjs / shaka). */
  destroy(): void

  /**
   * Optional precise seek through the streaming library. When present, the
   * engine prefers this over writing video.currentTime so DASH/HLS can rebuffer
   * at the target without re-attaching the source (which rewinds to 0).
   */
  /** Resolves after the destination is visually usable when the adapter can verify it. */
  seek?(time: number): void | Promise<StreamSeekResult | void>

  // --- optional codec-family control (DASH adapters only) ---
  getAvailableCodecFamilies?(): string[]
  getSelectedCodecFamily?(): string
  getCurrentCodecFamily?(): string | null
  setCodecFamily?(codecFamily: string): void
}

/**
 * Discriminator for which adapter a source needs. The engine caches the
 * current adapter keyed by this; on loadSource it reuses when unchanged and
 * destroys + rebuilds otherwise. Matches the pre-refactor "adapter instance
 * lives, internal library instance is rebuilt per source" semantics.
 */
export type StreamAdapterType = 'hls' | 'dash' | 'shaka-dash'
