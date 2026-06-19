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
 * PR1 (this file) introduces the seam with StreamContext still carrying the
 * reverse-driving surface (emit / registerQualities / setQuality / reportError)
 * that adapters used to call on PluginContext. PR2 will replace that surface
 * with the four-method StreamSink and narrow StreamContext to { videoElement,
 * logger, options }. The widening-then-narrowing is deliberate: PR1 is a pure
 * structural refactor (zero behavior change), PR2 is the control-flow change.
 */

import type { PlayerLogger } from './logger'
import type {
  MediaSource,
  PlayerError,
  PlayerEvents,
  PlayerState,
  PlaybackRecoveryAction,
  PlaybackRecoveryContext,
  QualityLevel,
  QualitySelectionRequest,
} from './types'

/**
 * The slice of the engine's event emitter surface that adapters use. Same
 * shape as EventEmitter<PlayerEvents>['emit'] minus the `this` return (adapters
 * forward to the emitter and don't chain on the result).
 */
export type StreamEmit = <K extends keyof PlayerEvents>(
  event: K,
  data?: PlayerEvents[K]
) => void

/**
 * Engine → adapter input. In PR1 this carries the reverse-driving methods
 * adapters used to reach on PluginContext (forwarded by the engine to its
 * closure), so behavior is byte-identical to the old plugin path. PR2 deletes
 * emit / registerQualities / registerCurrentQualityId / setQuality /
 * getCurrentQualityLabel / reportError and replaces them with a StreamSink
 * passed to onSourceChange.
 */
export interface StreamContext {
  /** Lazy read of the engine's <video> element (may be null until attached). */
  readonly videoElement: () => HTMLVideoElement | null
  /** Engine playback state snapshot (adapters read .quality / .playing). */
  readonly getState: () => PlayerState
  readonly logger: PlayerLogger

  // --- PR1 reverse-driving surface (deleted in PR2, replaced by StreamSink) ---
  /** Forwarded to the engine's event emitter (with its waiting/canplay intercept). */
  readonly emit: StreamEmit
  /** Engine records the available qualities + feeds them to error-recovery. */
  readonly registerQualities: (qualities: QualityLevel[]) => void
  /** Engine records the adapter's currently-active quality id. */
  readonly registerCurrentQualityId: (id?: string | number) => void
  /** Engine-level quality setter — adapters call this to set a default (round-trip, removed in PR2). */
  readonly setQuality: (quality: QualitySelectionRequest) => void
  /** Engine error sink. */
  readonly reportError: (error: PlayerError) => void
}

/**
 * Engine → adapter control. The four optional codec-family methods are present
 * only on the DASH adapters; the runtime probes with `adapter.getAvailableCodecFamilies?.()`
 * rather than branching on source type.
 */
export interface StreamAdapter {
  /** Load a source. In PR1 the sink parameter is not yet present (PR2 adds it). */
  onSourceChange(source: MediaSource): void
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
