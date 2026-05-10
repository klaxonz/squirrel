<template>
  <router-link
    :to="item.path"
    class="flex items-center gap-3 px-3 h-9 rounded-lg text-[13px] transition-all duration-200 outline-none group relative"
    :class="[
      isActive 
        ? 'bg-white dark:bg-zinc-800 text-foreground font-medium shadow-sm border border-border/80' 
        : 'text-muted-foreground hover:bg-zinc-200/50 dark:hover:bg-zinc-800/50 hover:text-foreground border border-transparent'
    ]"
  >
    <!-- Active Indicator Pill -->
    <div 
      v-if="isActive" 
      class="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-4 bg-primary rounded-r-full"
    ></div>

    <!-- Icon -->
    <AppIcon
      :name="item.icon"
      class="w-4 h-4 shrink-0 transition-transform duration-200 group-active:scale-90"
      :class="[
        isActive ? 'text-primary' : 'text-muted-foreground/80 group-hover:text-foreground'
      ]"
    />

    <span class="truncate tracking-tight">{{ item.name }}</span>
  </router-link>
</template>

<script setup lang="ts">
import AppIcon from '@/components/common/AppIcon.vue'
import type { AppIconName } from '@/icons/app-icons'

defineProps<{
  item: {
    path: string
    name: string
    icon: AppIconName
  }
  isActive: boolean
}>()
</script>