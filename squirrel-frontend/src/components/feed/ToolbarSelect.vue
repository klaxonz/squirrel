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
        <div class="item-inner">
          <span class="item-status"></span>
          <span class="select-item-text">{{ option.label }}</span>
        </div>
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
  font-family: 'Courier New', Courier, monospace;
  text-transform: uppercase;
  font-size: 0.6rem;
  letter-spacing: 0.1em;
  color: rgba(255, 255, 255, 0.3);
  transition: color 0.3s;
}

.filter-trigger-minimal:hover .filter-trigger-content {
  color: #fff;
}

.filter-label {
  font-weight: 400;
}

.filter-value {
  color: #ff4d00;
  font-weight: 700;
}

/* 下拉菜单容器：强制覆盖底层组件样式 */
:deep([data-radix-popper-content-wrapper]) {
  z-index: 100 !important;
}

:deep(.filter-content-minimal) {
  background-color: #050505 !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  border-radius: 0 !important;
  padding: 0 !important;
  min-width: 180px !important;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.9) !important;
}

/* 内部视图容器也需要强制黑色 */
:deep(.filter-content-minimal [data-radix-select-viewport]) {
  background-color: #050505 !important;
  padding: 0 !important;
}

.content-header-minimal,
.content-footer-minimal {
  padding: 0.6rem 1rem;
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.5rem;
  letter-spacing: 0.2em;
  color: rgba(255, 255, 255, 0.3);
  background: rgba(255, 255, 255, 0.03);
}

/* 选项样式强制覆盖 */
:deep(.filter-item-minimal) {
  padding: 0.8rem 1rem !important;
  border-radius: 0 !important;
  background-color: transparent !important;
  color: rgba(255, 255, 255, 0.4) !important;
  cursor: pointer !important;
  outline: none !important;
}

/* 移除 shadcn 默认的 Check 图标区域，我们使用自定义的 item-status */
:deep(.filter-item-minimal span:last-child) {
  right: auto !important;
  position: relative !important;
  display: block !important;
  width: 100% !important;
}

/* 悬停状态 */
:deep(.filter-item-minimal[data-highlighted]),
:deep(.filter-item-minimal:hover) {
  background-color: rgba(255, 255, 255, 0.05) !important;
}

:deep(.filter-item-minimal[data-highlighted]) .select-item-text,
:deep(.filter-item-minimal:hover) .select-item-text {
  color: #fff !important;
}

/* 选中状态 */
:deep(.filter-item-minimal[data-state="checked"]) {
  background-color: rgba(255, 77, 0, 0.08) !important;
}

:deep(.filter-item-minimal[data-state="checked"]) .select-item-text {
  color: #ff4d00 !important;
  font-weight: 700 !important;
}

:deep(.filter-item-minimal[data-state="checked"]) .item-status {
  background-color: #ff4d00 !important;
  box-shadow: 0 0 8px #ff4d00;
}
</style>
