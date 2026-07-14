<template>
  <div class="app-search-input" :class="props.class">
    <AppIcon name="search" class="app-search-input__icon" />
    <Input
      :model-value="modelValue"
      :placeholder="placeholder"
      :aria-label="ariaLabel || placeholder"
      class="app-search-input__control"
      @update:model-value="emit('update:modelValue', String($event))"
    />
    <Button
      v-if="modelValue"
      type="button"
      variant="ghost"
      size="mini-icon"
      class="app-search-input__clear"
      :aria-label="clearLabel"
      :title="clearLabel"
      @click="emit('update:modelValue', '')"
    >
      <AppIcon name="close" class="h-4 w-4" />
    </Button>
  </div>
</template>

<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'

const props = withDefaults(defineProps<{
  modelValue: string
  placeholder: string
  ariaLabel?: string
  clearLabel?: string
  class?: HTMLAttributes['class']
}>(), {
  ariaLabel: '',
  clearLabel: '清空搜索',
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()
</script>

<style scoped>
.app-search-input {
  position: relative;
  width: 100%;
}

.app-search-input__icon {
  position: absolute;
  top: 50%;
  left: 0.75rem;
  width: 0.875rem;
  height: 0.875rem;
  color: hsl(var(--muted-foreground) / 0.7);
  transform: translateY(-50%);
  pointer-events: none;
}

.app-search-input:focus-within .app-search-input__icon {
  color: hsl(var(--primary));
}

:deep(.app-search-input__control) {
  padding-left: 2.25rem;
  padding-right: 2.25rem;
}

.app-search-input__clear {
  position: absolute;
  top: 50%;
  right: 0.375rem;
  color: hsl(var(--muted-foreground) / 0.72);
  transform: translateY(-50%);
}
</style>
