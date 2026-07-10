<template>
  <aside
    class="sidebar-rail"
    :class="{ 'has-player': showSidebarMusicPlayer }"
    aria-label="应用侧边栏"
  >
    <header class="sidebar-header">
      <RouterLink
        to="/home"
        class="sidebar-brand"
        aria-label="归仓（首页）"
      >
        <BrandLogo size="xs" />
        <span class="sidebar-brand__name">归仓</span>
      </RouterLink>
    </header>

    <div class="sidebar-quick-actions">
      <Button
        unstyled
        type="button"
        class="sidebar-command"
        @click="openGlobalSearch"
      >
        <AppIcon name="search" class="sidebar-command__icon" :stroke-width="1.75" />
        <span class="sidebar-command__label">搜索</span>
      </Button>

      <SidebarMenuItem
        v-for="item in SIDEBAR_TOP_ITEMS"
        :key="item.path"
        :item="item"
        :is-active="isNavigationItemActive(item, $route)"
      />
    </div>

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
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '@/shared/icons/AppIcon.vue'
import BrandLogo from '@/shared/components/BrandLogo.vue'
import SidebarMenuItem from './SidebarMenuItem.vue'
import { Button } from '@/shared/ui/button'
import {
  NAV_GROUPS,
  SIDEBAR_FOOTER_ITEMS,
  SIDEBAR_TOP_ITEMS,
  isNavigationItemActive,
} from '@/shared/constants/sidebar'
import { useMusicPlayerStore } from '@/features/music/stores/musicPlayer'
import { useUIStore } from '@/shared/stores/ui'

const NAV_ID = 'app-sidebar-nav'

const route = useRoute()
const router = useRouter()
const musicPlayerStore = useMusicPlayerStore()
const uiStore = useUIStore()

const primaryNavGroups = NAV_GROUPS

const showSidebarMusicPlayer = computed(() =>
  route.name !== 'Music' && Boolean(
    musicPlayerStore.currentTrack
    && (musicPlayerStore.resolvingUrl || musicPlayerStore.audioSrc || musicPlayerStore.error),
  ),
)

async function openGlobalSearch() {
  uiStore.requestGlobalSearchFocus()
  if (!route.meta?.showSearch) {
    await router.push('/home')
  }
}
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

.sidebar-header {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  height: 3.5rem;
  padding: 0 0.625rem;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex: 1 1 auto;
  min-width: 0;
  height: 2rem;
  padding: 0 0.625rem;
  border-radius: var(--radius-md);
  text-decoration: none;
  color: hsl(var(--foreground));
  outline: none;
}

.sidebar-brand:hover {
  color: hsl(var(--foreground));
}

.sidebar-brand:focus-visible {
  box-shadow: inset 0 0 0 2px hsl(var(--ring) / 0.65);
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

.sidebar-command {
  display: flex;
  align-items: center;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  background: transparent;
  color: hsl(var(--muted-foreground));
  font: inherit;
  cursor: pointer;
  transition:
    background-color var(--duration-fast) var(--ease-default),
    color var(--duration-fast) var(--ease-default);
}

.sidebar-command:hover {
  background: hsl(var(--foreground) / 0.055);
  color: hsl(var(--foreground));
}

.sidebar-command:focus-visible {
  outline: none;
  box-shadow: inset 0 0 0 2px hsl(var(--ring) / 0.65);
}

.sidebar-command__icon {
  width: 1.125rem;
  height: 1.125rem;
  flex: 0 0 auto;
}

.sidebar-quick-actions {
  flex: 0 0 auto;
  display: flex;
  flex-direction: column;
  gap: var(--sidebar-item-gap);
  padding: 0.25rem 0.625rem 0.625rem;
}

.sidebar-command {
  gap: 0.75rem;
  width: 100%;
  height: var(--sidebar-item-height);
  padding: 0 0.625rem;
  font-size: 0.8125rem;
  font-weight: 500;
}

.sidebar-command__label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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
  .sidebar-rail,
  .sidebar-command {
    transition: none;
  }
}
</style>
