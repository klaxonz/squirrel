<template>
  <div
    v-if="visible"
    class="reader-settings-panel"
  >
    <div class="reader-settings-section">
      <span class="reader-settings-label">排版字体</span>
      <div class="reader-settings-grid">
        <Button
          text severity="secondary"
          size="sm"
          @click="select('sans')"
          class="reader-settings-option"
          :class="{ 'is-selected': fontFamily === 'sans' }"
          title="现代无衬线（推荐）"
        >无衬线</Button>
        <Button
          text severity="secondary"
          size="sm"
          @click="select('serif')"
          class="reader-settings-option font-serif"
          :class="{ 'is-selected': fontFamily === 'serif' }"
          title="经典衬线"
        >衬线</Button>
      </div>
    </div>

    <div class="reader-settings-section">
      <div class="reader-settings-row">
        <span class="reader-settings-label">字号大小</span>
        <span class="reader-settings-value">{{ fontSize }}px</span>
      </div>
      <div class="reader-settings-size-controls">
        <Button
          text severity="secondary"
          size="sm"
          @click="changeSize(-1)"
          class="reader-settings-size-button"
          :disabled="fontSize <= 14"
        >A-</Button>
        <Button
          text severity="secondary"
          size="sm"
          @click="changeSize(1)"
          class="reader-settings-size-button"
          :disabled="fontSize >= 24"
        >A+</Button>
      </div>
    </div>

    <div class="reader-settings-section">
      <span class="reader-settings-label">默认筛选</span>
      <div class="reader-settings-grid">
        <Button
          v-for="option in filterOptions"
          :key="option.value"
          text severity="secondary"
          size="sm"
          class="reader-settings-option"
          :class="{ 'is-selected': defaultEntryFilter === option.value }"
          :title="option.title"
          @click="selectDefaultFilter(option.value)"
        >{{ option.label }}</Button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Button } from '@/shared/ui/button'
import type { RssEntryFilter } from '@/features/rss/types/rss'

const filterOptions: Array<{ value: RssEntryFilter; label: string; title: string }> = [
  { value: 'all', label: '全部', title: '进入时显示全部文章' },
  { value: 'unread', label: '未读', title: '进入时显示未读文章' },
  { value: 'starred', label: '星标', title: '进入时显示星标文章' },
  { value: 'recent', label: '最近', title: '进入时显示最近浏览' },
]

const props = defineProps<{
  visible: boolean
  fontFamily: 'sans' | 'serif'
  fontSize: number
  defaultEntryFilter: RssEntryFilter
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  'update:fontFamily': [value: 'sans' | 'serif']
  'update:fontSize': [value: number]
  'update:defaultEntryFilter': [value: RssEntryFilter]
  save: []
}>()

function select(family: 'sans' | 'serif') {
  emit('update:fontFamily', family)
  emit('save')
}

function changeSize(delta: number) {
  const newSize = props.fontSize + delta
  if (newSize >= 14 && newSize <= 24) {
    emit('update:fontSize', newSize)
    emit('save')
  }
}

function selectDefaultFilter(filter: RssEntryFilter) {
  emit('update:defaultEntryFilter', filter)
}
</script>

<style scoped>
.reader-settings-panel {
  position: absolute;
  top: 100%;
  right: 0;
  z-index: 50;
  width: 14.5rem;
  margin-top: 0.375rem;
  padding: 0.75rem;
  border: 1px solid hsl(var(--border) / 0.36);
  border-radius: var(--radius-lg);
  background: hsl(var(--popover));
  color: hsl(var(--popover-foreground));
  box-shadow: var(--app-floating-shadow);
}

.reader-settings-section {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.reader-settings-section + .reader-settings-section {
  margin-top: 0.75rem;
}

.reader-settings-label {
  display: block;
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
  font-weight: 650;
}

.reader-settings-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.25rem;
  padding: 0.25rem;
  border: 1px solid hsl(var(--border) / 0.18);
  border-radius: var(--radius-md);
  background: var(--app-filter-track-bg);
}

.reader-settings-option,
.reader-settings-size-button {
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  height: auto;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 650;
}

.reader-settings-option {
  padding: 0.3125rem 0.375rem;
  text-align: center;
}

.reader-settings-option:hover,
.reader-settings-size-button:hover:not(:disabled) {
  color: hsl(var(--foreground));
  background: var(--app-selection-bg-hover);
}

.reader-settings-option.is-selected {
  border-color: var(--app-selection-border);
  background: var(--app-selection-bg);
  color: hsl(var(--foreground));
}

.reader-settings-row,
.reader-settings-size-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.reader-settings-value {
  color: hsl(var(--foreground) / 0.82);
  font-size: 0.75rem;
  font-variant-numeric: tabular-nums;
  font-weight: 650;
}

.reader-settings-size-controls {
  gap: 0.375rem;
}

.reader-settings-size-button {
  flex: 1 1 0;
  min-height: 1.875rem;
  border-color: hsl(var(--border) / 0.42);
  background: var(--app-selection-bg);
}

.reader-settings-size-button:disabled {
  cursor: not-allowed;
  opacity: 0.42;
}

@media (prefers-reduced-motion: reduce) {
  .reader-settings-option,
  .reader-settings-size-button {
    transition: none;
  }
}
</style>
