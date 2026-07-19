<template>
  <aside
    class="sidebar-rail"
    :class="{ 'has-player': showSidebarMusicPlayer, 'is-collapsed': collapsed }"
    aria-label="应用侧边栏"
  >
    <nav class="sidebar-top-nav" aria-label="主要入口">
      <SidebarMenuItem
        v-for="item in SIDEBAR_TOP_ITEMS"
        :key="item.path"
        :item="item"
        :is-active="isNavigationItemActive(item, $route)"
        :collapsed="collapsed"
      />
    </nav>

    <nav :id="NAV_ID" class="sidebar-nav custom-scrollbar" aria-label="主导航">
      <section
        v-for="group in primaryNavGroups"
        :key="group.key"
        class="sidebar-group"
        :aria-labelledby="`sidebar-group-${group.key}`"
      >
        <h2 :id="`sidebar-group-${group.key}`" class="sidebar-group__label">
          {{ group.label }}
        </h2>
        <div class="sidebar-group__items">
          <SidebarMenuItem
            v-for="item in group.items"
            :key="item.path"
            :item="item"
            :is-active="isNavigationItemActive(item, $route)"
            :collapsed="collapsed"
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
        :collapsed="collapsed"
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

defineProps<{ collapsed?: boolean }>()

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
.sidebar-rail {
  display: flex;
  width: 100%;
  height: 100%;
  flex-direction: column;
  overflow: hidden;
  border-right: 1px solid var(--app-hairline);
  background: hsl(var(--background));
  color: hsl(var(--foreground));
  user-select: none;
}

.sidebar-top-nav,
.sidebar-footer {
  display: flex;
  flex: 0 0 auto;
  flex-direction: column;
  gap: var(--sidebar-item-gap);
  padding: 0.75rem;
}

.sidebar-top-nav {
  border-bottom: 1px solid var(--app-hairline);
}

.sidebar-footer {
  border-top: 1px solid var(--app-hairline);
}

.sidebar-nav {
  min-height: 0;
  flex: 1 1 auto;
  overflow-x: hidden;
  overflow-y: auto;
  padding: 0.875rem 0.75rem;
  transition: padding-bottom var(--duration-base) var(--ease-out);
}

/* The fixed mini player occupies the bottom of the scrollable rail, directly
   above Settings. Reserve that space in nav instead of moving the footer. */
.sidebar-rail.has-player .sidebar-nav {
  padding-bottom: calc(0.875rem + var(--sidebar-player-height));
}

.sidebar-group + .sidebar-group {
  margin-top: 1.25rem;
}

.sidebar-group__label {
  margin: 0 0 0.375rem;
  padding: 0 0.625rem;
  color: hsl(var(--muted-foreground) / 0.72);
  font-size: 0.6875rem;
  font-weight: 620;
  line-height: 1.6;
  white-space: nowrap;
}

.sidebar-group__items {
  display: flex;
  flex-direction: column;
  gap: var(--sidebar-item-gap);
}

.sidebar-rail.is-collapsed :is(.sidebar-top-nav, .sidebar-nav, .sidebar-footer) {
  padding-inline: 0.375rem;
}

/* Keep first-level landmarks visible in the narrow rail. Only horizontal
   padding changes, so category and item geometry stay vertically stable. */
.sidebar-rail.is-collapsed .sidebar-group__label {
  padding-inline: 0;
  text-align: center;
}

@media (prefers-reduced-motion: reduce) {
  .sidebar-nav {
    transition: none;
  }
}
</style>
