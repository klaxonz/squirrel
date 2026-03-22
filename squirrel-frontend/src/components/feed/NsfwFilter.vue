<template>
  <Select :model-value="modelValue" @update:model-value="handleValueChange">
    <SelectTrigger class="toolbar-select">
      <div class="toolbar-select__copy">
        <ShieldCheckIcon class="h-4 w-4 shrink-0 text-muted-foreground" />
        <span v-if="!isMobile" class="toolbar-select__label">敏感内容</span>
        <span class="toolbar-select__value">{{ currentLabel }}</span>
      </div>
    </SelectTrigger>
    <SelectContent class="toolbar-select__content">
      <SelectItem v-for="option in nsfwOptions" :key="option.value" :value="option.value">
        {{ option.label }}
      </SelectItem>
    </SelectContent>
  </Select>
</template>

<script setup>
import { computed } from 'vue'
import { ShieldCheckIcon } from '@heroicons/vue/24/outline'
import { isMobile } from '@/composables/useMobile'
import { Select, SelectContent, SelectItem, SelectTrigger } from '@/components/ui/select'

const props = defineProps({
  modelValue: {
    type: String,
    required: true,
  },
})

const emit = defineEmits(['update:modelValue'])

const nsfwOptions = [
  { value: 'all', label: '全部' },
  { value: 'yes', label: '仅 NSFW' },
  { value: 'no', label: '仅安全内容' },
]

const currentLabel = computed(() => {
  return nsfwOptions.find((option) => option.value === props.modelValue)?.label || '全部'
})

const handleValueChange = (value) => {
  emit('update:modelValue', String(value))
}
</script>

<style scoped>
.toolbar-select {
  width: auto;
  flex: 0 0 auto;
  max-width: 100%;
  min-width: 9rem;
  border-radius: 9999px;
  border-color: hsl(var(--border) / 0.72);
  background: hsl(var(--card) / 0.82);
  box-shadow: 0 12px 28px hsl(var(--surface-shadow) / 0.08);
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
  border-radius: calc(var(--radius-xl) + 2px);
}

@media (max-width: 768px) {
  .toolbar-select {
    min-width: auto;
    width: 3rem;
    padding-left: 0.7rem;
    padding-right: 0.7rem;
  }

  .toolbar-select__copy {
    justify-content: center;
  }

  .toolbar-select__value {
    display: none;
  }
}
</style>
