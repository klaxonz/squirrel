<template>
  <div class="music-empty-state">
    <AppIcon :name="icon" class="h-10 w-10" />
    <p>{{ text }}</p>
  </div>
</template>

<script setup lang="ts">
import AppIcon from '@/components/common/AppIcon.vue'
import type { AppIconName } from '@/icons/app-icons'

withDefaults(defineProps<{
  icon?: AppIconName
  text?: string
}>(), {
  icon: 'search',
  text: '暂无内容',
})
</script>

<style scoped>
.music-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 4rem 1rem;
  color: hsl(var(--muted-foreground) / 0.4);
  font-size: 0.875rem;
}
</style>
