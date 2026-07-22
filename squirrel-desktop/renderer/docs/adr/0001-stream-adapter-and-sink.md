# ADR 0001: Stream adapters communicate through a sink

Status: accepted

The player engine owns the active HLS, dash.js, or Shaka adapter. Adapters read
only `StreamContext` and publish qualities, buffering, and failures only through
`StreamSink`. They are not player plugins and they must not mutate Vue state.

Every source load receives a generation-scoped sink. Callbacks from an adapter
belonging to an older source are ignored after a new playback generation starts.
This is required because player-library teardown is asynchronous.

The engine owns playback intent, lifecycle transitions, quality presentation,
recovery policy, and the public operation contract. An adapter may return an
asynchronous seek result when it can verify stronger completion semantics. The
Shaka adapter resolves seek only after it observes a video frame from the target
position, including its decoder/manifest repair sequence.
