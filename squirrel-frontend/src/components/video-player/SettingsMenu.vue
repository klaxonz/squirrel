<template>
  <div class="settings-control">
    <button 
      @click="$emit('toggle-menu')" 
      class="control-btn" 
      aria-label="设置"
    >
      <Icon icon="material-symbols:settings" class="control-icon" />
    </button>

    <!-- 设置菜单 -->
    <div v-if="showMenu" class="settings-menu">
      <!-- 播放质量设置 -->
      <div class="settings-section">
        <div class="settings-title">播放质量</div>
        <div class="quality-options">
          <button
            v-for="quality in availableQualities"
            :key="quality.value"
            @click="$emit('set-quality', quality.value)"
            class="quality-option"
            :class="{ active: currentQuality === quality.value }"
          >
            {{ quality.label }}
          </button>
        </div>
      </div>

      <!-- 字幕设置 -->
      <div class="settings-section" v-if="subtitles && subtitles.length > 0">
        <div class="settings-title">字幕</div>
        <div class="subtitle-options">
          <button
            @click="$emit('set-subtitle', null)"
            class="subtitle-option"
            :class="{ active: !currentSubtitle }"
          >
            关闭
          </button>
          <button
            v-for="subtitle in subtitles"
            :key="subtitle.id"
            @click="$emit('set-subtitle', subtitle)"
            class="subtitle-option"
            :class="{ active: currentSubtitle?.id === subtitle.id }"
          >
            {{ subtitle.language }}
          </button>
        </div>
      </div>

      <!-- 其他设置 -->
      <div class="settings-section">
        <div class="settings-title">其他设置</div>
        
        <div class="setting-item">
          <label class="setting-label">
            <input
              type="checkbox"
              :checked="autoplay"
              @change="$emit('update-autoplay', $event.target.checked)"
              class="setting-checkbox"
            >
            自动播放
          </label>
        </div>
        
        <div class="setting-item">
          <label class="setting-label">
            <input
              type="checkbox"
              :checked="loop"
              @change="$emit('update-loop', $event.target.checked)"
              class="setting-checkbox"
            >
            循环播放
          </label>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Icon } from '@iconify/vue'

const props = defineProps({
  showMenu: Boolean,
  currentQuality: String,
  availableQualities: Array,
  currentSubtitle: Object,
  subtitles: Array,
  autoplay: Boolean,
  loop: Boolean
})

const emit = defineEmits([
  'toggle-menu',
  'set-quality',
  'set-subtitle',
  'update-autoplay',
  'update-loop'
])
</script>

<style scoped>
.settings-control {
  @apply relative;
}

.control-btn {
  @apply p-2 rounded-full bg-transparent hover:bg-white/10
    transition-all duration-200 text-white
    focus:outline-none focus:ring-2 focus:ring-white/30
    flex items-center justify-center;
  min-width: 40px;
  min-height: 40px;
}

.control-btn:hover {
  transform: scale(1.05);
}

.control-btn:active {
  transform: scale(0.95);
}

.control-icon {
  @apply text-xl;
  filter: drop-shadow(0 1px 2px rgba(0,0,0,0.3));
}

.settings-menu {
  @apply absolute bottom-full right-0 mb-3 w-72
    rounded-xl p-0
    border border-white/10 shadow-2xl;
  background: rgba(40, 40, 40, 0.95);
  backdrop-filter: blur(12px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6);
}

.settings-section {
  @apply p-4 border-b border-white/10 last:border-b-0;
}

.settings-title {
  @apply text-white font-medium text-sm mb-3;
  font-family: 'Roboto', 'YouTube Noto', sans-serif;
}

.quality-options,
.subtitle-options {
  @apply space-y-1;
}

.quality-option,
.subtitle-option {
  @apply w-full text-left px-3 py-2 rounded-lg text-sm
    text-white/80 hover:text-white hover:bg-white/10
    transition-all duration-200;
  font-family: 'Roboto', sans-serif;
}

.quality-option:hover,
.subtitle-option:hover {
  transform: translateX(2px);
}

.quality-option.active,
.subtitle-option.active {
  @apply text-white;
  background: rgba(255, 0, 0, 0.15);
  border-left: 3px solid #ff0000;
}

.setting-item {
  @apply mb-3 last:mb-0;
}

.setting-label {
  @apply flex items-center gap-3 text-sm text-white/80
    hover:text-white cursor-pointer transition-colors duration-200;
  font-family: 'Roboto', sans-serif;
}

.setting-checkbox {
  @apply w-4 h-4 rounded border-white/30 bg-transparent
    focus:ring-2 focus:ring-white/30 focus:ring-offset-0
    transition-all duration-200;
  accent-color: #ff0000;
}

.setting-checkbox:checked {
  background-color: #ff0000;
  border-color: #ff0000;
}
</style>
