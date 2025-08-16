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
            <span>{{ quality.label }}</span>
            <Icon
              v-if="currentQuality === quality.value"
              icon="material-symbols:check"
              class="check-icon"
            />
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
  @apply absolute bottom-full right-0 mb-3 w-36
    rounded-xl p-0
    border border-white/10 shadow-2xl;
  background: rgba(40, 40, 40, 0.95);
  backdrop-filter: blur(12px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6);
  transform-origin: bottom right;
  animation: menu-appear 160ms ease-out;
}

@keyframes menu-appear {
  from { opacity: 0; transform: translateY(8px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.settings-section {
  @apply p-2 last:border-b-0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.settings-title {
  @apply text-white font-medium text-xs mb-2;
  font-family: 'Roboto', 'YouTube Noto', sans-serif;
}

.quality-options,
.subtitle-options {
  @apply space-y-0.5;
}

.quality-option,
.subtitle-option {
  @apply w-full text-left px-2 py-1 rounded-lg text-xs
    text-white/90 hover:text-white hover:bg-white/10
    transition-colors duration-200;
  font-family: 'Roboto', sans-serif;
}

.quality-option { @apply flex items-center justify-between; }

.check-icon { color: #fff; font-size: 16px; }

.quality-option:hover,
.subtitle-option:hover {
  transform: none;
}

.quality-option.active,
.subtitle-option.active {
  @apply text-white;
  background: rgba(255, 255, 255, 0.12);
}

.setting-item {
  @apply mb-2 last:mb-0;
}

.setting-label {
  @apply flex items-center gap-2 text-xs text-white/80
    hover:text-white cursor-pointer transition-colors duration-200;
  font-family: 'Roboto', sans-serif;
}

.setting-checkbox {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 2px;
  border: 1px solid rgba(255, 255, 255, 0.4);
  background: transparent;
  display: inline-block;
  position: relative;
  transition: background 160ms ease, border-color 160ms ease, box-shadow 160ms ease;
}

.setting-checkbox:hover {
  border-color: rgba(255, 255, 255, 0.6);
}

.setting-checkbox:focus-visible {
  outline: 2px solid rgba(255, 255, 255, 0.3);
  outline-offset: 2px;
}

.setting-checkbox:checked {
  background-color: #cc0000;
  border-color: #cc0000;
}

.setting-checkbox:checked::after {
  content: '';
  position: absolute;
  left: 4px;
  top: 1px;
  width: 6px;
  height: 10px;
  border-right: 2px solid #fff;
  border-bottom: 2px solid #fff;
  transform: rotate(45deg);
}


</style>
