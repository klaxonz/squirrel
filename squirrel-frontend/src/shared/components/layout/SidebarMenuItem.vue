<template>
  <router-link
    :to="item.path"
    class="group relative flex items-center gap-3 h-9 px-3 rounded-md text-sm transition-all duration-150 outline-none focus-visible:ring-2 focus-visible:ring-ring/40 focus-visible:ring-offset-2 focus-visible:ring-offset-sidebar"
    :class="[
      isActive
        ? 'is-active bg-primary/18 text-foreground font-medium ring-1 ring-inset ring-primary/25'
        : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground'
    ]"
  >
    <AppIcon
      :name="item.icon"
      class="w-4 h-4 shrink-0 transition-colors duration-150"
      :class="[
        isActive ? 'text-primary drop-shadow-[0_0_6px_hsl(var(--primary)/0.5)]' : 'text-muted-foreground/70 group-hover:text-foreground'
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
