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
  /** Release the underlying library instance (hls.js / dashjs / shaka). */
  destroy(): void

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
