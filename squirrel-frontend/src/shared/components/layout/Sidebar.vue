<template>
  <aside class="w-[var(--sidebar-width)] h-full flex flex-col bg-sidebar border-r border-sidebar-border select-none">
    <!-- Brand Section — matches AppHeader's h-14 baseline so the logo aligns
         with the top-bar content row. -->
    <div class="h-14 flex items-center px-4 mb-3 shrink-0">
      <router-link to="/" class="flex items-center gap-2.5 px-2 group w-full rounded-md outline-none focus-visible:ring-2 focus-visible:ring-ring/40">
        <BrandLogo size="sm" class="transition-transform duration-200 group-hover:scale-105 group-active:scale-95" />
        <span class="text-sm font-semibold tracking-tight text-foreground font-display">归仓</span>
      </router-link>
    </div>

    <!-- Navigation Groups -->
    <nav
      class="flex-1 overflow-y-auto px-2.5 space-y-5 custom-scrollbar"
      :class="showSidebarMusicPlayer ? 'pb-20' : 'pb-4'"
    >
      <div v-for="group in NAV_GROUPS" :key="group.key">
        <div class="px-2.5 mb-1.5 flex items-center justify-between">
          <span class="text-2xs font-semibold tracking-[0.14em] text-muted-foreground/55 uppercase">
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
import BrandLogo from '@/shared/components/BrandLogo.vue'
import SidebarMenuItem from './SidebarMenuItem.vue'
import { NAV_GROUPS, isNavigationItemActive } from '@/shared/constants/sidebar'
import { useMusicPlayerStore } from '@/features/music/stores/musicPlayer'

const route = useRoute()
const musicPlayerStore = useMusicPlayerStore()

const showSidebarMusicPlayer = computed(() =>
  route.name !== 'Music' && Boolean(musicPlayerStore.currentTrack && (musicPlayerStore.resolvingUrl || musicPlayerStore.audioSrc))
)
</script>
