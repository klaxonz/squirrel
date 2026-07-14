<template>
  <div
    class="app-workbench app-two-column"
    :class="{
      'app-two-column--sidebar-always': sidebarAlways,
      'app-two-column--fill': fill,
      'app-two-column--no-main-scroll': !mainScroll,
    }"
    :style="rootStyle"
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
        <div class="app-workbench__header-content">
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
import { computed, ref } from 'vue'

const props = withDefaults(defineProps<{
  /** Sidebar width CSS value (default 17.5rem). */
  sidebarWidth?: string
  /** Always show sidebar (desktop + smaller widths). Default false = lg+ only. */
  sidebarAlways?: boolean
  /** Content max-width inside main scroll (CSS value or null for token default). */
  contentWidth?: string | null
  /** Stretch to parent height (default true for workbench pages). */
  fill?: boolean
  /**
   * When true (default), main content scrolls as one pane.
   * When false, main body is a non-scrolling flex host for multi-pane layouts.
   */
  mainScroll?: boolean
}>(), {
  sidebarWidth: '17.5rem',
  sidebarAlways: false,
  contentWidth: null,
  fill: true,
  mainScroll: true,
})

/** Main pane scroll/body root — used by infinite-scroll observers when mainScroll. */
const scrollEl = ref<HTMLElement | null>(null)
defineExpose({ scrollEl })

const rootStyle = computed(() => {
  const style: Record<string, string> = {
    '--app-workbench-sidebar-width': props.sidebarWidth,
  }
  if (props.contentWidth) {
    style['--app-workbench-content-width'] = props.contentWidth
  }
  return style
})
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
}

.app-two-column--fill {
  height: 100%;
  min-height: 0;
}

/* Default: hide sidebar below lg; --always keeps it visible. */
.app-workbench__sidebar {
  display: none;
}

.app-workbench__sidebar--always {
  display: flex;
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
}
</style>
