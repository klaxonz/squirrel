# Video Play Actions Inline Design

**Goal:** Replace the overflow action menu on the video play page with a fully inline action row and reduce the visual size of all action buttons.

**Scope**
- Modify [VideoPlay.vue](D:/Code/init/squirrel/squirrel-frontend/src/views/VideoPlay.vue)
- No playback logic, routing, or store changes

**Design**
- Remove the `更多` trigger and stop using a separate overflow menu in the video action area.
- Render all available actions in one inline row.
- Reduce action button height, horizontal padding, icon size, and label size by one visual step.
- Keep the same action labels and interaction semantics so discoverability stays high.

**Success Criteria**
- The play page shows all video actions directly without a `更多` menu.
- The action row reads lighter and more compact than before.
- The action row still wraps safely on smaller widths.
