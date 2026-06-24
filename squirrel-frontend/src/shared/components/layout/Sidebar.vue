<template>
  <aside
    class="h-full flex flex-col bg-sidebar border-r border-sidebar-border select-none w-[var(--sidebar-width)]"
  >
    <!-- Brand row — logo + name on the left, collapse toggle on the right.
         Folded mode drops the name and centers the logo; the toggle drops to
         its own row below the rail. -->
    <div class="flex items-center gap-2 px-3 h-12 shrink-0">
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
      <button
        v-if="isSidebarOpen"
        type="button"
        class="shrink-0 w-8 h-8 flex items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring/40"
        title="收起侧边栏"
        @click="uiStore.toggleSidebar()"
      >
        <AppIcon name="chevronLeft" class="w-4 h-4" />
      </button>
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

    <!-- Folded-mode toggle — only the icon row, centered at the bottom. -->
    <button
      v-if="!isSidebarOpen"
      type="button"
      class="shrink-0 mx-auto mb-2 w-8 h-8 flex items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring/40"
      title="展开侧边栏"
      @click="uiStore.toggleSidebar()"
    >
      <AppIcon name="chevronRight" class="w-4 h-4" />
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