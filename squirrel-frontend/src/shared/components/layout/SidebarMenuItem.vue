<template>
  <router-link
    :to="item.path"
    class="group relative flex items-center gap-3 h-9 px-3 rounded-lg text-[13px] transition-all duration-200 outline-none focus-visible:ring-2 focus-visible:ring-ring/40 focus-visible:ring-offset-2 focus-visible:ring-offset-sidebar"
    :class="[
      isActive
        ? 'bg-accent text-foreground font-semibold'
        : 'text-muted-foreground hover:bg-accent/60 hover:text-foreground'
    ]"
  >
    <!-- Active accent bar (left edge) -->
    <span
      v-if="isActive"
      aria-hidden="true"
      class="absolute left-0 top-1/2 -translate-y-1/2 h-4 w-[3px] rounded-r-full bg-primary"
    />

    <!-- Icon -->
    <AppIcon
      :name="item.icon"
      class="w-4 h-4 shrink-0 transition-transform duration-200 group-hover:scale-110 group-active:scale-90"
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