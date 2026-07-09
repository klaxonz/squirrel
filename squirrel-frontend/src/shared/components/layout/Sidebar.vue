<template>
  <aside
    class="sidebar-rail"
    :class="{ 'is-collapsed': !isSidebarOpen }"
  >
    <nav
      class="sidebar-nav custom-scrollbar"
      :class="[
        isSidebarOpen ? 'is-expanded' : 'is-compact',
        showSidebarMusicPlayer ? 'has-player' : ''
      ]"
    >
      <div v-for="group in NAV_GROUPS" :key="group.key" class="sidebar-group">
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

    <Button
      variant="ghost"
      size="icon-sm"
      type="button"
      class="sidebar-toggle"
      :title="isSidebarOpen ? '收起侧边栏' : '展开侧边栏'"
      :aria-label="isSidebarOpen ? '收起侧边栏' : '展开侧边栏'"
      @click="uiStore.toggleSidebar()"
    >
      <AppIcon :name="isSidebarOpen ? 'chevronLeft' : 'chevronRight'" class="w-3.5 h-3.5" />
    </Button>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppIcon from '@/shared/icons/AppIcon.vue'
import SidebarMenuItem from './SidebarMenuItem.vue'
import { Button } from '@/shared/ui/button'
import { NAV_GROUPS, isNavigationItemActive } from '@/shared/constants/sidebar'
import { useMusicPlayerStore } from '@/features/music/stores/musicPlayer'
import { useUIStore } from '@/shared/stores/ui'

const route = useRoute()
const musicPlayerStore = useMusicPlayerStore()
const uiStore = useUIStore()

const isSidebarOpen = computed(() => uiStore.isSidebarOpen)

const showSidebarMusicPlayer = computed(() =>
  route.name !== 'Music' && Boolean(musicPlayerStore.currentTrack && (musicPlayerStore.resolvingUrl || musicPlayerStore.audioSrc))
)
</script>

<style scoped>
.sidebar-rail {
  position: relative;
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
  transition:
    width var(--duration-base) var(--ease-default),
    border-color var(--duration-fast) var(--ease-default);
}

.sidebar-nav {
  flex: 1 1 auto;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
}

.sidebar-nav.is-expanded {
  padding: var(--space-4) var(--space-3) var(--space-3);
}

.sidebar-nav.is-compact {
  padding: var(--space-4) var(--space-2) var(--space-3);
}

.sidebar-nav.has-player {
  padding-bottom: 5rem;
}

.sidebar-group + .sidebar-group {
  margin-top: var(--space-6);
}

.sidebar-group__label {
  margin: 0 0 var(--space-2);
  padding: 0 var(--space-2);
  color: hsl(var(--muted-foreground) / 0.78);
  font-size: 0.6875rem;
  font-weight: 650;
  letter-spacing: 0;
}

.sidebar-group__items {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sidebar-toggle {
  position: absolute;
  right: var(--space-2);
  bottom: var(--space-2);
  z-index: 1;
  width: 1.75rem;
  height: 1.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  background: hsl(var(--card) / 0.62);
  border: 1px solid hsl(var(--border) / 0.6);
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  box-shadow: 0 1px 0 hsl(var(--foreground) / 0.04) inset;
  transition:
    background-color var(--duration-fast) var(--ease-default),
    color var(--duration-fast) var(--ease-default),
    border-color var(--duration-fast) var(--ease-default);
}
.sidebar-toggle:hover {
  background: hsl(var(--accent));
  color: hsl(var(--foreground));
  border-color: hsl(var(--primary) / 0.4);
}
.sidebar-toggle:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px hsl(var(--background)), 0 0 0 4px hsl(var(--ring) / 0.4);
}
</style>
