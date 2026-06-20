<template>
  <aside class="w-[var(--sidebar-width)] h-full flex flex-col bg-sidebar border-r border-border/60 select-none">
    <!-- Brand Section — matches AppHeader's h-14 baseline so the logo aligns
         with the top-bar content row. -->
    <div class="h-14 flex items-center px-4 mb-2 shrink-0">
      <router-link to="/" class="flex items-center gap-2.5 px-2 group w-full rounded-lg outline-none focus-visible:ring-2 focus-visible:ring-ring/40">
        <div class="w-8 h-8 text-primary-foreground rounded-lg flex items-center justify-center transition-transform duration-300 group-hover:scale-105 group-active:scale-95 bg-gradient-to-br shadow-[0_2px_10px_hsl(var(--primary)/0.35)]" style="background-image: linear-gradient(135deg, hsl(var(--primary)), hsl(28 80% 46%));">
          <AppIcon name="brand" class="w-4 h-4" />
        </div>
        <span class="text-[16px] font-bold tracking-tight text-foreground font-display">归仓</span>
      </router-link>
    </div>

    <!-- Navigation Groups -->
    <nav
      class="flex-1 overflow-y-auto px-3 space-y-6 custom-scrollbar"
      :class="showSidebarMusicPlayer ? 'pb-20' : 'pb-4'"
    >
      <div v-for="group in NAV_GROUPS" :key="group.key">
        <div class="px-2 mb-2 flex items-center justify-between">
          <span class="text-[11px] font-semibold tracking-wider text-muted-foreground/60 uppercase">
            {{ group.label }}
          </span>
        </div>
        <div class="space-y-0.5">
          <SidebarMenuItem
            v-for="item in group.items"
            :key="item.path"
            :item="item"
            :is-active="isNavigationItemActive(item, $route)"
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
import SidebarMenuItem from './SidebarMenuItem.vue'
import { NAV_GROUPS, isNavigationItemActive } from '@/shared/constants/sidebar'
import { useMusicPlayerStore } from '@/features/music/stores/musicPlayer'

const route = useRoute()
const musicPlayerStore = useMusicPlayerStore()

const showSidebarMusicPlayer = computed(() =>
  route.name !== 'Music' && Boolean(musicPlayerStore.currentTrack && (musicPlayerStore.resolvingUrl || musicPlayerStore.audioSrc))
)
</script>
