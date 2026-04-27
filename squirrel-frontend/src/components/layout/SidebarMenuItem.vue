<template>
  <router-link
    :to="item.path"
    class="flex items-center gap-2.5 px-3 h-8 rounded-md text-[13px] transition-all duration-200 outline-none group"
    :class="[
      isActive 
        ? 'bg-accent text-foreground font-medium shadow-[inset_0_1px_0_0_rgba(255,255,255,0.05)]' 
        : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground'
    ]"
  >
    <!-- Icon - Simple and clean -->
    <AppIcon
      :name="item.icon"
      class="w-4 h-4 shrink-0 transition-transform duration-200 group-active:scale-90"
      :class="[
        isActive ? 'text-foreground' : 'text-muted-foreground/60 group-hover:text-foreground'
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
