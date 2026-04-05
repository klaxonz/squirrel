# Video Play Theater Mode Design

Date: 2026-04-05
Status: Proposed and user-approved for planning
Scope: `squirrel-frontend`

## Context

The current video playback page already exposes a widescreen toggle through the player:

- `VideoPlayer.vue` emits `widescreenChange`.
- `VideoPlay.vue` owns the `isWidescreen` page state.
- `App.vue` already reacts to widescreen state by collapsing the global sidebar shell on desktop.

However, the page layout does not yet behave like YouTube theater mode:

1. Widescreen currently hides the related-video sidebar instead of restructuring the page.
2. The main content column still remains constrained by the normal two-column layout.
3. Related videos do not move into the main content flow below the player.
4. The current `VideoPlay.vue` stylesheet contains repeated layout rules, which makes widescreen behavior fragile and harder to extend.

## Goals

1. Make widescreen behave like YouTube theater mode on desktop layouts.
2. Expand the player area by widening the main content column in widescreen mode.
3. Keep title, channel, and action metadata below the player in both normal and widescreen modes.
4. Move related videos from the right sidebar into the page flow below the main content when widescreen is enabled.
5. Keep the player control behavior unchanged and confine layout responsibility to the page view.

## Non-Goals

1. Redesign `VideoPlayer.vue` controls or fullscreen behavior.
2. Change the event contract between `VideoPlayer.vue` and `VideoPlay.vue`.
3. Rebuild the app shell or sidebar behavior in `App.vue`.
4. Introduce a separate mobile theater-mode layout.
5. Redesign related-video card visuals beyond what is necessary for the new placement.

## Recommendation

Keep the existing page DOM order and switch layouts entirely through page-level structure and CSS:

- `video-main` stays before `video-aside` in the template.
- Normal mode uses a two-column layout.
- Widescreen mode collapses the page container into a single column.
- In that single-column state, `video-aside` naturally renders below the main player and metadata sections.

This approach matches the requested theater-mode behavior while avoiding duplicated related-video markup and keeping responsibility boundaries clean.

## Alternatives Considered

### Alternative A: hide the related sidebar and only widen the player

Pros:

- Lowest implementation effort.
- Minimal template changes.

Cons:

- Does not match the requested YouTube behavior.
- Removes related-video browsing instead of relocating it.

### Alternative B: duplicate the related-video block for sidebar and below-player placements

Pros:

- Simple to reason about in each visual mode.
- Allows fully separate styling for each placement.

Cons:

- Duplicates a large template block.
- Increases maintenance risk and regression surface.
- Makes loading and empty states easy to desynchronize.

### Alternative C: keep one markup block and change the page grid by mode

Pros:

- Closest to the requested theater-mode behavior.
- No duplicated related-video markup.
- Clean separation between player interaction and page layout.

Cons:

- Requires careful cleanup of overlapping CSS rules in `VideoPlay.vue`.

Recommended choice: Alternative C.

## Target Behavior

### Normal mode

- The page uses a desktop two-column layout on large screens.
- `video-main` contains the player and metadata.
- `video-aside` remains on the right side as the related-video rail.
- The related-video rail may remain sticky on desktop.

### Widescreen mode

- The page container switches to a single-column layout.
- The player remains at the top of the page and grows with the wider main-content limit.
- Metadata remains immediately below the player.
- Related videos move below metadata as part of the normal page flow.
- The related-video section is no longer sticky and no longer height-constrained as a sidebar rail.

### Mobile and narrow layouts

- Narrow layouts remain effectively single-column in both states.
- Widescreen should not introduce a second mobile-specific structure.
- The widescreen toggle may still change state, but the visual delta on narrow screens can remain minimal.

## Template Design

The implementation should remain centered in `VideoPlay.vue`.

### Page structure

Keep the existing high-level template order:

1. `.video-page`
2. `.video-page__container`
3. `.video-main`
4. `.video-aside`

Do not introduce duplicate related-video lists for different modes.

### Widescreen state usage

`isWidescreen` remains the single source of truth for page layout mode:

- it still comes from the player toggle event
- it still drives `document.documentElement.classList.toggle('video-widescreen', ...)`
- it still emits the app-level sidebar update through the existing event bus

The key template change is that `video-aside` should no longer be conditionally hidden in widescreen mode. It must stay in the DOM and rely on layout classes for repositioning.

## CSS Layout Design

### Container layout

Refactor `VideoPlay.vue` so `video-page__container` owns the desktop layout modes:

- default large-screen mode: two columns
- widescreen large-screen mode: one column

The widescreen variant should also increase the practical width available to the player area so the player visibly expands instead of merely removing the sidebar.

### Main content sizing

`video-main` should:

- remain full-width in normal mode within the left column
- expand to the full single-column width in widescreen mode
- preserve the current vertical order of player then metadata

### Aside behavior

`video-aside` should have two presentation modes:

- normal mode: sidebar rail, optional sticky positioning
- widescreen mode: standard block flow below the main content

The widescreen mode must remove rail-specific constraints such as sticky top offsets or sidebar-only max-height assumptions.

### Related-video cards

Card styling should stay visually consistent, but the widescreen-below-player presentation should avoid over-compressed sidebar sizing:

- allow a wider card ratio when rendered below the player
- preserve loading, empty, and transition states
- avoid introducing a second card component

### Style cleanup

`VideoPlay.vue` currently contains repeated definitions for layout-related selectors such as:

- `.video-section`
- `.video-container`
- `.viewfinder-box`
- `.video-meta`
- `.related-video-card`

Implementation should consolidate these rules so one final definition controls each layout primitive. This cleanup is in scope because the theater-mode change depends on predictable cascade behavior.

## Component Boundary

### `VideoPlayer.vue`

No behavior changes are required in the player component.

It should continue to:

- render the widescreen button
- receive the `widescreen` prop
- emit `widescreenChange`

The player should not become responsible for page reflow, related-video placement, or shell layout.

### `VideoPlay.vue`

This view remains responsible for:

- owning `isWidescreen`
- applying mode classes
- coordinating page layout
- deciding where related videos appear through CSS layout

### `App.vue`

No structural changes are required beyond preserving the current widescreen shell reaction:

- app-level sidebar collapse behavior remains as-is
- no additional theater-mode logic should be added here for this change

## Error and Edge Behavior

1. If related videos are loading, skeletons must appear in the correct location for the active layout mode.
2. If there are no related videos, the empty state must remain visible in both normal and widescreen layouts.
3. If the user toggles widescreen repeatedly, the page should not remove and recreate the related-video subtree unnecessarily.
4. If the viewport crosses responsive breakpoints while widescreen is enabled, layout should remain coherent and not leave the aside hidden or sticky in the wrong mode.

## Verification Plan

### Test additions

Add a focused frontend regression test that verifies:

1. `VideoPlay.vue` keeps the related-video aside in the template without widescreen-only `hidden` removal logic.
2. The page container has a dedicated widescreen layout class path.
3. The stylesheet includes a widescreen single-column rule for the page container.
4. The stylesheet includes a widescreen rule that disables sidebar-style sticky behavior for the related-video section.

These tests can be source-based if that is the lightest existing frontend test pattern for this area.

### Manual verification

1. Open a video page on desktop width.
2. Confirm normal mode shows player and metadata on the left with related videos on the right.
3. Click the player widescreen toggle.
4. Confirm the player area expands horizontally.
5. Confirm metadata stays below the player.
6. Confirm related videos move below the metadata instead of disappearing.
7. Exit widescreen and confirm the page returns to the two-column layout.

### Build verification

Run at minimum:

1. the targeted frontend regression test for theater mode
2. `npm run typecheck`

If the page style cleanup touches broader template structure, also run:

3. `npm run build:check`

## Risks

1. Repeated CSS selectors in `VideoPlay.vue` can cause the intended theater-mode rules to be overridden unexpectedly.
2. Sidebar-specific related-video styles may look cramped when moved below the player unless widened deliberately.
3. Widescreen shell behavior from `App.vue` can visually conflict with page-level layout if the container widths are not recalibrated together.
4. Over-coupling the layout change to desktop breakpoints can accidentally create odd intermediate tablet behavior.

## Mitigations

1. Consolidate duplicate layout selectors before finalizing theater-mode rules.
2. Keep one related-video markup path and solve placement through layout classes only.
3. Limit implementation scope to `VideoPlay.vue` unless verification proves an app-shell adjustment is necessary.
4. Verify both normal mode and widescreen mode at desktop and narrow widths before closing the task.

## Implementation Notes For Planning

Implementation should be sequenced in this order:

1. add a failing regression test for theater-mode layout markers
2. refactor `VideoPlay.vue` template to keep the aside mounted in widescreen
3. consolidate duplicated layout CSS in `VideoPlay.vue`
4. implement normal-mode and widescreen-mode grid rules
5. verify targeted test, typecheck, and build checks as needed
