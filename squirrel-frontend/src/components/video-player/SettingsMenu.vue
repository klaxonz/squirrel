<template>
  <div class="settings-control">
    <button
        @click.stop="$emit('toggle-menu')"
        class="control-btn"
        aria-label="设置"
    >
      <Icon icon="material-symbols:settings" class="control-icon"/>
    </button>

    <div v-if="showMenu" class="settings-menu" @click.stop>
      <!-- 主菜单 -->
      <div v-if="activePanel==='main'" class="menu-panel">
        <div class="menu-list">
          <button class="menu-item" @click="activePanel='subtitles'">
            <span class="item-left">
              <Icon icon="material-symbols:subtitles" class="item-icon"/>
              <span>字幕</span>
            </span>
            <span class="item-right"><span>{{ currentSubtitleLabel }}</span><Icon icon="material-symbols:chevron-right"/></span>
          </button>

          <button v-if="availableQualities && availableQualities.length>0" class="menu-item"
                  @click="activePanel='quality'">
            <span class="item-left">
              <Icon icon="material-symbols:high-quality" class="item-icon"/>
              <span>播放质量</span>
            </span>
            <span class="item-right"><span>{{ currentQualityLabel }}</span><Icon icon="material-symbols:chevron-right"/></span>
          </button>


          <button class="menu-item" @click="activePanel='playback-rate'">
            <span class="item-left">
              <Icon icon="material-symbols:speed" class="item-icon"/>
              <span>播放速度</span>
            </span>
            <span class="item-right"><span>{{ currentRateLabel }}</span><Icon icon="material-symbols:chevron-right"/></span>
          </button>

          <div class="menu-item toggled">
            <span class="item-left">自动播放</span>
            <label class="yt-switch">
              <input type="checkbox" :checked="autoplay" @change="$emit('update-autoplay', $event.target.checked)"/>
              <span class="slider"></span>
            </label>
          </div>

          <div class="menu-item toggled">
            <span class="item-left">循环播放</span>
            <label class="yt-switch">
              <input type="checkbox" :checked="loop" @change="$emit('update-loop', $event.target.checked)"/>
              <span class="slider"></span>
            </label>
          </div>
        </div>
      </div>

      <!-- 字幕选择子菜单 -->
      <div v-else-if="activePanel==='subtitles'" class="menu-panel">
        <div class="menu-header">
          <button class="back-btn" @click="activePanel='main'">
            <Icon icon="material-symbols:arrow-back-ios-new"/>
          </button>
          <span class="header-title">字幕</span>
        </div>
        <div class="menu-list">
          <button class="menu-item" :class="{ active: !currentSubtitle }" @click="$emit('set-subtitle', null)">
            <span class="item-left">关闭</span>
            <Icon v-if="!currentSubtitle" icon="material-symbols:check" class="check-icon"/>
          </button>
          <button
              v-for="subtitle in subtitles"
              :key="subtitle.id"
              class="menu-item"
              :class="{ active: currentSubtitle?.id === subtitle.id }"
              @click="$emit('set-subtitle', subtitle)"
          >
            <span class="item-left">{{ subtitle.language }}</span>
            <Icon v-if="currentSubtitle?.id === subtitle.id" icon="material-symbols:check" class="check-icon"/>
          </button>

          <button class="menu-item" @click="activePanel='subtitle-style'">
            <span class="item-left">选项</span>
            <Icon icon="material-symbols:chevron-right"/>
          </button>
        </div>
      </div>

      <!-- 字幕样式子菜单 -->
      <div v-else-if="activePanel==='subtitle-style'" class="menu-panel">
        <div class="menu-header">
          <button class="back-btn" @click="activePanel='subtitles'">
            <Icon icon="material-symbols:arrow-back-ios-new"/>
          </button>
          <span class="header-title">字幕选项</span>
        </div>
        <div class="menu-content">
          <div class="setting-item-row">
            <span class="setting-label">字号</span>
            <div class="btn-group">
              <button class="btn-chip" :class="{ active: subtitleSettings?.fontSize==='small' }"
                      @click="$emit('update-subtitle-font-size','small')">小
              </button>
              <button class="btn-chip" :class="{ active: subtitleSettings?.fontSize==='medium' }"
                      @click="$emit('update-subtitle-font-size','medium')">中
              </button>
              <button class="btn-chip" :class="{ active: subtitleSettings?.fontSize==='large' }"
                      @click="$emit('update-subtitle-font-size','large')">大
              </button>
              <button class="btn-chip" :class="{ active: subtitleSettings?.fontSize==='xlarge' }"
                      @click="$emit('update-subtitle-font-size','xlarge')">特大
              </button>
            </div>
          </div>
          <div class="setting-item-row">
            <span class="setting-label">颜色</span>
            <div class="btn-group">
              <button class="btn-chip" :class="{ active: subtitleSettings?.color==='white' }"
                      @click="$emit('update-subtitle-color','white')">白色
              </button>
              <button class="btn-chip" :class="{ active: subtitleSettings?.color==='yellow' }"
                      @click="$emit('update-subtitle-color','yellow')">黄色
              </button>
            </div>
          </div>
          <div class="setting-item-row">
            <span class="setting-label">背景</span>
            <input class="range" type="range" min="0" max="1" step="0.1" :value="subtitleSettings?.bgOpacity ?? 0.4"
                   @input="$emit('update-subtitle-bg-opacity', Number($event.target.value))"/>
          </div>
          <div class="setting-item-row">
            <span class="setting-label">位置</span>
            <div class="btn-group">
              <button class="btn-chip" :class="{ active: subtitleSettings?.position==='bottom' }"
                      @click="$emit('update-subtitle-position','bottom')">底部
              </button>
              <button class="btn-chip" :class="{ active: subtitleSettings?.position==='top' }"
                      @click="$emit('update-subtitle-position','top')">顶部
              </button>
            </div>
          </div>
          <div class="setting-item-row">
            <label class="setting-label">
              <input type="checkbox" :checked="subtitleSettings?.shadow"
                     @change="$emit('update-subtitle-shadow', $event.target.checked)" class="setting-checkbox"/>
              阴影
            </label>
          </div>
        </div>
      </div>

      <!-- 画质子菜单 -->
      <div v-else-if="activePanel==='quality'" class="menu-panel">
        <div class="menu-header">
          <button class="back-btn" @click="activePanel='main'">
            <Icon icon="material-symbols:arrow-back-ios-new"/>
          </button>
          <span class="header-title">播放质量</span>
        </div>
        <div class="menu-list">
          <button
              v-for="quality in availableQualities"
              :key="quality.value"
              class="menu-item"
              :class="{ active: currentQuality === quality.value }"
              @click="$emit('set-quality', quality.value)"
          >
            <span class="item-left">{{ quality.label }}</span>
            <Icon v-if="currentQuality === quality.value" icon="material-symbols:check" class="check-icon"/>
          </button>
        </div>
      </div>

      <!-- 播放速度子菜单 -->
      <div v-else-if="activePanel==='playback-rate'" class="menu-panel">
        <div class="menu-header">
          <button class="back-btn" @click="activePanel='main'">
            <Icon icon="material-symbols:arrow-back-ios-new"/>
          </button>
          <span class="header-title">播放速度</span>
        </div>
        <div class="menu-list">
          <button
            v-for="rate in (availableRates || [])"
            :key="String(rate)"
            class="menu-item"
            :class="{ active: Number(currentRate) === Number(rate) }"
            @click="$emit('set-playback-rate', rate)"
          >
            <span class="item-left">{{ Number(rate) === 1 ? '正常' : rate + 'x' }}</span>
            <Icon v-if="Number(currentRate) === Number(rate)" icon="material-symbols:check" class="check-icon"/>
          </button>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import {computed, ref, watch} from 'vue'
import {Icon} from '@iconify/vue'

const props = defineProps({
  showMenu: Boolean,
  initialPanel: {type: String, default: 'main'},
  currentQuality: String,
  availableQualities: Array,
  currentSubtitle: Object,
  subtitles: Array,
  subtitleSettings: Object,
  autoplay: Boolean,
  loop: Boolean,
  currentRate: [Number, String],
  availableRates: Array
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
  'update-loop',
  'set-playback-rate'
])

const currentRateLabel = computed(() => {
  const r = Number(props.currentRate)
  if (!r || isNaN(r)) return '正常'
  return r === 1 ? '正常' : r + 'x'
})

// 分级菜单状态
const activePanel = ref('main')

watch(() => props.showMenu, (val) => {
  if (val) activePanel.value = props.initialPanel || 'main'
})

// 文案
const currentSubtitleLabel = computed(() => {
  if (!props.currentSubtitle) return '关闭'
  return props.currentSubtitle.language || '未知'
})

const currentQualityLabel = computed(() => {
  const found = (props.availableQualities || []).find(q => q.value === props.currentQuality)
  return found?.label || (props.availableQualities?.[0]?.label)
})
</script>

<style scoped>
.settings-control {
  position: relative;
}

.control-btn {
  padding: 0.5rem;
  border-radius: 9999px;
  background: transparent;
  min-width: 40px;
  min-height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all .2s;
}

/* Remove default focus ring to avoid white border flash on click */
.control-btn { outline: none; }
.control-btn:focus { outline: none; box-shadow: none; }
.control-btn:focus-visible { outline: none; box-shadow: none; }
.control-btn::-moz-focus-inner { border: 0; }


.control-btn:hover {
  transform: scale(1.05);
  background: rgba(255, 255, 255, .1);
}

.control-btn:active {
  transform: scale(0.95);
}

.control-icon {
  font-size: 1.25rem;
  filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.3));
}

.settings-menu {
  position: absolute;
  bottom: 100%;
  right: 0;
  margin-bottom: 0.75rem;
  width: 16rem;
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

.setting-item-row {
  margin: 6px 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.setting-label {
  color: #eaeaea;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.setting-checkbox {
  width: 14px;
  height: 14px;
}

.btn-group {
  display: flex;
  gap: 6px;
}

.btn-chip {
  padding: 4px 8px;
  border-radius: 9999px;
  border: 1px solid rgba(255, 255, 255, .14);
  background: transparent;
  color: #eaeaea;
  font-size: 12px;
  cursor: pointer;
}

.btn-chip.active, .btn-chip:hover {
  background: rgba(255, 255, 255, .08);
}

.range {
  width: 100%;
}


.check-icon {
  color: #fff;
  font-size: 16px;
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

.menu-panel {
  width: 100%;
}

.menu-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-bottom: 1px solid rgba(255, 255, 255, .08);
}

.back-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 9999px;
  color: #fff;
  background: transparent;
}

.back-btn:hover {
  background: rgba(255, 255, 255, .08);
}

.header-title {
  color: #fff;
  font-size: 12px;
  font-weight: 500;
}

.menu-list {
  display: flex;
  flex-direction: column;
  padding: 6px;
  gap: 4px;
}

.menu-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 8px;
  color: #eaeaea;
  background: transparent;
  border: none;
  cursor: pointer;
  transition: background .15s ease, color .15s ease;
}

.menu-item:hover {
  background: rgba(255, 255, 255, .08);
}

.menu-item.active {
  background: rgba(255, 255, 255, .12);
  color: #fff;
}

.menu-item.toggled {
  cursor: default;
}

.menu-item.toggled:hover {
  background: transparent;
}

.item-left {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.item-right {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: #9aa0a6;
  font-size: 11px;
}

.item-icon {
  font-size: 16px;
}

.menu-content {
  padding: 8px 10px;
}

.yt-switch {
  position: relative;
  display: inline-block;
  width: 34px;
  height: 18px;
}

.yt-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.yt-switch .slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, .2);
  transition: .2s;
  border-radius: 9999px;
}

.yt-switch .slider:before {
  position: absolute;
  content: "";
  height: 14px;
  width: 14px;
  left: 2px;
  top: 2px;
  background-color: #fff;
  transition: .2s;
  border-radius: 9999px;
}

.yt-switch input:checked + .slider {
  background: #cc0000;
}

.yt-switch input:checked + .slider:before {
  transform: translateX(16px);
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
