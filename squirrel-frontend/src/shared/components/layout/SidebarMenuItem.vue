<template>
  <router-link
    :to="item.path"
    class="flex items-center gap-3 px-3 h-9 rounded-lg text-[13px] transition-all duration-200 outline-none group"
    :class="[
      isActive 
        ? 'bg-zinc-200/60 dark:bg-zinc-800/80 text-foreground font-medium' 
        : 'text-muted-foreground hover:bg-zinc-200/40 dark:hover:bg-zinc-800/40 hover:text-foreground'
    ]"
  >
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
import AppIcon from '@/shared/icons/AppIcon.vue'
import type { AppIconName } from '@/shared/icons/app-icons'

defineProps<{
  item: {
    path: string
    name: string
    icon: AppIconName
  }
  isActive: boolean
}>()
</script>