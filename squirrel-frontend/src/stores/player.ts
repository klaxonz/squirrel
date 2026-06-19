import { defineStore } from 'pinia'
import { shallowRef } from 'vue'
import type { IPlayerAdapter } from '@/components/video-player/core'
import type { PlayerHandlers, VideoPlayerHandle } from '@/types/playerSession'

// ponytail: this store used to also own a 22-field `session` reactive bag
// (source / videoSnapshot / title / handlers / active / target / ...). That
// bag was the "facts layer" of "what's playing now"; per ADR-0002 it moved to
// PlaybackSession (`composables/usePlaybackSession.ts`), which is the single
// owner. What remains here are assembly handles GlobalVideoPlayerHost needs to
// mount the VideoPlayer — they are wiring state, not playback state.
//
//   playerRef — VideoPlayer component instance (structural handle, avoids a
//               circular import on VideoPlayer.vue)
//   target    — Teleport anchor element
//   adapter   — IPlayerAdapter the shell injects (LocalStorageAdapter from
//               VideoPlay); falls back to BackendPlayerAdapter in the host.
//               ponytail: moves into the host / orchestrator in PR2.
//   handlers  — callbacks the shell wires through VideoPlayer emits.
//               ponytail: deleted in PR2 once the data-flow inversion makes
//               the orchestrator the direct emit target.

export const usePlayerStore = defineStore('player', () => {
  const playerRef = shallowRef<VideoPlayerHandle | null>(null)
  const target = shallowRef<HTMLElement | null>(null)
  const adapter = shallowRef<IPlayerAdapter | null>(null)
  const handlers = shallowRef<PlayerHandlers>({} as PlayerHandlers)

  return {
    playerRef,
    target,
    adapter,
    handlers,
  }
})

