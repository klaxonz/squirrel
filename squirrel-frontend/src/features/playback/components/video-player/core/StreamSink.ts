/**
 * Stream sink — the only channel by which a StreamAdapter drives the engine.
 *
 * See docs/adr/0001-stream-adapter-and-sink.md. PR2 of the epic: this replaces
 * the PR1 reverse-driving surface (emit / registerQualities /
 * registerCurrentQualityId / setQuality / reportError on StreamContext) with
 * four explicit callbacks. The engine owns quality strategy on top of the
 * facts the sink delivers; the adapter owns implementation detail (e.g. DASH
 * codec-family default selection) and reports the result via qualitiesResolved.
 */

import type { PlayerError, QualityLevel } from './types'

export interface StreamQualityChange {
  id: string | number
  label: string
  auto: boolean
}

export interface StreamSink {
  /**
   * One-shot, after a source loads and the adapter has resolved its quality
   * list. `currentId` is the adapter's currently-active quality (already
   * reflecting any internal default it chose, e.g. a DASH codec-family pick),
   * or null if it has not selected one. The engine applies user strategy
   * (preference / auto-quality) on top and may call adapter.setQuality to
   * override — there is no round-trip back into the engine.
   */
  qualitiesResolved(qualities: QualityLevel[], currentId: string | number | null): void

  /**
   * Recurring, on ABR auto-switch or after the engine calls setQuality and the
   * adapter confirms. Keeps the engine's current-quality state in sync.
   */
  qualityChanged(quality: StreamQualityChange): void

  /**
   * Replaces emit('waiting') / emit('canplay'). The adapter reports its
   * buffering state so the engine can drive the loading-state machine and
   * autoPlayOnReady. HLS does not call this (it relies on the native <video>
   * element's waiting/canplay events, which the engine listens to directly);
   * Dash/Shaka call it because they manage their own buffering.
   */
  loadingStateChanged(isLoading: boolean): void

  /** Fatal (or transient, per the error's `fatal` flag) playback error. */
  error(error: PlayerError): void
}
