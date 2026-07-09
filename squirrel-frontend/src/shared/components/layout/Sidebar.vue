<template>
  <aside
    class="sidebar-rail"
    :class="{ 'is-collapsed': !isSidebarOpen }"
    :aria-expanded="isSidebarOpen"
  >
    <div class="sidebar-top">
      <RouterLink
        v-show="isSidebarOpen"
        to="/home"
        class="sidebar-brand"
        aria-label="归仓（首页）"
      >
        <BrandLogo size="xs" />
        <span class="sidebar-brand__name">归仓</span>
      </RouterLink>

      <Button
        variant="ghost"
        size="mini-icon"
        type="button"
        class="sidebar-toggle"
        :title="isSidebarOpen ? '收起侧边栏 (Ctrl+B)' : '展开侧边栏 (Ctrl+B)'"
        :aria-label="isSidebarOpen ? '收起侧边栏' : '展开侧边栏'"
        :aria-expanded="isSidebarOpen"
        :aria-controls="NAV_ID"
        @click="uiStore.toggleSidebar()"
      >
        <AppIcon
          name="chevronLeft"
          class="sidebar-toggle__icon"
          :class="{ 'is-collapsed': !isSidebarOpen }"
          :stroke-width="2"
        />
      </Button>
    </div>

    <nav
      :id="NAV_ID"
      class="sidebar-nav custom-scrollbar"
      :class="{ 'has-player': showSidebarMusicPlayer }"
      aria-label="主导航"
    >
      <div
        v-for="group in NAV_GROUPS"
        :key="group.key"
        class="sidebar-group"
      >
        <div
          v-if="isSidebarOpen"
          class="sidebar-group__label"
        >
          {{ group.label }}
        </div>
        <div class="sidebar-group__items">
          <SidebarMenuItem
            v-for="item in group.items"
            :key="item.path"
            :item="item"
            :is-active="isNavigationItemActive(item, $route)"
            :collapsed="!isSidebarOpen"
          />
        </div>
      </div>
    </nav>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppIcon from '@/shared/icons/AppIcon.vue'
import BrandLogo from '@/shared/components/BrandLogo.vue'
import SidebarMenuItem from './SidebarMenuItem.vue'
import { Button } from '@/shared/ui/button'
import { NAV_GROUPS, isNavigationItemActive } from '@/shared/constants/sidebar'
import { useMusicPlayerStore } from '@/features/music/stores/musicPlayer'
import { useUIStore } from '@/shared/stores/ui'

const NAV_ID = 'app-sidebar-nav'

const route = useRoute()
const musicPlayerStore = useMusicPlayerStore()
const uiStore = useUIStore()

const isSidebarOpen = computed(() => uiStore.isSidebarOpen)

const showSidebarMusicPlayer = computed(() =>
  route.name !== 'Music' && Boolean(musicPlayerStore.currentTrack && (musicPlayerStore.resolvingUrl || musicPlayerStore.audioSrc)),
)
</script>

<style scoped>
/*
  Boring on purpose.
  - Brand + collapse share one top row inside the card (not edge, not app header).
  - Collapse is a normal icon button; chevron rotates — no icon-set swap.
  - Collapsed: brand hides, toggle centers, nav is icon-only.
*/
.sidebar-rail {
  width: var(--sidebar-width);
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid hsl(var(--sidebar-border) / 0.82);
  border-radius: var(--radius-xl);
  background: hsl(var(--sidebar));
  box-shadow: var(--app-surface-shadow);
  user-select: none;
  transition: width var(--duration-base) var(--ease-out);
}

.sidebar-top {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 0.25rem;
  height: 2.75rem;
  padding: 0 0.5rem 0 0.625rem;
  border-bottom: 1px solid hsl(var(--sidebar-border) / 0.5);
}

.sidebar-rail.is-collapsed .sidebar-top {
  justify-content: center;
  padding-inline: 0.375rem;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
  flex: 1 1 auto;
  height: 1.75rem;
  padding: 0 0.125rem;
  border-radius: var(--radius-md);
  text-decoration: none;
  color: hsl(var(--foreground));
  outline: none;
}

.sidebar-brand:hover {
  background: hsl(var(--card) / 0.45);
}

.sidebar-brand:focus-visible {
  box-shadow: 0 0 0 2px hsl(var(--sidebar)), 0 0 0 4px hsl(var(--ring) / 0.4);
}

.sidebar-brand__name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: var(--font-display);
  font-size: 0.9375rem;
  font-weight: 600;
  letter-spacing: -0.015em;
  line-height: 1.2;
}

.sidebar-toggle {
  flex: 0 0 auto;
  margin-left: auto;
  color: hsl(var(--muted-foreground));
}

.sidebar-rail.is-collapsed .sidebar-toggle {
  margin-left: 0;
}

.sidebar-toggle:hover {
  color: hsl(var(--foreground));
}

.sidebar-toggle__icon {
  width: 1rem;
  height: 1rem;
  display: block;
  transition: transform var(--duration-base) var(--ease-out);
}

.sidebar-toggle__icon.is-collapsed {
  transform: rotate(180deg);
}

.sidebar-nav {
  flex: 1 1 auto;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
  padding: 0.75rem 0.5rem;
}

.sidebar-nav.has-player {
  padding-bottom: 5rem;
}

.sidebar-group + .sidebar-group {
  margin-top: 1.25rem;
}

.sidebar-group__label {
  margin: 0 0 0.375rem;
  padding: 0 0.625rem;
  color: hsl(var(--muted-foreground) / 0.72);
  font-size: 0.6875rem;
  font-weight: 600;
  line-height: 1.2;
}

.sidebar-group__items {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

@media (prefers-reduced-motion: reduce) {
  .sidebar-rail,
  .sidebar-toggle__icon {
    transition: none;
  }
}
</style>
