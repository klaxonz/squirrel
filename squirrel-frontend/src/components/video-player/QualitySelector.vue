<template>
  <div class="quality-selector">
    <button 
      @click.stop="$emit('toggle-menu')" 
      class="control-btn quality-btn" 
      aria-label="视频质量"
    >
      <Icon icon="material-symbols:hd" class="control-icon" />
      <span class="quality-text">{{ currentQualityLabel }}</span>
    </button>

    <!-- 质量选择菜单 -->
    <div v-if="showMenu" class="quality-menu" @click.stop>
      <div class="menu-header">
        <span class="menu-title">清晰度</span>
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
          <span class="check-icon-container">
            <Icon 
              v-if="currentQuality === quality.value" 
              icon="material-symbols:check" 
              class="check-icon" 
            />
          </span>
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
  return quality?.label || (props.availableQualities?.[0]?.label || 'HD')
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
  position: absolute;
  bottom: 100%;
  right: 0;
  margin-bottom: 0.75rem;
  min-width: 8rem;
  width: auto;
  border-radius: 0.75rem;
  padding: 0;
  border: 1px solid rgba(255, 255, 255, .1);
  background: rgba(40, 40, 40, .95);
  backdrop-filter: blur(12px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, .6);
  transform-origin: bottom right;
  animation: menu-appear 160ms ease-out;
  font-size: 12px;
  line-height: 1.25;
}

@keyframes menu-appear {
  from {
    opacity: 0;
    transform: translateY(8px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.menu-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-bottom: 1px solid rgba(255, 255, 255, .08);
}

.menu-title {
  color: #fff;
  font-size: 12px;
  font-weight: 500;
  font-family: 'Roboto', 'YouTube Noto', sans-serif;
}

.quality-options {
  display: flex;
  flex-direction: column;
  padding: 6px;
  gap: 4px;
}

.quality-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  border-radius: 8px;
  color: #eaeaea;
  background: transparent;
  border: none;
  cursor: pointer;
  transition: background .15s ease, color .15s ease;
  font-family: 'Roboto', sans-serif;
  font-size: 12px;
  min-height: 32px;
}

.quality-option:hover {
  background: rgba(255, 255, 255, .08);
}

.quality-option.active {
  background: rgba(255, 255, 255, .12);
  color: #fff;
}

.quality-label {
  flex: 1;
  text-align: left;
}

.check-icon-container {
  width: 20px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.check-icon {
  font-size: 16px;
  color: #fff;
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
