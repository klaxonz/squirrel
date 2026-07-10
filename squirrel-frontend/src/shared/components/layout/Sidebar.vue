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
        <div
          :id="`sidebar-group-${group.key}`"
          class="sidebar-group__label"
        >
          <AppIcon :name="group.icon" class="sidebar-group__icon" :stroke-width="1.75" />
          <span>{{ group.label }}</span>
        </div>
        <div class="sidebar-group__items">
          <SidebarMenuItem
            v-for="item in group.items"
            :key="item.path"
            :item="item"
            :is-active="isNavigationItemActive(item, $route)"
            nested
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
import AppIcon from '@/shared/icons/AppIcon.vue'
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
.sidebar-rail {
  --sidebar-player-space: 6.25rem;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 0;
  border-right: 1px solid hsl(var(--sidebar-border) / 0.55);
  border-radius: 0;
  background: hsl(var(--sidebar));
  box-shadow: none;
  user-select: none;
  transition: padding-bottom var(--duration-base) var(--ease-out);
}

.sidebar-rail.has-player {
  padding-bottom: var(--sidebar-player-space);
}

.sidebar-top-nav {
  flex: 0 0 auto;
  display: flex;
  flex-direction: column;
  gap: var(--sidebar-item-gap);
  padding: 0.25rem 0.625rem 0.625rem;
}

.sidebar-nav {
  flex: 1 1 auto;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
  padding: 0.25rem 0.625rem 0.625rem;
}

.sidebar-group + .sidebar-group {
  margin-top: 1rem;
}

.sidebar-group__label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  height: 1.75rem;
  margin: 0 0 0.25rem;
  padding: 0 0.625rem;
  color: hsl(var(--muted-foreground) / 0.75);
  font-size: 0.75rem;
  font-weight: 500;
  line-height: 1.2;
}

.sidebar-group__icon {
  width: 1rem;
  height: 1rem;
  flex: 0 0 auto;
}

.sidebar-group__items {
  display: flex;
  flex-direction: column;
  gap: var(--sidebar-item-gap);
}

.sidebar-footer {
  flex: 0 0 auto;
  padding: 0.625rem;
  border-top: 1px solid var(--app-hairline);
}

@media (prefers-reduced-motion: reduce) {
  .sidebar-rail {
    transition: none;
  }
}
</style>
