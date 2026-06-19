<template>
  <Dialog :open="modelValue" @update:open="emit('update:modelValue', $event)">
    <DialogContent class="sm:max-w-[480px] !p-0 gap-0">
      <div class="flex max-h-[82vh] flex-col overflow-hidden bg-background">
        <header class="flex items-center justify-between gap-4 px-5 py-4 sm:px-6">
          <DialogTitle class="text-base font-semibold text-foreground">筛选</DialogTitle>
          <button
            type="button"
            class="inline-flex size-8 shrink-0 items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-muted/70 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            title="关闭"
            @click="close"
          >
            <AppIcon name="close" class="size-4" />
          </button>
        </header>

        <div class="overflow-y-auto px-5 pb-2 sm:px-6">
          <section
            v-for="(section, i) in filterSections"
            :key="section.key"
            class="filter-section"
            :class="{ 'filter-section--first': i === 0 }"
          >
            <h3 class="filter-section__title">
              <AppIcon :name="section.icon" class="size-3.5" />
              <span>{{ section.title }}</span>
            </h3>

            <div class="filter-section__options" :aria-label="section.title">
              <button
                v-for="opt in section.options"
                :key="opt.value"
                type="button"
                class="filter-pill"
                :class="{ 'is-active': section.model.value === opt.value }"
                :aria-pressed="section.model.value === opt.value"
                @click="section.model.value = opt.value"
              >
                {{ opt.label }}
              </button>
            </div>
          </section>
        </div>

        <footer class="flex items-center justify-between gap-3 border-t border-border/30 bg-muted/20 px-5 py-3 sm:px-6">
          <Button
            variant="ghost"
            size="sm"
            class="px-2 text-muted-foreground hover:text-foreground"
            :disabled="draftActiveCount === 0 && localSortBy === 'publish_date'"
            @click="resetAll"
          >
            重置
          </Button>
          <Button size="sm" class="min-w-20" @click="confirm">应用</Button>
        </footer>
      </div>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import type { AppIconName } from '@/shared/icons/app-icons'
import { useUserSettings } from '@/shared/composables/useUserSettings'
import type { TimeRange, Duration, ContentType } from '@/features/video/composables/useFeedFilters'
import { Dialog, DialogContent, DialogTitle } from '@/shared/ui/dialog'
import { Button } from '@/shared/ui/button'

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

const draftActiveCount = computed(() => {
  let c = 0
  if (localSortBy.value !== 'publish_date') c++
  if (localTimeRange.value !== 'all') c++
  if (localDuration.value !== 'all') c++
  if (localContentType.value !== 'all' && !props.subscriptionId) c++
  if (localNsfw.value !== 'all' && settings.value.showNsfw) c++
  return c
})

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
.filter-section {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
  padding: 1rem 0;
  border-top: 1px solid hsl(var(--border) / 0.4);
}

.filter-section--first {
  padding-top: 0.25rem;
  border-top: 0;
}

.filter-section__title {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.02em;
}

.filter-section__options {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.filter-pill {
  display: inline-flex;
  min-width: 0;
  height: 2rem;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: 999px;
  background: hsl(var(--muted) / 0.5);
  padding: 0 0.9rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.8125rem;
  font-weight: 600;
  white-space: nowrap;
  transition: background-color var(--duration-fast, 150ms) var(--ease-default, ease),
              color var(--duration-fast, 150ms) var(--ease-default, ease);
}

.filter-pill:hover {
  background: hsl(var(--muted));
  color: hsl(var(--foreground));
}

.filter-pill.is-active {
  background: hsl(var(--primary) / 0.1);
  color: hsl(var(--primary));
}
</style>
