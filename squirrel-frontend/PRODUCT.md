# Product

## Register

product

## Users

Squirrel is for self-hosting users who collect, subscribe to, download, browse, and play long-form video and music from multiple sites. The primary surface is a desktop-first web/Electron app used in focused management sessions: reviewing new subscription items, searching local and remote media, checking runtime health, adjusting download/playback settings, and opening playback without losing task context.

Users need a reliable media operations desk, not a marketing experience. They are often managing many channels, videos, jobs, logs, and playback states at once, so the interface must support scanning, filtering, triage, and quick recovery from failures.

## Product Purpose

Squirrel centralizes personal media subscription workflows: add sources, fetch and organize videos, generate media-library metadata, browse downloaded content, play media, manage music playback, inspect site runtimes, and keep scheduled tasks healthy.

Success means users can tell what is new, what needs attention, what is playing, what is downloading, and what is broken without hunting through unrelated pages or browser history. The UI should feel like a mature desktop control surface that remains predictable under large libraries and imperfect network/runtime states.

## Brand Personality

Quiet, cinematic, competent.

The product should feel like a private media archive with operational controls: restrained amber identity, dark-first viewing comfort, dense but readable lists, and minimal ceremony. It should feel calm during routine browsing and precise during diagnostics.

## Anti-references

- Do not make the app feel like a landing page, streaming-service billboard, or SaaS dashboard template.
- Do not use decorative gradients, glass panels, or visual effects that compete with media thumbnails and task controls.
- Do not hide operational state behind vague copy, generic empty states, or browser-like navigation behavior.
- Do not optimize for mobile-first layouts unless explicitly requested; this product is desktop-first.
- Do not add fallback UI patterns that mask missing data, runtime failures, or broken authentication.

## Design Principles

- Respect the desktop shell. Navigation, shortcuts, side buttons, and visible hierarchy must follow app-level boundaries instead of browser history assumptions.
- Keep media first. Thumbnails, titles, channel identity, playback state, and subscription status should dominate content screens; chrome stays quiet.
- Expose operational truth. Downloads, site runtimes, scheduled tasks, logs, auth state, and server configuration should show concrete state and next action.
- Preserve context. Search, filters, playback, sidebar state, and scroll position should let users move between tasks without disorientation.
- Use one visual language. Buttons, fields, tabs, badges, cards, dialogs, skeletons, and navigation states must share the same token system and interaction vocabulary.
- Treat current UI as evidence, not authority. Existing screens reveal product structure and technical constraints, but flawed visual hierarchy, cramped density, decorative effects, or inconsistent components must be redesigned from the root instead of preserved.

## Accessibility & Inclusion

Target WCAG 2.1 AA for contrast, keyboard focus, and control semantics. Keyboard navigation must remain visible across custom Vue components, sidebar entries, menus, tabs, dialogs, and playback controls. Motion should be short and state-driven, with reduced-motion alternatives for page transitions and animated placeholders. Color cannot be the only status indicator for runtime health, destructive actions, downloads, or playback state.
