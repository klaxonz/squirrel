<template>
  <aside
    class="sidebar-rail relative h-full flex flex-col bg-sidebar border-r border-sidebar-border select-none w-[var(--sidebar-width)]"
    :class="{ 'is-collapsed': !isSidebarOpen }"
  >
    <!-- Brand row — logo only, no toggle competing for space. -->
    <div class="flex items-center h-12 shrink-0" :class="isSidebarOpen ? 'px-3' : 'px-2'">
      <router-link
        to="/"
        class="flex items-center gap-2.5 h-8 px-1.5 rounded-md group outline-none focus-visible:ring-2 focus-visible:ring-ring/40"
        :class="isSidebarOpen ? 'flex-1 min-w-0' : 'w-full justify-center'"
        :title="isSidebarOpen ? undefined : '归仓'"
      >
        <BrandLogo size="sm" class="transition-transform duration-200 group-hover:scale-105 group-active:scale-95 shrink-0" />
        <span
          v-if="isSidebarOpen"
          class="text-sm font-semibold tracking-tight text-foreground font-display truncate"
        >归仓</span>
      </router-link>
    </div>

    <!-- Navigation -->
    <nav
      class="flex-1 overflow-y-auto overflow-x-hidden custom-scrollbar"
      :class="[
        isSidebarOpen ? 'px-2 space-y-4' : 'px-1.5 space-y-2',
        showSidebarMusicPlayer ? 'pb-20' : 'pb-2'
      ]"
    >
      <div v-for="group in NAV_GROUPS" :key="group.key">
        <div
          v-if="isSidebarOpen"
          class="px-2 mb-0.5"
        >
          <span class="text-2xs font-semibold tracking-[0.12em] text-muted-foreground/60 uppercase">
            {{ group.label }}
          </span>
        </div>
        <div class="space-y-0.5">
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

    <!-- Collapse toggle — pinned to the sidebar's right edge, vertically
         centered. Stays in one fixed spot across both states. -->
    <button
      type="button"
      class="sidebar-toggle"
      :title="isSidebarOpen ? '收起侧边栏' : '展开侧边栏'"
      @click="uiStore.toggleSidebar()"
    >
      <AppIcon :name="isSidebarOpen ? 'chevronLeft' : 'chevronRight'" class="w-3.5 h-3.5" />
    </button>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import BrandLogo from '@/shared/components/BrandLogo.vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import SidebarMenuItem from './SidebarMenuItem.vue'
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
  transition: width 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.sidebar-toggle {
  position: absolute;
  top: 50%;
  right: -13px;
  transform: translateY(-50%);
  z-index: 51;
  width: 26px;
  height: 26px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 9999px;
  background: hsl(var(--background));
  border: 1px solid hsl(var(--border) / 0.6);
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  box-shadow: 0 1px 3px hsl(var(--foreground) / 0.08);
  transition: background-color 0.12s ease, color 0.12s ease, border-color 0.12s ease;
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
