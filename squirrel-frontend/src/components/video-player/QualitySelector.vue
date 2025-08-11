<template>
  <div class="quality-selector">
    <button 
      @click="$emit('toggle-menu')" 
      class="control-btn quality-btn" 
      aria-label="视频质量"
    >
      <Icon icon="material-symbols:hd" class="control-icon" />
      <span class="quality-text">{{ currentQualityLabel }}</span>
    </button>

    <!-- 质量选择菜单 -->
    <div v-if="showMenu" class="quality-menu">
      <div class="menu-header">
        <span class="menu-title">质量</span>
      </div>
      <div class="quality-options">
        <button
          v-for="quality in availableQualities"
          :key="quality.value"
          @click="$emit('set-quality', quality.value)"
          class="quality-option"
          :class="{ active: currentQuality === quality.value }"
        >
          <span class="quality-label">{{ quality.label }}</span>
          <Icon 
            v-if="currentQuality === quality.value" 
            icon="material-symbols:check" 
            class="check-icon" 
          />
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Icon } from '@iconify/vue'

const props = defineProps({
  currentQuality: String,
  availableQualities: Array,
  showMenu: Boolean
})

const emit = defineEmits(['toggle-menu', 'set-quality'])

const currentQualityLabel = computed(() => {
  const quality = props.availableQualities?.find(q => q.value === props.currentQuality)
  return quality?.label || 'Auto'
})
</script>

<style scoped>
.quality-selector {
  @apply relative;
}

.control-btn {
  @apply p-2 rounded-full bg-transparent hover:bg-white/10 
    transition-all duration-200 text-white
    focus:outline-none focus:ring-2 focus:ring-white/30
    flex items-center justify-center gap-1;
  min-width: 40px;
  min-height: 40px;
}

.quality-btn {
  @apply px-3;
  min-width: auto;
}

.control-btn:hover {
  transform: scale(1.05);
}

.control-btn:active {
  transform: scale(0.95);
}

.control-icon {
  @apply text-lg;
  filter: drop-shadow(0 1px 2px rgba(0,0,0,0.3));
}

.quality-text {
  @apply text-xs font-medium;
  font-family: 'Roboto', sans-serif;
  text-shadow: 0 1px 2px rgba(0,0,0,0.3);
}

.quality-menu {
  @apply absolute bottom-full right-0 mb-3 w-48
    rounded-xl p-0
    border border-white/10 shadow-2xl;
  background: rgba(40, 40, 40, 0.95);
  backdrop-filter: blur(12px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6);
}

.menu-header {
  @apply p-4 border-b border-white/10;
}

.menu-title {
  @apply text-white font-medium text-sm;
  font-family: 'Roboto', 'YouTube Noto', sans-serif;
}

.quality-options {
  @apply p-2;
}

.quality-option {
  @apply w-full text-left px-3 py-2 rounded-lg text-sm
    text-white/80 hover:text-white hover:bg-white/10
    transition-all duration-200 flex items-center justify-between;
  font-family: 'Roboto', sans-serif;
}

.quality-option:hover {
  transform: translateX(2px);
}

.quality-option.active {
  @apply text-white;
  background: rgba(255, 0, 0, 0.15);
}

.quality-label {
  @apply flex-1;
}

.check-icon {
  @apply text-base;
  color: #ff0000;
}
</style>
