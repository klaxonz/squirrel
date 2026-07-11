<template>
  <aside
    class="sidebar-rail"
    :class="{ 'has-player': showSidebarMusicPlayer }"
    aria-label="应用侧边栏"
  >
    <nav class="sidebar-top-nav" aria-label="主要入口">
      <SidebarMenuItem
        v-for="item in SIDEBAR_TOP_ITEMS"
        :key="item.path"
        :item="item"
        :is-active="isNavigationItemActive(item, $route)"
      />
    </nav>

    <nav
      :id="NAV_ID"
      class="sidebar-nav custom-scrollbar"
      aria-label="主导航"
    >
      <section
        v-for="group in primaryNavGroups"
        :key="group.key"
        class="sidebar-group"
        :aria-labelledby="`sidebar-group-${group.key}`"
      >
        <h2
          :id="`sidebar-group-${group.key}`"
          class="sidebar-group__label"
        >
          {{ group.label }}
        </h2>
        <div class="sidebar-group__items">
          <SidebarMenuItem
            v-for="item in group.items"
            :key="item.path"
            :item="item"
            :is-active="isNavigationItemActive(item, $route)"
          />
        </div>
      </section>
    </nav>

    <footer class="sidebar-footer">
      <SidebarMenuItem
        v-for="item in SIDEBAR_FOOTER_ITEMS"
        :key="item.path"
        :item="item"
        :is-active="isNavigationItemActive(item, $route)"
      />
    </footer>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import SidebarMenuItem from './SidebarMenuItem.vue'
import {
  NAV_GROUPS,
  SIDEBAR_FOOTER_ITEMS,
  SIDEBAR_TOP_ITEMS,
  isNavigationItemActive,
} from '@/shared/constants/sidebar'
import { useMusicPlayerStore } from '@/features/music/stores/musicPlayer'

const NAV_ID = 'app-sidebar-nav'

const route = useRoute()
const musicPlayerStore = useMusicPlayerStore()

const primaryNavGroups = NAV_GROUPS

const showSidebarMusicPlayer = computed(() =>
  route.name !== 'Music' && Boolean(
    musicPlayerStore.currentTrack
    && (musicPlayerStore.resolvingUrl || musicPlayerStore.audioSrc || musicPlayerStore.error),
  ),
)
</script>

<style scoped>
/* Main app rail — quiet lift of canvas, single-canvas shell (DESIGN elevation). */
.sidebar-rail {
  --sidebar-player-space: 6.25rem;
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  overflow: hidden;
  border: 0;
  border-right: 1px solid hsl(var(--border) / 0.38);
  border-radius: 0;
  background: hsl(var(--sidebar) / 0.72);
  color: hsl(var(--sidebar-foreground));
  box-shadow: none;
  user-select: none;
  transition: padding-bottom var(--duration-base) var(--ease-out);
}

.sidebar-rail.has-player {
  padding-bottom: var(--sidebar-player-space);
}

.sidebar-top-nav {
  display: flex;
  flex: 0 0 auto;
  flex-direction: column;
  gap: var(--sidebar-item-gap);
  padding: var(--space-2) var(--space-2) 0.625rem;
  border-bottom: 0;
}

.sidebar-nav {
  flex: 1 1 auto;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
  padding: var(--space-2);
}

.sidebar-group + .sidebar-group {
  margin-top: 1.125rem;
}

/* Quiet section label — text only, no chrome icons (DESIGN: quiet chrome). */
.sidebar-group__label {
  margin: 0 0 0.375rem;
  padding: 0 0.625rem;
  color: hsl(var(--muted-foreground) / 0.58);
  font-size: 0.625rem;
  font-weight: 600;
  line-height: 1.25;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.sidebar-group__items {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.sidebar-footer {
  display: flex;
  flex: 0 0 auto;
  flex-direction: column;
  gap: 1px;
  padding: 0.375rem var(--space-2) var(--space-2);
  border-top: 1px solid hsl(var(--border) / 0.28);
}

@media (prefers-reduced-motion: reduce) {
  .sidebar-rail {
    transition: none;
  }
}
</style>
