<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="isOpen" class="modal-overlay" @click.self="close">
        <div class="modal-panel" role="dialog" aria-label="筛选">
          <!-- Header -->
          <div class="modal-header">
            <span class="modal-title">筛选</span>
            <button class="modal-close" @click="close" aria-label="关闭">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M18 6L6 18M6 6l12 12" stroke-linecap="round" />
              </svg>
            </button>
          </div>

          <div class="modal-body">
            <!-- 排序 -->
            <div v-if="scope === 'video'" class="filter-section">
              <div class="filter-section-title">排序</div>
              <div class="filter-chips">
                <button
                  v-for="opt in sortOptions"
                  :key="opt.value"
                  class="filter-chip"
                  :class="{ 'is-selected': localSortBy === opt.value }"
                  @click="localSortBy = opt.value"
                >
                  {{ opt.label }}
                </button>
              </div>
            </div>

            <!-- 上传日期 -->
            <div v-if="scope === 'video'" class="filter-section">
              <div class="filter-section-title">上传日期</div>
              <div class="filter-chips">
                <button
                  v-for="opt in timeRangeOptions"
                  :key="opt.value"
                  class="filter-chip"
                  :class="{ 'is-selected': localTimeRange === opt.value }"
                  @click="localTimeRange = opt.value"
                >
                  {{ opt.label }}
                </button>
              </div>
            </div>

            <!-- 时长 -->
            <div v-if="scope === 'video'" class="filter-section">
              <div class="filter-section-title">时长</div>
              <div class="filter-chips">
                <button
                  v-for="opt in durationOptions"
                  :key="opt.value"
                  class="filter-chip"
                  :class="{ 'is-selected': localDuration === opt.value }"
                  @click="localDuration = opt.value"
                >
                  {{ opt.label }}
                </button>
              </div>
            </div>

            <!-- 类型 -->
            <div v-if="scope === 'video' && !subscriptionId" class="filter-section">
              <div class="filter-section-title">类型</div>
              <div class="filter-chips">
                <button
                  v-for="opt in contentTypeOptions"
                  :key="opt.value"
                  class="filter-chip"
                  :class="{ 'is-selected': localContentType === opt.value }"
                  @click="localContentType = opt.value"
                >
                  {{ opt.label }}
                </button>
              </div>
            </div>

            <!-- 敏感内容 -->
            <div v-if="settings.showNsfw" class="filter-section">
              <div class="filter-section-title">敏感内容</div>
              <div class="filter-chips">
                <button
                  v-for="opt in nsfwOptions"
                  :key="opt.value"
                  class="filter-chip"
                  :class="{ 'is-selected': localNsfw === opt.value }"
                  @click="localNsfw = opt.value"
                >
                  {{ opt.label }}
                </button>
              </div>
            </div>

            <!-- 站点 -->
            <div v-if="!subscriptionId" class="filter-section">
              <div class="filter-section-title">站点</div>
              <div class="filter-chips">
                <button
                  class="filter-chip"
                  :class="{ 'is-selected': !localSite }"
                  @click="clearSite"
                >
                  全部
                </button>
                <button
                  v-for="opt in siteOptions"
                  :key="opt.value"
                  class="filter-chip"
                  :class="{ 'is-selected': localSite === opt.value }"
                  @click="selectSite(opt)"
                >
                  {{ opt.label }}
                </button>
              </div>
            </div>

          </div>

          <!-- Footer -->
          <div class="modal-footer">
            <button class="modal-btn modal-btn--reset" @click="resetAll">重置</button>
            <button class="modal-btn modal-btn--confirm" @click="confirm">确定</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useUserSettings } from '@/composables/useUserSettings'
import { useSites } from '@/composables/useSites'
import type { TimeRange, Duration, ContentType } from '@/composables/useFeedFilters'

const props = withDefaults(defineProps<{
  modelValue: boolean
  timeRange: TimeRange
  duration: Duration
  contentType: ContentType
  nsfw: string
  site?: string
  subscriptionId?: string | number
  siteLabel?: string
  sortBy: string
  /** 'video' shows all feed filters; 'subscription' shows only nsfw/site */
  scope?: 'video' | 'subscription'
}>(), {
  scope: 'video',
})

const emit = defineEmits<{
  'update:modelValue': [v: boolean]
  'update:timeRange': [v: TimeRange]
  'update:duration': [v: Duration]
  'update:contentType': [v: ContentType]
  'update:nsfw': [v: string]
  'update:site': [v: string | undefined]
  'update:sortBy': [v: string]
}>()

const { settings } = useUserSettings()
const { options: siteOptions, fetchSites } = useSites()

const localTimeRange = ref<TimeRange>(props.timeRange)
const localDuration = ref<Duration>(props.duration)
const localContentType = ref<ContentType>(props.contentType)
const localNsfw = ref(props.nsfw)
const localSite = ref(props.site)
const siteLabel = ref(props.siteLabel)
const localSortBy = ref(props.sortBy)

watch(() => props.modelValue, (open) => {
  if (open) {
    localTimeRange.value = props.timeRange
    localDuration.value = props.duration
    localContentType.value = props.contentType
    localNsfw.value = props.nsfw
    localSite.value = props.site
    siteLabel.value = props.siteLabel
    localSortBy.value = props.sortBy
  }
})

const isOpen = computed(() => props.modelValue)
const close = () => emit('update:modelValue', false)
const confirm = () => {
  emit('update:timeRange', localTimeRange.value)
  emit('update:duration', localDuration.value)
  emit('update:contentType', localContentType.value)
  emit('update:nsfw', localNsfw.value)
  emit('update:site', localSite.value)
  emit('update:sortBy', localSortBy.value)
  emit('update:modelValue', false)
}

const clearSite = () => {
  localSite.value = undefined
  siteLabel.value = undefined
}

const selectSite = (opt: { value: string; label: string }) => {
  localSite.value = opt.value
  siteLabel.value = opt.label
}

const resetAll = () => {
  localTimeRange.value = 'all'
  localDuration.value = 'all'
  localContentType.value = 'all'
  localNsfw.value = 'all'
  localSortBy.value = 'publish_date'
  clearSite()
}

watch(() => props.modelValue, (open) => {
  document.body.style.overflow = open ? 'hidden' : ''
})

const handleKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Escape' && props.modelValue) close()
}
onMounted(async () => {
  document.addEventListener('keydown', handleKeydown)
  if (!siteOptions.value) {
    await fetchSites()
  }
})
onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
  document.body.style.overflow = ''
})

const timeRangeOptions = [
  { value: 'all' as TimeRange, label: '不限' },
  { value: 'today' as TimeRange, label: '今天' },
  { value: 'week' as TimeRange, label: '本周' },
  { value: 'month' as TimeRange, label: '本月' },
  { value: 'year' as TimeRange, label: '本年' },
]

const durationOptions = [
  { value: 'all' as Duration, label: '不限' },
  { value: 'short' as Duration, label: '不到 4 分钟' },
  { value: 'medium' as Duration, label: '4 - 20 分钟' },
  { value: 'long' as Duration, label: '超过 20 分钟' },
]

const contentTypeOptions = [
  { value: 'all' as ContentType, label: '不限' },
  { value: 'CHANNEL' as ContentType, label: '频道' },
  { value: 'PLAYLIST' as ContentType, label: '播放列表' },
  { value: 'ACTRESS' as ContentType, label: '女優' },
  { value: 'MOVIE' as ContentType, label: '电影' },
  { value: 'TV_SERIES' as ContentType, label: '剧集' },
  { value: 'ACTOR' as ContentType, label: '演员' },
]

const nsfwOptions = [
  { value: 'all', label: '不限' },
  { value: 'yes', label: '仅 NSFW' },
  { value: 'no', label: '仅安全内容' },
]

const sortOptions = [
  { value: 'publish_date', label: '上传时间' },
  { value: 'created_at', label: '添加时间' },
]

</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  background: hsl(var(--background) / 0.75);
  backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-panel {
  background: hsl(var(--popover));
  border: 1px solid hsl(var(--border) / 0.5);
  border-radius: var(--radius-xl);
  width: min(480px, calc(100vw - 2rem));
  max-height: min(640px, 90dvh);
  display: flex;
  flex-direction: column;
  box-shadow: 0 24px 64px hsl(var(--foreground) / 0.2), 0 4px 16px hsl(var(--foreground) / 0.1);
  overflow: hidden;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.25rem 1.25rem 0.875rem;
  border-bottom: 1px solid hsl(var(--border) / 0.3);
  flex-shrink: 0;
}

.modal-title {
  font-family: 'JetBrains Mono', 'Courier New', monospace;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: hsl(var(--foreground));
}

.modal-close {
  width: 1.75rem;
  height: 1.75rem;
  border-radius: var(--radius-sm);
  border: 1px solid hsl(var(--border) / 0.3);
  background: transparent;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
  padding: 0;
}

.modal-close:hover {
  background: hsl(var(--destructive) / 0.1);
  border-color: hsl(var(--destructive) / 0.4);
  color: hsl(var(--destructive));
}

.modal-close svg {
  width: 0.875rem;
  height: 0.875rem;
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem 0;
}

.filter-section {
  padding: 0.875rem 1.25rem;
}

.filter-section + .filter-section {
  border-top: 1px solid hsl(var(--border) / 0.15);
}

.filter-section-title {
  font-family: 'JetBrains Mono', 'Courier New', monospace;
  font-size: 0.6rem;
  font-weight: 700;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: hsl(var(--muted-foreground) / 0.6);
  margin-bottom: 0.75rem;
}

.filter-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.375rem;
  align-items: center;
}

.filter-chip {
  padding: 0.3rem 0.75rem;
  border-radius: var(--radius-sm);
  border: 1px solid hsl(var(--border) / 0.4);
  background: hsl(var(--secondary) / 0.3);
  color: hsl(var(--muted-foreground));
  font-family: 'JetBrains Mono', 'Courier New', monospace;
  font-size: 0.65rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.filter-chip:hover {
  border-color: hsl(var(--primary) / 0.4);
  color: hsl(var(--foreground) / 0.8);
  background: hsl(var(--secondary) / 0.5);
}

.filter-chip.is-selected {
  background: hsl(var(--primary) / 0.12);
  border-color: hsl(var(--primary) / 0.5);
  color: hsl(var(--foreground));
  font-weight: 600;
}

.modal-footer {
  display: flex;
  gap: 0.5rem;
  padding: 0.75rem 1.25rem;
  border-top: 1px solid hsl(var(--border) / 0.3);
  flex-shrink: 0;
}

.modal-btn {
  flex: 1;
  padding: 0.5rem;
  border-radius: var(--radius-md);
  border: 1px solid hsl(var(--border) / 0.5);
  font-family: 'JetBrains Mono', 'Courier New', monospace;
  font-size: 0.65rem;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  cursor: pointer;
  transition: all 0.15s ease;
}

.modal-btn--reset {
  background: transparent;
  color: hsl(var(--muted-foreground));
}

.modal-btn--reset:hover {
  background: hsl(var(--secondary) / 0.5);
  color: hsl(var(--foreground));
}

.modal-btn--confirm {
  background: hsl(var(--primary));
  border-color: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
}

.modal-btn--confirm:hover {
  opacity: 0.9;
}

/* Transition */
.modal-enter-active,
.modal-leave-active {
  transition: all 0.25s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .modal-panel,
.modal-leave-to .modal-panel {
  transform: scale(0.95) translateY(-12px);
}
</style>
