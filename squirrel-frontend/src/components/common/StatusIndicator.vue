<template>
  <div class="status-indicator inline-flex items-center">
    <!-- 图标 -->
    <component
      :is="iconComponent"
      :class="[
        'status-icon w-4 h-4 mr-1.5 flex-shrink-0',
        iconColorClass
      ]"
    />

    <!-- 文本 -->
    <span :class="['status-text text-sm', textColorClass]">
      {{ statusText }}
    </span>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
  PauseCircleIcon
} from '@heroicons/vue/24/outline'

const props = defineProps({
  status: {
    type: String,
    required: true,
    validator: (value) => [
      'healthy', 'degraded', 'critical', 'unknown'
    ].includes(value)
  }
})

const statusConfig = {
  healthy: {
    icon: CheckCircleIcon,
    text: '正常',
    textColor: 'text-color-success',
    iconColor: 'text-color-success'
  },
  degraded: {
    icon: ExclamationTriangleIcon,
    text: '降级',
    textColor: 'text-color-warning',
    iconColor: 'text-color-warning'
  },
  critical: {
    icon: ExclamationTriangleIcon,
    text: '异常',
    textColor: 'text-color-error',
    iconColor: 'text-color-error'
  },
  unknown: {
    icon: ExclamationTriangleIcon,
    text: '未知',
    textColor: 'text-text-tertiary',
    iconColor: 'text-text-tertiary'
  }
}

const config = computed(() => statusConfig[props.status] || statusConfig.unknown)

const iconComponent = computed(() => config.value.icon)
const statusText = computed(() => config.value.text)
const textColorClass = computed(() => config.value.textColor)
const iconColorClass = computed(() => config.value.iconColor)
</script>
