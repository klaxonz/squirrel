<template>
  <Button text variant="secondary" size="sm" icon-only :aria-label="label" @click="$emit('click', $event)">
    <AppIcon :name="icon" class="h-4 w-4" />
  </Button>
</template>

<script setup lang="ts">
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
import type { AppIconName } from '@/shared/icons/app-icons'

defineProps<{
  icon: AppIconName
  label?: string
}>()

defineEmits<{
  click: [event: MouseEvent]
}>()
</script>
