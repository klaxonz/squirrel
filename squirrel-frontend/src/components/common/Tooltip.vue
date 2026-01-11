<template>
  <div class="tooltip-wrapper" @mouseenter="showTooltip" @mouseleave="hideTooltip">
    <slot />
    <transition name="tooltip-fade">
      <div
        v-if="visible && text"
        class="tooltip-content"
        :class="placement"
        :style="positionStyle"
      >
        {{ text }}
        <div class="tooltip-arrow" :class="arrowClass"></div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  text: {
    type: String,
    default: ''
  },
  placement: {
    type: String,
    default: 'right',
    validator: (value) => ['top', 'bottom', 'left', 'right'].includes(value)
  },
  delay: {
    type: Number,
    default: 300
  },
  offset: {
    type: Number,
    default: 8
  }
})

const visible = ref(false)
const timer = ref(null)
const wrapperRef = ref(null)

const showTooltip = () => {
  if (!props.text) return
  timer.value = setTimeout(() => {
    visible.value = true
  }, props.delay)
}

const hideTooltip = () => {
  if (timer.value) {
    clearTimeout(timer.value)
    timer.value = null
  }
  visible.value = false
}

const arrowClass = computed(() => {
  return `arrow-${props.placement}`
})

const positionStyle = computed(() => {
  return {
    '--tooltip-offset': `${props.offset}px`
  }
})

onUnmounted(() => {
  if (timer.value) {
    clearTimeout(timer.value)
  }
})
</script>

<style scoped>
.tooltip-wrapper {
  position: relative;
  display: flex;
  width: 100%;
}

.tooltip-content {
  position: absolute;
  z-index: 1000;
  padding: 0.375rem 0.625rem;
  font-size: var(--font-size-2xs);
  line-height: 1;
  color: var(--text-primary);
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-primary);
  border-radius: 0.375rem;
  white-space: nowrap;
  pointer-events: none;
  box-shadow: var(--shadow-md);
}

.tooltip-content.right {
  left: calc(100% + var(--tooltip-offset));
  top: 50%;
  transform: translateY(-50%);
}

.tooltip-content.left {
  right: calc(100% + var(--tooltip-offset));
  top: 50%;
  transform: translateY(-50%);
}

.tooltip-content.top {
  bottom: calc(100% + var(--tooltip-offset));
  left: 50%;
  transform: translateX(-50%);
}

.tooltip-content.bottom {
  top: calc(100% + var(--tooltip-offset));
  left: 50%;
  transform: translateX(-50%);
}

.tooltip-arrow {
  position: absolute;
  width: 0.375rem;
  height: 0.375rem;
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-primary);
}

.arrow-right {
  right: 100%;
  top: 50%;
  transform: translateY(-50%) rotate(45deg);
  border-right: none;
  border-bottom: none;
}

.arrow-left {
  left: 100%;
  top: 50%;
  transform: translateY(-50%) rotate(45deg);
  border-left: none;
  border-top: none;
}

.arrow-top {
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%) rotate(45deg);
  border-top: none;
  border-right: none;
}

.arrow-bottom {
  top: 100%;
  left: 50%;
  transform: translateX(-50%) rotate(45deg);
  border-bottom: none;
  border-left: none;
}

.tooltip-fade-enter-active,
.tooltip-fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.tooltip-fade-enter-from,
.tooltip-fade-leave-to {
  opacity: 0;
}

.tooltip-fade-enter-from.right,
.tooltip-fade-leave-to.right {
  transform: translateY(-50%) translateX(-4px);
}

.tooltip-fade-enter-from.left,
.tooltip-fade-leave-to.left {
  transform: translateY(-50%) translateX(4px);
}

.tooltip-fade-enter-from.top,
.tooltip-fade-leave-to.top {
  transform: translateX(-50%) translateY(4px);
}

.tooltip-fade-enter-from.bottom,
.tooltip-fade-leave-to.bottom {
  transform: translateX(-50%) translateY(-4px);
}
</style>
