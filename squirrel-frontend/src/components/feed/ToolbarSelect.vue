<template>
  <Select
    :model-value="modelValue"
    @update:model-value="handleValueChange"
  >
    <SelectTrigger class="filter-trigger-minimal" :style="triggerStyle">
      <div class="filter-trigger-content">
        <span class="filter-label">{{ label }} //</span>
        <span class="filter-value">{{ currentLabel }}</span>
      </div>
    </SelectTrigger>
    <SelectContent class="filter-content-minimal" :side-offset="8">
      <SelectItem v-for="option in options" :key="option.value" :value="option.value" class="filter-item-minimal">
        <span class="select-item-text">{{ option.label }}</span>
      </SelectItem>
    </SelectContent>
  </Select>
</template>

<script setup>
import { computed } from 'vue'
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
})

const emit = defineEmits(['update:modelValue'])

const triggerStyle = computed(() => ({
  '--filter-min-width': props.minWidth,
}))

const handleValueChange = (value) => {
  emit('update:modelValue', String(value))
}
</script>

<style scoped>
.filter-trigger-minimal {
  background: transparent !important;
  border: none !important;
  padding: 0 !important;
  height: auto !important;
  min-width: var(--filter-min-width, 6rem);
  box-shadow: none !important;
  outline: none !important;
}

.filter-trigger-content {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-family: 'JetBrains Mono', 'Courier New', monospace;
  text-transform: uppercase;
  font-size: 0.65rem;
  letter-spacing: 0.12em;
  color: rgba(255, 255, 255, 0.3);
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.filter-trigger-minimal:hover .filter-trigger-content {
  color: rgba(255, 255, 255, 0.9);
}

.filter-label {
  font-weight: 500;
}

.filter-value {
  color: #ff4d00;
  font-weight: 800;
}

/* 下拉菜单容器：强制覆盖底层组件样式 */
:deep([data-radix-popper-content-wrapper]) {
  z-index: 100 !important;
}

:deep(.filter-content-minimal) {
  background-color: rgba(5, 5, 5, 0.98) !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  border-radius: 4px !important;
  padding: 0 !important;
  min-width: 190px !important;
  box-shadow: 0 40px 80px rgba(0, 0, 0, 0.9) !important;
  backdrop-filter: blur(20px);
}

/* 选项样式强制覆盖 */
:deep(.filter-item-minimal) {
  border-radius: 0 !important;
  margin: 0 !important;
  border-bottom: 1px solid rgba(255, 255, 255, 0.02) !important;
  color: rgba(255, 255, 255, 0.3) !important;
}

:deep(.filter-item-minimal:last-child) {
  border-bottom: none !important;
}

/* 悬停状态 */
:deep(.filter-item-minimal[data-highlighted]),
:deep(.filter-item-minimal:hover) {
  background-color: rgba(255, 255, 255, 0.03) !important;
  color: rgba(255, 255, 255, 0.8) !important;
}

/* 选中状态 */
:deep(.filter-item-minimal[data-state="checked"]) {
  color: #fff !important;
}
</style>
