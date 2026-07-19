<template>
  <div
    class="app-workbench app-two-column"
    :class="{
      [`app-two-column--preset-${preset}`]: true,
      'app-two-column--sidebar-always': sidebarAlways,
      'app-two-column--sidebar-collapsed': sidebarCollapsed,
      'app-two-column--fill': fill,
      'app-two-column--no-main-scroll': !mainScroll,
    }"
  >
    <aside
      v-if="$slots.sidebar"
      class="app-workbench__sidebar"
      :class="{ 'app-workbench__sidebar--always': sidebarAlways }"
    >
      <slot name="sidebar" />
    </aside>

    <main class="app-workbench__main">
      <header v-if="$slots.header" class="app-workbench__header">
        <div
          class="app-workbench__header-content"
          :class="{ 'app-content-aligned-divider': preset === 'music' }"
        >
          <slot name="header" />
        </div>
      </header>

      <!--
        mainScroll=true (default): single scroll region for feed / settings content.
        mainScroll=false: body fills remaining height so multi-pane children
        (RSS entry list + reader) own their own scroll roots.
      -->
      <div
        v-if="mainScroll"
        ref="scrollEl"
        class="app-workbench__scroll custom-scrollbar"
        data-route-scroll="workbench-main"
      >
        <slot />
      </div>
      <div
        v-else
        ref="scrollEl"
        class="app-workbench__body"
      >
        <slot />
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

withDefaults(defineProps<{
  /** Named desktop layout; prevents page-local width drift. */
  preset?: 'settings' | 'playlist' | 'music' | 'rss'
  /** Always show sidebar (desktop + smaller widths). Default false = lg+ only. */
  sidebarAlways?: boolean
  /** Collapse the secondary workbench sidebar while preserving the main pane. */
  sidebarCollapsed?: boolean
  /** Stretch to parent height (default true for workbench pages). */
  fill?: boolean
  /**
   * When true (default), main content scrolls as one pane.
   * When false, main body is a non-scrolling flex host for multi-pane layouts.
   */
  mainScroll?: boolean
}>(), {
  preset: 'playlist',
  sidebarAlways: false,
  sidebarCollapsed: false,
  fill: true,
  mainScroll: true,
})

/** Main pane scroll/body root — used by infinite-scroll observers when mainScroll. */
const scrollEl = ref<HTMLElement | null>(null)
defineExpose({ scrollEl })

</script>

<style scoped>
/*
  Single workbench shell. All two-column product pages (settings, tasks,
  site runtimes, playlists, music, rss, etc.) share this component so chrome,
  borders, and scroll regions stay identical. Visual tokens live on
  .app-workbench* in layout.css — this file only owns component-level flags.
*/
.app-two-column {
  width: 100%;
  container-name: workbench;
  container-type: inline-size;
}

.app-two-column--fill {
  height: 100%;
  min-height: 0;
}

.app-two-column--preset-settings {
  --app-workbench-sidebar-width: 12rem;
  --app-workbench-content-width: var(--app-content-form-max);
}

.app-two-column--preset-playlist {
  --app-workbench-sidebar-width: 17.5rem;
  --app-workbench-content-width: none;
}

.app-two-column--preset-music {
  --app-workbench-sidebar-width: 12rem;
  --app-workbench-content-width: var(--app-content-media-max);
  --app-workbench-content-gutter: var(--app-content-media-gutter);
  --app-divider-inline-gutter: var(--app-workbench-content-gutter);
}

.app-two-column--preset-music .app-workbench__header {
  border-bottom: 0;
}

.app-two-column--preset-rss {
  --app-workbench-sidebar-width: clamp(13rem, 18cqi, 15.5rem);
  --app-workbench-content-width: none;
  --app-workbench-sidebar-bg: transparent;
}

/* Default: hide sidebar below lg; --always keeps it visible. */
.app-workbench__sidebar {
  display: none;
}

.app-workbench__sidebar--always {
  display: flex;
}

.app-two-column--sidebar-collapsed .app-workbench__sidebar {
  display: none;
}

.app-workbench__body {
  display: flex;
  min-height: 0;
  min-width: 0;
  flex: 1 1 auto;
  overflow: hidden;
}

@media (min-width: 1024px) {
  .app-workbench__sidebar {
    display: flex;
  }

  .app-two-column--sidebar-collapsed .app-workbench__sidebar {
    display: none;
  }
}
</style>
