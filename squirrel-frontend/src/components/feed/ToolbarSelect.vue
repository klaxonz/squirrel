<template>
  <Select
    :model-value="modelValue"
    :open="open"
    @update:model-value="handleValueChange"
    @update:open="handleOpenChange"
  >
    <SelectTrigger class="toolbar-select" :style="triggerStyle">
      <div class="toolbar-select__copy">
        <component :is="icon" class="h-4 w-4 shrink-0 text-muted-foreground" />
        <span v-if="!isMobile && label" class="toolbar-select__label">{{ label }}</span>
        <span class="toolbar-select__value">{{ currentLabel }}</span>
      </div>
    </SelectTrigger>
    <SelectContent class="toolbar-select__content">
      <SelectItem v-for="option in options" :key="option.value" :value="option.value">
        {{ option.label }}
      </SelectItem>
    </SelectContent>
  </Select>
</template>

<script setup>
import { computed } from 'vue'
import { isMobile } from '@/composables/useMobile'
import { Select, SelectContent, SelectItem, SelectTrigger } from '@/components/ui/select'

const props = defineProps({
  modelValue: {
    type: String,
    required: true,
  },
  label: {
    type: String,
    default: '',
  },
  currentLabel: {
    type: String,
    required: true,
  },
  options: {
    type: Array,
    default: () => [],
  },
  icon: {
    type: [Object, Function],
    required: true,
  },
  minWidth: {
    type: String,
    default: '7rem',
  },
  open: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:modelValue', 'update:open'])

const triggerStyle = computed(() => ({
  '--toolbar-select-min-width': props.minWidth,
}))

const handleValueChange = (value) => {
  emit('update:modelValue', String(value))
  emit('update:open', false)
}

const handleOpenChange = (value) => {
  emit('update:open', !!value)
}
</script>

<style scoped>
.toolbar-select {
  width: auto;
  flex: 0 0 auto;
  max-width: 100%;
  min-width: var(--toolbar-select-min-width, 7rem);
  border-color: hsl(var(--border) / 0.82);
  background: hsl(var(--card));
  box-shadow:
    inset 0 1px 0 hsl(var(--background) / 0.9),
    0 1px 2px hsl(20 20% 20% / 0.04);
}

.toolbar-select__copy {
  display: inline-flex;
  width: 100%;
  align-items: center;
  gap: 0.4rem;
  min-width: 0;
}

.toolbar-select__label {
  font-size: var(--font-size-2xs);
  color: hsl(var(--muted-foreground));
}

.toolbar-select__value {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.toolbar-select__content {
  border-radius: calc(var(--radius-lg) + 2px);
}

@media (max-width: 768px) {
  .toolbar-select {
    min-width: auto;
    width: 2.5rem;
    padding-left: 0.55rem;
    padding-right: 0.55rem;
  }

  .toolbar-select__copy {
    justify-content: center;
  }

  .toolbar-select__value {
    display: none;
  }
}
</style>
