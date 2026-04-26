<template>
  <div class="subscription-avatar" :class="sizeClass">
    <img
      v-if="src && !hasError"
      :src="src"
      :alt="name"
      class="avatar-image"
      referrerpolicy="no-referrer"
      @error="handleError"
    >
    <div v-else class="avatar-placeholder">
      <span class="placeholder-char font-mono">{{ displayChar }}</span>
      <div class="placeholder-grid"></div>
    </div>
    <slot name="indicator"></slot>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

const props = withDefaults(defineProps<{
  src?: string | null
  name?: string
  size?: 'xs' | 'sm' | 'md' | 'lg'
}>(), {
  size: 'md'
})

const hasError = ref(false)

watch(() => props.src, () => {
  hasError.value = false
})

const handleError = () => {
  hasError.value = true
}

const displayChar = computed(() => {
  return props.name?.trim().charAt(0).toUpperCase() || '?'
})

const sizeClass = computed(() => {
  return {
    'avatar--xs': props.size === 'xs',
    'avatar--sm': props.size === 'sm',
    'avatar--md': props.size === 'md',
    'avatar--lg': props.size === 'lg',
  }
})
</script>

<style scoped>
.subscription-avatar {
  position: relative;
  overflow: hidden;
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border-radius: calc(var(--radius-sm) - 1px);
}

.avatar--xs { width: 1.25rem; height: 1.25rem; }
.avatar--sm { width: 1.5rem; height: 1.5rem; }
.avatar--md { width: 1.75rem; height: 1.75rem; }
.avatar--lg { width: 2rem; height: 2rem; }

.avatar-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  filter: grayscale(0.4);
  transition: filter var(--duration-normal) var(--ease-default);
}

.subscription-avatar:hover .avatar-image {
  filter: grayscale(0);
}

.avatar-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: hsl(var(--muted) / 0.5);
  position: relative;
}

.placeholder-char {
  font-weight: 900;
  font-size: 0.7em;
  color: hsl(var(--foreground) / 0.2);
  z-index: 1;
  letter-spacing: -0.05em;
}

.placeholder-grid {
  position: absolute;
  inset: 0;
  background-image: 
    linear-gradient(hsl(var(--foreground) / 0.03) 1px, transparent 1px),
    linear-gradient(90deg, hsl(var(--foreground) / 0.03) 1px, transparent 1px);
  background-size: 4px 4px;
}

.avatar--xs .placeholder-char { font-size: 0.6em; }
.avatar--lg .placeholder-char { font-size: 0.8em; }
</style>
