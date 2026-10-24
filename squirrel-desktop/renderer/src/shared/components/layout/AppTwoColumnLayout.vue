<template>
  <div
    class="app-workbench app-two-column"
    :class="[
      `app-two-column--preset-${preset}`,
      responsiveMode && `app-two-column--mode-${responsiveMode}`,
      {
        'app-two-column--legacy': !responsiveMode,
        'app-two-column--sidebar-always': sidebarAlways,
        'app-two-column--sidebar-open': isSidebarOpen,
        'app-two-column--sidebar-collapsed': !isSidebarOpen,
        'app-two-column--fill': fill,
        'app-two-column--no-main-scroll': !mainScroll,
      },
    ]"
  >
    <button
      v-if="responsiveMode === 'drawer' && isSidebarOpen"
      type="button"
      class="app-two-column__scrim"
      aria-label="关闭侧栏"
      :aria-controls="sidebarId"
      @click="closeSidebar"
    />

    <aside
      v-if="$slots.sidebar"
      :id="sidebarId"
      ref="sidebarEl"
      class="app-workbench__sidebar"
      :class="{ 'app-workbench__sidebar--always': sidebarAlways }"
      :aria-label="sidebarLabel"
    >
      <slot name="sidebar" :open="isSidebarOpen" :close="closeSidebar" :toggle="toggleSidebar" />
    </aside>

    <main class="app-workbench__main">
      <header v-if="$slots.header || showSidebarToggle" class="app-workbench__header">
        <div
          class="app-workbench__header-content"
          :class="{ 'app-content-aligned-divider': preset === 'music' }"
        >
          <template v-if="showSidebarToggle">
            <slot
              name="sidebar-toggle"
              :open="isSidebarOpen"
              :label="toggleLabel"
              :toggle="toggleSidebar"
            >
              <button
                type="button"
                class="app-two-column__sidebar-toggle"
                :aria-label="toggleLabel"
                :title="toggleLabel"
                :aria-expanded="isSidebarOpen"
                :aria-controls="sidebarId"
                @click="toggleSidebar"
              >
                <AppIcon :name="isSidebarOpen ? 'panelClose' : 'panelOpen'" />
              </button>
            </slot>
            <div v-if="$slots.header" class="app-two-column__header-slot">
              <slot name="header" />
            </div>
          </template>
          <slot v-else name="header" />
        </div>
      </header>

      <div
        ref="scrollEl"
        class="app-two-column__main-root"
        :class="mainScroll ? 'app-workbench__scroll custom-scrollbar' : 'app-workbench__body'"
        :data-route-scroll="mainScroll ? scrollKey : undefined"
      >
        <slot />
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'

export type AppTwoColumnResponsiveMode = 'fixed' | 'collapsible' | 'drawer' | 'stack'

const props = withDefaults(defineProps<{
  /** Named desktop layout; prevents page-local width drift. */
  preset?: 'settings' | 'playlist' | 'music' | 'rss'
  /** Explicit mode. Omit to preserve legacy breakpoint and sidebar props. */
  responsiveMode?: AppTwoColumnResponsiveMode
  /** Controlled sidebar state for collapsible and drawer modes. */
  sidebarOpen?: boolean
  /** Initial uncontrolled state for collapsible and drawer modes. */
  defaultSidebarOpen?: boolean
  /** Render the built-in toggle header for collapsible and drawer modes. */
  sidebarToggle?: boolean
  /** Always show sidebar in legacy mode. */
  sidebarAlways?: boolean
  /** Legacy inverse sidebar state. Prefer sidebarOpen with an explicit mode. */
  sidebarCollapsed?: boolean
  sidebarLabel?: string
  sidebarToggleLabel?: string
  /** Stable route-scroll key for navigation restoration. */
  scrollKey?: string
  /** Stretch to parent height (default true for workbench pages). */
  fill?: boolean
  /** When false, the stable main root is a non-scrolling flex host. */
  mainScroll?: boolean
}>(), {
  preset: 'playlist',
  responsiveMode: undefined,
  sidebarOpen: undefined,
  defaultSidebarOpen: true,
  sidebarToggle: true,
  sidebarAlways: false,
  sidebarCollapsed: false,
  sidebarLabel: '侧栏',
  sidebarToggleLabel: '',
  scrollKey: 'workbench-main',
  fill: true,
  mainScroll: true,
})

const emit = defineEmits<{
  'update:sidebarOpen': [open: boolean]
  'sidebar-toggle': [open: boolean]
}>()

const sidebarId = `app-workbench-sidebar-${Math.random().toString(36).slice(2, 9)}`
const internalSidebarOpen = ref(props.defaultSidebarOpen)
const isSidebarOpen = computed(() => {
  if (!props.responsiveMode) return !props.sidebarCollapsed
  if (props.responsiveMode === 'fixed' || props.responsiveMode === 'stack') return true
  return props.sidebarOpen ?? internalSidebarOpen.value
})
const canToggleSidebar = computed(() => (
  Boolean(props.responsiveMode)
  && (props.responsiveMode === 'collapsible' || props.responsiveMode === 'drawer')
))
const showSidebarToggle = computed(() => props.sidebarToggle && canToggleSidebar.value)
const toggleLabel = computed(() => props.sidebarToggleLabel || (isSidebarOpen.value ? '收起侧栏' : '展开侧栏'))

watch(() => props.defaultSidebarOpen, (open) => {
  if (props.sidebarOpen === undefined) internalSidebarOpen.value = open
})

function setSidebarOpen(open: boolean) {
  if (!canToggleSidebar.value) return
  if (props.sidebarOpen === undefined) internalSidebarOpen.value = open
  emit('update:sidebarOpen', open)
  emit('sidebar-toggle', open)
}

function toggleSidebar() {
  setSidebarOpen(!isSidebarOpen.value)
}

function openSidebar() {
  setSidebarOpen(true)
}

function closeSidebar() {
  setSidebarOpen(false)
}

const scrollEl = ref<HTMLElement | null>(null)
const sidebarEl = ref<HTMLElement | null>(null)
defineExpose({ scrollEl, sidebarEl, isSidebarOpen, toggleSidebar, openSidebar, closeSidebar })
</script>

<style scoped>
.app-two-column {
  position: relative;
  isolation: isolate;
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
  --app-workbench-content-width: var(--app-page-max-width);
  --app-workbench-content-gutter: var(--app-page-gutter);
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

.app-workbench__sidebar {
  display: none;
}

.app-two-column--legacy .app-workbench__sidebar--always,
.app-two-column--mode-fixed .app-workbench__sidebar,
.app-two-column--mode-stack .app-workbench__sidebar,
.app-two-column--mode-collapsible.app-two-column--sidebar-open .app-workbench__sidebar {
  display: flex;
}

.app-workbench__body,
.app-two-column__main-root {
  min-height: 0;
  min-width: 0;
}

.app-workbench__body {
  display: flex;
  flex: 1 1 auto;
  overflow: hidden;
}

.app-two-column__header-slot {
  display: flex;
  width: 100%;
  min-width: 0;
  flex: 1 1 auto;
  align-self: stretch;
}

.app-two-column__sidebar-toggle {
  display: inline-flex;
  width: 2rem;
  height: 2rem;
  flex: 0 0 2rem;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: var(--radius-sm);
  color: hsl(var(--muted-foreground));
  background: transparent;
  cursor: pointer;
}

.app-two-column__sidebar-toggle:hover {
  color: hsl(var(--foreground));
  background: hsl(var(--secondary));
}

.app-two-column__sidebar-toggle:focus-visible {
  outline: 2px solid hsl(var(--ring));
  outline-offset: 2px;
}

.app-two-column__sidebar-toggle :deep(svg) {
  width: 1rem;
  height: 1rem;
}

.app-two-column__scrim {
  display: none;
}

@media (min-width: 1024px) {
  .app-two-column--legacy .app-workbench__sidebar {
    display: flex;
  }

  .app-two-column--legacy.app-two-column--sidebar-collapsed .app-workbench__sidebar {
    display: none;
  }
}

@container workbench (min-width: 48rem) {
  .app-two-column--mode-drawer .app-workbench__sidebar {
    display: flex;
  }

  .app-two-column--mode-drawer .app-two-column__sidebar-toggle,
  .app-two-column--mode-drawer .app-two-column__scrim {
    display: none;
  }
}

@container workbench (max-width: 47.999rem) {
  .app-two-column--mode-drawer.app-two-column--sidebar-open .app-workbench__sidebar {
    position: absolute;
    inset: 0 auto 0 0;
    z-index: calc(var(--z-sidebar) + 1);
    display: flex;
    max-width: min(86cqi, var(--app-workbench-sidebar-width));
    box-shadow: var(--shadow-lg);
    /* The drawer is the workbench sidebar — same card surface as the workbench. */
    background: hsl(var(--card));
  }

  .app-two-column--mode-drawer.app-two-column--sidebar-open .app-two-column__scrim {
    position: absolute;
    inset: 0;
    z-index: var(--z-sidebar);
    display: block;
    width: 100%;
    border: 0;
    background: hsl(var(--foreground) / 0.28);
    cursor: default;
  }

  .app-two-column--mode-stack {
    height: auto;
    min-height: 100%;
    flex-direction: column;
    overflow-y: auto;
  }

  .app-two-column--mode-stack .app-workbench__sidebar {
    width: 100%;
    max-height: min(40vh, 20rem);
    border-right: 0;
    border-bottom: 1px solid hsl(var(--border));
  }

  .app-two-column--mode-stack .app-workbench__main {
    flex: 0 0 auto;
    overflow: visible;
  }

  .app-two-column--mode-stack .app-workbench__scroll {
    overflow: visible;
  }
}

@media (prefers-reduced-motion: reduce) {
  .app-workbench__sidebar,
  .app-two-column__scrim {
    transition: none;
  }
}
</style>
