# Video Play Decard Design

**Goal:** Remove the card-like shells from the video play page so the player, metadata, and related list feel like one continuous editorial layout.

**Scope**
- Modify [VideoPlay.vue](D:/Code/init/squirrel/squirrel-frontend/src/views/VideoPlay.vue)
- No routing, store, or player logic changes

**Design**
- Remove border, radius, shadow, and gradient shell styles from the main player section.
- Remove border, radius, shadow, and gradient shell styles from the metadata section and rely on spacing plus a light divider.
- Remove border, radius, shadow, and gradient shell styles from the related videos side section.
- Reduce the card feel of each related item so the page does not look de-carded outside but still card-heavy inside.

**Success Criteria**
- The video play page no longer presents the player area, metadata area, or aside column as separate floating cards.
- Content grouping remains clear through spacing and subtle separators.
- Mobile layout remains intact.
