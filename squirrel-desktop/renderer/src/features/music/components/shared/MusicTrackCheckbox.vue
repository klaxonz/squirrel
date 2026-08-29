<template>
  <Button
    text variant="secondary"
    size="sm" icon-only
    :class="checked && 'app-selection-active'"
    :aria-label="checked ? '取消选择' : '选择歌曲'"
    :aria-pressed="checked"
    @click="$emit('toggle')"
  >
    <AppIcon v-if="checked" name="check" class="h-4 w-4" />
    <AppIcon v-else name="circle" class="h-4 w-4" />
  </Button>
</template>

<script setup lang="ts">
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'

defineProps<{
  checked?: boolean
}>()

defineEmits<{
  toggle: []
}>()
</script>
