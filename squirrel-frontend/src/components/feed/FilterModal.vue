<template>
  <Dialog :open="modelValue" @update:open="emit('update:modelValue', $event)">
    <DialogContent class="sm:max-w-[640px] !p-0">
      <div class="flex max-h-[82vh] flex-col overflow-hidden bg-background">
        <header class="flex items-start justify-between gap-4 border-b border-border/30 px-5 py-4 sm:px-6">
          <div class="min-w-0">
            <DialogTitle class="text-base font-semibold text-foreground">筛选</DialogTitle>
          </div>

          <button
            type="button"
            class="inline-flex size-8 shrink-0 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            title="关闭"
            @click="close"
          >
            <AppIcon name="close" class="size-4" />
          </button>
        </header>

        <div class="overflow-y-auto px-5 py-3 sm:px-6">
          <div class="filter-panel">
            <section
              v-for="section in filterSections"
              :key="section.key"
              class="filter-section"
            >
              <div class="filter-section__label">
                <AppIcon :name="section.icon" class="size-3.5 text-muted-foreground/70" />
                <span>{{ section.title }}</span>
              </div>

              <div class="filter-options" :aria-label="section.title">
                <button
                  v-for="opt in section.options"
                  :key="opt.value"
                  type="button"
                  class="filter-option"
                  :class="{ 'is-active': section.model.value === opt.value }"
                  :aria-pressed="section.model.value === opt.value"
                  @click="section.model.value = opt.value"
                >
                  <span class="truncate">{{ opt.label }}</span>
                </button>
              </div>
            </section>
          </div>
        </div>

        <footer class="flex flex-col gap-3 border-t border-border/30 bg-muted/20 px-5 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <Button
            variant="ghost"
            size="sm"
            class="self-start px-2 text-muted-foreground"
            :disabled="draftActiveCount === 0 && localSortBy === 'publish_date'"
            @click="resetAll"
          >
            重置
          </Button>
          <div class="flex justify-end gap-2">
            <Button variant="outline" size="sm" class="min-w-20" @click="close">取消</Button>
            <Button size="sm" class="min-w-24" @click="confirm">应用</Button>
          </div>
        </footer>
      </div>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import AppIcon from '@/components/common/AppIcon.vue'
import type { AppIconName } from '@/icons/app-icons'
import { useUserSettings } from '@/composables/useUserSettings'
import type { TimeRange, Duration, ContentType } from '@/composables/useFeedFilters'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'

type FilterKey = 'sortBy' | 'timeRange' | 'duration' | 'contentType' | 'nsfw'
type FilterOption = { value: string, label: string }
type FilterSection = {
  key: FilterKey
  title: string
  icon: AppIconName
  model: { value: string }
  options: FilterOption[]
}

const props = withDefaults(defineProps<{
  modelValue: boolean, timeRange: TimeRange, duration: Duration, contentType: ContentType,
  nsfw: string, site?: string, subscriptionId?: string | number, siteLabel?: string, sortBy: string,
  scope?: 'video' | 'subscription'
}>(), { scope: 'video' })

const emit = defineEmits<{
  'update:modelValue': [v: boolean], 'update:timeRange': [v: TimeRange], 'update:duration': [v: Duration],
  'update:contentType': [v: ContentType], 'update:nsfw': [v: string], 'update:site': [v: string | undefined],
  'update:sortBy': [v: string]
}>()

const { settings, loadUserSettings } = useUserSettings()

const localTimeRange = ref<string>(props.timeRange)
const localDuration = ref<string>(props.duration)
const localContentType = ref<string>(props.contentType)
const localNsfw = ref(props.nsfw)
const localSortBy = ref(props.sortBy)

const filterSections = computed<FilterSection[]>(() => {
  const sections: FilterSection[] = []
  if (props.scope === 'video') {
    sections.push({
      key: 'sortBy',
      title: '排序',
      icon: 'upload',
      model: localSortBy,
      options: sortOptions,
    })
    sections.push({
      key: 'timeRange',
      title: '时间',
      icon: 'time',
      model: localTimeRange,
      options: timeRangeOptions,
    })
    sections.push({
      key: 'duration',
      title: '时长',
      icon: 'film',
      model: localDuration,
      options: durationOptions,
    })
    if (!props.subscriptionId) {
      sections.push({
        key: 'contentType',
        title: '来源类型',
        icon: 'content',
        model: localContentType,
        options: contentTypeOptions,
      })
    }
  }
  if (settings.value.showNsfw) {
    sections.push({
      key: 'nsfw',
      title: '内容分级',
      icon: 'security',
      model: localNsfw,
      options: nsfwOptions,
    })
  }
  return sections
})

const draftChips = computed(() => {
  const chips: { key: FilterKey, label: string }[] = []
  if (localSortBy.value !== 'publish_date') chips.push({ key: 'sortBy', label: `排序：${labelFor(sortOptions, localSortBy.value)}` })
  if (localTimeRange.value !== 'all') chips.push({ key: 'timeRange', label: `时间：${labelFor(timeRangeOptions, localTimeRange.value)}` })
  if (localDuration.value !== 'all') chips.push({ key: 'duration', label: `时长：${labelFor(durationOptions, localDuration.value)}` })
  if (localContentType.value !== 'all' && !props.subscriptionId) chips.push({ key: 'contentType', label: `类型：${labelFor(contentTypeOptions, localContentType.value)}` })
  if (localNsfw.value !== 'all' && settings.value.showNsfw) chips.push({ key: 'nsfw', label: `分级：${labelFor(nsfwOptions, localNsfw.value)}` })
  return chips
})

const draftActiveCount = computed(() => draftChips.value.length)

watch(() => props.modelValue, (open) => {
  if (open) {
    localTimeRange.value = props.timeRange
    localDuration.value = props.duration
    localContentType.value = props.contentType
    localNsfw.value = props.nsfw
    localSortBy.value = props.sortBy
  }
})

const close = () => emit('update:modelValue', false)

const confirm = () => {
  emit('update:timeRange', localTimeRange.value as TimeRange)
  emit('update:duration', localDuration.value as Duration)
  emit('update:contentType', localContentType.value as ContentType)
  emit('update:nsfw', localNsfw.value)
  emit('update:sortBy', localSortBy.value)
  close()
}

const resetAll = () => {
  localTimeRange.value = 'all'
  localDuration.value = 'all'
  localContentType.value = 'all'
  localNsfw.value = 'all'
  localSortBy.value = 'publish_date'
}

const labelFor = (options: FilterOption[], value: string) => options.find((opt) => opt.value === value)?.label || value

onMounted(async () => { await loadUserSettings() })

const timeRangeOptions: FilterOption[] = [
  { value: 'all', label: '不限' },
  { value: 'today', label: '今天' },
  { value: 'week', label: '本周' },
  { value: 'month', label: '本月' },
]
const durationOptions: FilterOption[] = [
  { value: 'all', label: '不限' },
  { value: 'short', label: '短片' },
  { value: 'medium', label: '常规' },
  { value: 'long', label: '长片' },
]
const contentTypeOptions: FilterOption[] = [
  { value: 'all', label: '全部' },
  { value: 'CHANNEL', label: '频道' },
  { value: 'PLAYLIST', label: '列表' },
]
const nsfwOptions: FilterOption[] = [
  { value: 'all', label: '全部' },
  { value: 'yes', label: '敏感' },
  { value: 'no', label: '安全' },
]
const sortOptions: FilterOption[] = [
  { value: 'publish_date', label: '上传日期' },
  { value: 'created_at', label: '添加日期' },
]
</script>

<style scoped>
.filter-panel {
  display: flex;
  flex-direction: column;
}

.filter-section {
  display: flex;
  min-width: 0;
  align-items: center;
  justify-content: space-between;
  gap: 1.25rem;
  padding: 0.875rem 0;
}

.filter-section + .filter-section {
  border-top: 1px solid hsl(var(--border) / 0.28);
}

.filter-section__label {
  display: inline-flex;
  min-width: 6.5rem;
  align-items: center;
  gap: 0.5rem;
  color: hsl(var(--foreground));
  font-size: 0.8125rem;
  font-weight: 650;
}

.filter-options {
  display: inline-flex;
  min-width: 0;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 1.125rem;
}

.filter-option {
  display: inline-flex;
  min-width: 0;
  height: 1.75rem;
  align-items: center;
  justify-content: center;
  position: relative;
  border: 0;
  border-radius: 0;
  background: transparent;
  padding: 0 0.125rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 600;
  transition: color var(--duration-fast, 150ms) var(--ease-default, ease);
}

.filter-option:hover {
  color: hsl(var(--foreground));
}

.filter-option.is-active {
  color: hsl(var(--foreground));
  font-weight: 700;
}

.filter-option.is-active::after {
  position: absolute;
  right: 0;
  bottom: -0.125rem;
  left: 0;
  height: 2px;
  border-radius: 999px;
  background: hsl(var(--primary));
  content: '';
}

@media (max-width: 639px) {
  .filter-section {
    align-items: stretch;
    flex-direction: column;
    gap: 0.625rem;
  }

  .filter-options {
    justify-content: flex-start;
  }
}
</style>
