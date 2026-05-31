<template>
  <aside class="w-[var(--sidebar-width)] h-full flex flex-col bg-zinc-50/50 dark:bg-zinc-950/30 border-r border-border select-none">
    <!-- Brand Section (Premium Minimalist) -->
    <div class="h-16 flex items-center px-4 mt-2 mb-4">
      <router-link to="/" class="flex items-center gap-3 px-2 group w-full">
        <div class="w-8 h-8 bg-primary text-primary-foreground rounded-lg flex items-center justify-center shadow-[0_2px_10px_rgb(0,0,0,0.1)] transition-transform duration-300 group-hover:scale-105 group-active:scale-95">
          <AppIcon name="brand" class="w-4 h-4" />
        </div>
        <span class="text-[15px] font-bold tracking-tight text-foreground">松鼠</span>
      </router-link>
    </div>

    <!-- Navigation Groups -->
    <nav class="flex-1 overflow-y-auto px-3 space-y-6 scrollbar-hide pb-4">
      <div v-for="group in NAV_GROUPS" :key="group.key">
        <div class="px-2 mb-2 flex items-center justify-between">
          <span class="text-[11px] font-semibold tracking-wider text-muted-foreground/60 uppercase">
            {{ group.label }}
          </span>
        </div>
        <div class="space-y-1">
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
import AppIcon from '@/components/common/AppIcon.vue'
import SidebarMenuItem from './SidebarMenuItem.vue'
import { NAV_GROUPS, isNavigationItemActive } from '@/constants/sidebar'
</script>