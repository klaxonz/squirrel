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
  @apply p-2 rounded-lg bg-black/20 hover:bg-black/40 
    transition-colors duration-200 text-white
    focus:outline-none focus:ring-2 focus:ring-white/50;
}

.control-icon {
  @apply text-lg;
}

.settings-menu {
  @apply absolute bottom-full right-0 mb-2 w-64
    bg-black/90 backdrop-blur-sm rounded-lg p-4
    border border-white/10 shadow-xl;
}

.settings-section {
  @apply mb-4 last:mb-0;
}

.settings-title {
  @apply text-white font-medium text-sm mb-2;
}

.quality-options,
.subtitle-options {
  @apply space-y-1;
}

.quality-option,
.subtitle-option {
  @apply w-full text-left px-3 py-2 rounded text-sm
    text-white/80 hover:text-white hover:bg-white/10
    transition-colors duration-200;
}

.quality-option.active,
.subtitle-option.active {
  @apply text-white bg-white/20;
}

.setting-item {
  @apply mb-2 last:mb-0;
}

.setting-label {
  @apply flex items-center gap-2 text-sm text-white/80
    hover:text-white cursor-pointer;
}

.setting-checkbox {
  @apply w-4 h-4 rounded border-white/20 bg-transparent
    text-red-500 focus:ring-red-500 focus:ring-offset-0;
}
</style>
