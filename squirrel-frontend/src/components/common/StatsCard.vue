<template>
  <Card class="p-4" :hover-effect="hoverEffect">
    <div class="flex items-center justify-between">
      <div class="flex-1">
        <div class="text-xs text-text-tertiary mb-1">{{ title }}</div>
        <div
          :class="[
            'text-2xl font-bold font-mono mb-2',
            valueColorClass
          ]"
        >
          {{ formattedValue }}
        </div>

        <!-- 子信息 -->
        <div v-if="$slots.subtitle" class="text-xs text-text-secondary">
          <slot name="subtitle" />
        </div>

        <!-- 进度条 -->
        <ProgressBar
          v-if="showProgress"
          :percent="progressPercent"
          :variant="progressVariant"
          :show-label="false"
          class="mt-2"
        />
      </div>

      <!-- 右侧图标或内容 -->
      <div v-if="$slots.icon" class="ml-4">
        <slot name="icon" />
      </div>
    </div>
  </Card>
</template>

<script setup>
import { computed } from 'vue'
import Card from './Card.vue'
import ProgressBar from './ProgressBar.vue'

const props = defineProps({
  title: {
    type: String,
    required: true
  },
  value: {
    type: [Number, String],
    default: 0
  },
  valueColor: {
    type: String,
    default: 'default',
    validator: (value) => ['default', 'success', 'error', 'warning'].includes(value)
  },
  format: {
    type: String,
    default: 'number',
    validator: (value) => ['number', 'percentage', 'duration'].includes(value)
  },
  showProgress: {
    type: Boolean,
    default: false
  },
  progressPercent: {
    type: Number,
    default: 0
  },
  progressVariant: {
    type: String,
    default: 'default'
  },
  hoverEffect: {
    type: Boolean,
    default: false
  }
})

const formattedValue = computed(() => {
  if (typeof props.value === 'string') {
    return props.value
  }

  switch (props.format) {
    case 'percentage':
      return `${props.value}%`
    case 'duration':
      return `${props.value}s`
    default:
      return props.value.toLocaleString()
  }
})

const valueColorClass = computed(() => {
  switch (props.valueColor) {
    case 'success':
      return 'text-color-success'
    case 'error':
      return 'text-color-error'
    case 'warning':
      return 'text-color-warning'
    default:
      return 'text-text-primary'
  }
})
</script>
