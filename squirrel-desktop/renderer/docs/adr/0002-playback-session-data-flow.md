# ADR 0002: Playback session owns playback facts

Status: accepted

`PlaybackSession` is the application-scoped owner of facts describing what is
playing: video identity, resolved source, metadata, subtitles, playlist, and
presentation options. Pinia stores only host wiring and UI-specific runtime
projection. Pages consume readonly session facts and mutate them through session
verbs; they do not reconcile duplicate local copies.

Media lifecycle is deliberately not stored in the facts object. Resolver,
engine, and UI share `PlaybackCoordinator`, whose snapshot is projected into the
player runtime store for rendering.
