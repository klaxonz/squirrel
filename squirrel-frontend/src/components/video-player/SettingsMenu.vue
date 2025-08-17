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

      <!-- 字幕选择 -->
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

      <!-- 字幕样式 -->
      <div class="settings-section">
        <div class="settings-title">字幕样式</div>
        <div class="setting-item-row">
          <span class="setting-label">字号</span>
          <div class="btn-group">
            <button class="btn-chip" :class="{ active: subtitleSettings?.fontSize==='small' }" @click="$emit('update-subtitle-font-size','small')">小</button>
            <button class="btn-chip" :class="{ active: subtitleSettings?.fontSize==='medium' }" @click="$emit('update-subtitle-font-size','medium')">中</button>
            <button class="btn-chip" :class="{ active: subtitleSettings?.fontSize==='large' }" @click="$emit('update-subtitle-font-size','large')">大</button>
            <button class="btn-chip" :class="{ active: subtitleSettings?.fontSize==='xlarge' }" @click="$emit('update-subtitle-font-size','xlarge')">特大</button>
          </div>
        </div>
        <div class="setting-item-row">
          <span class="setting-label">颜色</span>
          <div class="btn-group">
            <button class="btn-chip" :class="{ active: subtitleSettings?.color==='white' }" @click="$emit('update-subtitle-color','white')">白色</button>
            <button class="btn-chip" :class="{ active: subtitleSettings?.color==='yellow' }" @click="$emit('update-subtitle-color','yellow')">黄色</button>
          </div>
        </div>
        <div class="setting-item-row">
          <span class="setting-label">背景</span>
          <input class="range" type="range" min="0" max="1" step="0.1" :value="subtitleSettings?.bgOpacity ?? 0.4" @input="$emit('update-subtitle-bg-opacity', Number($event.target.value))" />
        </div>
        <div class="setting-item-row">
          <span class="setting-label">位置</span>
          <div class="btn-group">
            <button class="btn-chip" :class="{ active: subtitleSettings?.position==='bottom' }" @click="$emit('update-subtitle-position','bottom')">底部</button>
            <button class="btn-chip" :class="{ active: subtitleSettings?.position==='top' }" @click="$emit('update-subtitle-position','top')">顶部</button>
          </div>
        </div>
        <div class="setting-item-row">
          <label class="setting-label">
            <input type="checkbox" :checked="subtitleSettings?.shadow" @change="$emit('update-subtitle-shadow', $event.target.checked)" class="setting-checkbox" />
            阴影
          </label>
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
  subtitleSettings: Object,
  autoplay: Boolean,
  loop: Boolean
})

const emit = defineEmits([
  'toggle-menu',
  'set-quality',
  'set-subtitle',
  'update-subtitle-font-size',
  'update-subtitle-color',
  'update-subtitle-bg-opacity',
  'update-subtitle-position',
  'update-subtitle-shadow',
  'update-autoplay',
  'update-loop'
])
</script>

<style scoped>
.settings-control { position: relative; }
.control-btn { padding: 0.5rem; border-radius: 9999px; background: transparent; color: #fff; min-width: 40px; min-height: 40px; display: flex; align-items: center; justify-content: center; transition: all .2s; }
.control-btn:hover { transform: scale(1.05); background: rgba(255,255,255,.1); }
.control-btn:active { transform: scale(0.95); }
.control-icon { font-size: 1.25rem; filter: drop-shadow(0 1px 2px rgba(0,0,0,0.3)); }
.settings-menu { position: absolute; bottom: 100%; right: 0; margin-bottom: 0.75rem; width: 14rem; border-radius: 0.75rem; padding: 0; border: 1px solid rgba(255,255,255,.1); background: rgba(40,40,40,.95); backdrop-filter: blur(12px); box-shadow: 0 8px 32px rgba(0,0,0,.6); transform-origin: bottom right; animation: menu-appear 160ms ease-out; }
@keyframes menu-appear { from { opacity: 0; transform: translateY(8px) scale(0.98);} to { opacity: 1; transform: translateY(0) scale(1);} }
.settings-section { padding: 0.5rem; border-bottom: 1px solid rgba(255,255,255,.08); }
.settings-title { color: #fff; font-weight: 500; font-size: 12px; margin-bottom: 0.5rem; font-family: 'Roboto', 'YouTube Noto', sans-serif; }
.quality-options, .subtitle-options { display: grid; grid-auto-rows: minmax(28px,auto); gap: 6px; }
.subtitle-option { width: 100%; text-align: left; padding: 6px 8px; border-radius: 8px; color: #eaeaea; background: transparent; border: none; cursor: pointer; }
.subtitle-option.active, .subtitle-option:hover { background: rgba(255,255,255,.08); }

.setting-item { margin: 6px 0; }
.setting-item-row { margin: 6px 0; display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.setting-label { color: #eaeaea; font-size: 12px; display: flex; align-items: center; gap: 8px; }
.setting-checkbox { width: 14px; height: 14px; }
.btn-group { display: flex; gap: 6px; }
.btn-chip { padding: 4px 8px; border-radius: 9999px; border: 1px solid rgba(255,255,255,.14); background: transparent; color: #eaeaea; font-size: 12px; cursor: pointer; }
.btn-chip.active, .btn-chip:hover { background: rgba(255,255,255,.08); }
.range { width: 100%; }

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
