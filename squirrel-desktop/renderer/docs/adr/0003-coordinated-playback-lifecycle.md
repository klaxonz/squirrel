# ADR 0003: One coordinated playback lifecycle

Status: accepted

## Decision

`PlaybackCoordinator` is the single lifecycle authority from provider resolution
through media playback. Its phases are resolving, loading, ready, playing,
paused, seeking, buffering, recovering, ended, and error.

Each new video creates a generation. Resolve, load, seek, and recovery create
monotonic operation IDs with abort signals. Starting a newer source or operation
invalidates older asynchronous completions. Resolver results and stream-adapter
callbacks must prove that their generation is still active before publishing.

## Invariants

- Playback intent (`play` or `pause`) is independent of `HTMLMediaElement.paused`.
  Internal detach/reload pauses never overwrite user intent.
- Vue does not own a second loading or error state. It projects the coordinator
  snapshot into render-only store fields.
- A load completes on ready, playing, paused, or error. A seek completes only
  when its operation reaches a stable phase.
- Shaka seek readiness additionally requires a presented destination video
  frame. Audio time advancing is not considered visual completion.
- A source becomes available to the player as soon as provider resolution
  finishes; detail, subtitle, and related-video fetches cannot delay first frame.
- A short-lived, identity-scoped YouTube DASH cache may start immediately and is
  refreshed in the background. Forced refresh always waits for provider output.

## Error policy

Provider/library codes are retained for diagnostics, then normalized by
`classifyPlaybackError` for retry, quality fallback, and localized UI policy.
Recovery is a lifecycle operation rather than a separate spinner/error channel.
