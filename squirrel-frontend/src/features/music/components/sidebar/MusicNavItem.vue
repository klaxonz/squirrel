<template>
  <Button
    variant="ghost"
    class="music-nav-item"
    :class="{ 'music-nav-item--active': active }"
    :aria-current="active ? 'page' : undefined"
    @click="$emit('click')"
  >
    <AppIcon :name="item.icon" class="h-4 w-4" />
    <span>{{ item.label }}</span>
  </Button>
</template>

<script setup lang="ts">
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
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
  justify-content: flex-start;
  gap: 0.625rem;
  padding: 0.5rem 0.75rem;
  margin: 1px 0.75rem;
  width: calc(100% - 1.5rem);
  color: hsl(var(--muted-foreground));
  font-size: 0.8125rem;
  text-align: left;
  border-radius: var(--radius-md);
  position: relative;
}

.music-nav-item--active {
  border-color: hsl(var(--primary) / 0.18);
  background: hsl(var(--primary) / 0.08);
  color: hsl(var(--foreground));
  font-weight: 600;
}

.music-nav-item--active :first-child {
  color: hsl(var(--primary));
}
</style>
