<template>
  <button
    class="music-nav-item"
    :class="{ 'music-nav-item--active': active }"
    @click="$emit('click')"
  >
    <AppIcon :name="item.icon" class="h-4 w-4" />
    <span>{{ item.label }}</span>
  </button>
</template>

<script setup lang="ts">
import AppIcon from '@/shared/icons/AppIcon.vue'
import type { AppIconName } from '@/shared/icons/app-icons'

interface NavItem {
  id: string
  label: string
  icon: AppIconName
}

defineProps<{
  item: NavItem
  active?: boolean
}>()

defineEmits<{
  click: []
}>()
</script>

<style scoped>
.music-nav-item {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.5rem 0.75rem;
  margin: 1px 0.75rem;
  width: calc(100% - 1.5rem);
  border: none;
  background: none;
  color: hsl(var(--muted-foreground));
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  text-align: left;
  border-radius: 0.5rem;
  position: relative;
}

.music-nav-item:hover {
  background: hsl(var(--foreground) / 0.04);
  color: hsl(var(--foreground));
}

.music-nav-item--active {
  background: hsl(var(--foreground) / 0.06);
  color: hsl(var(--foreground));
  font-weight: 600;
}

.music-nav-item--active :first-child {
  color: hsl(var(--primary));
}
</style>
