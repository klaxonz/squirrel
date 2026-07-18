<template>
  <Button
    text severity="secondary"
    class="music-nav-item"
    :class="{ 'is-active': active }"
    :aria-current="active ? 'page' : undefined"
    @click="$emit('click')"
  >
    <AppIcon :name="item.icon" class="music-nav-item__icon" :stroke-width="active ? 2 : 1.75" />
    <span class="music-nav-item__label">{{ item.label }}</span>
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
/* Secondary rail item — same neutral selection language as app sidebar. */
.music-nav-item {
  justify-content: flex-start;
  gap: var(--space-2);
  width: calc(100% - 1.5rem);
  height: var(--sidebar-item-height);
  margin: 1px 0.75rem;
  padding: 0 0.625rem;
  border: 0;
  border-radius: var(--radius-md);
  color: hsl(var(--muted-foreground));
  font-size: 0.8125rem;
  font-weight: 500;
  text-align: left;
}

.music-nav-item:hover {
  background: hsl(var(--foreground) / 0.055);
  color: var(--app-selection-fg);
}

.music-nav-item.is-active {
  background: var(--app-selection-bg);
  color: var(--app-selection-fg);
  font-weight: 600;
}

.music-nav-item.is-active:hover {
  background: var(--app-selection-bg-hover);
}

.music-nav-item__icon {
  width: 1rem;
  height: 1rem;
  flex-shrink: 0;
  color: currentColor;
}

.music-nav-item__label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
