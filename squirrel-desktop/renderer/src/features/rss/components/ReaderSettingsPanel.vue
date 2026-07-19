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
          title="极简现代 (Inter)"
        >Inter</Button>
        <Button
          text severity="secondary"
          size="sm"
          @click="select('serif')"
          class="reader-settings-option font-serif"
          :class="{ 'is-selected': fontFamily === 'serif' }"
          title="经典衬线 (Georgia)"
        >Georgia</Button>
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
          :disabled="fontSize <= 12"
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
  </div>
</template>

<script setup lang="ts">
import { Button } from '@/shared/ui/button'

const props = defineProps<{
  visible: boolean
  fontFamily: 'sans' | 'serif'
  fontSize: number
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  'update:fontFamily': [value: 'sans' | 'serif']
  'update:fontSize': [value: number]
  save: []
}>()

function select(family: 'sans' | 'serif') {
  emit('update:fontFamily', family)
  emit('save')
}

function changeSize(delta: number) {
  const newSize = props.fontSize + delta
  if (newSize >= 12 && newSize <= 24) {
    emit('update:fontSize', newSize)
    emit('save')
  }
}
</script>

<style scoped>
.reader-settings-panel {
  position: absolute;
  top: 100%;
  right: 0;
  z-index: 50;
  width: 13rem;
  margin-top: 0.375rem;
  padding: 0.75rem;
  border: 1px solid hsl(var(--border) / 0.36);
  border-radius: 0.625rem;
  background: hsl(var(--popover));
  color: hsl(var(--popover-foreground));
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
  border-radius: 0.5rem;
  background: hsl(var(--accent) / 0.2);
}

.reader-settings-option,
.reader-settings-size-button {
  border: 1px solid transparent;
  border-radius: 0.375rem;
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
  background: hsl(var(--accent) / 0.36);
}

.reader-settings-option.is-selected {
  border-color: hsl(var(--border) / 0.68);
  background: hsl(var(--accent) / 0.72);
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
  background: hsl(var(--accent) / 0.24);
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
