<template>
  <Dialog :open="modelValue" @update:open="emit('update:modelValue', $event)">
    <DialogContent class="sm:max-w-[380px] !p-0">
      <!-- Sharp Header -->
      <div class="px-6 py-4 flex items-center justify-between border-b border-border/10">
        <DialogTitle class="text-[14px] font-bold text-foreground">筛选器</DialogTitle>
        <button 
          @click="close" 
          class="w-7 h-7 flex items-center justify-center rounded hover:bg-accent transition-all active:scale-90"
        >
          <X class="w-3.5 h-3.5 text-muted-foreground" />
        </button>
      </div>

      <!-- Settings List -->
      <div class="px-6 py-5 space-y-7 overflow-y-auto max-h-[60vh] no-scrollbar">
        <div v-for="section in filterSections" :key="section.title" class="space-y-3">
          <h4 class="text-[11px] font-bold text-muted-foreground/30 uppercase tracking-wider">{{ section.title }}</h4>
          
          <div class="flex flex-wrap gap-1.5">
            <button
              v-for="opt in section.options"
              :key="opt.value"
              class="setting-pill"
              :class="{ 'is-active': section.model.value === opt.value }"
              @click="section.model.value = opt.value"
            >
              {{ opt.label }}
            </button>
          </div>
        </div>
      </div>

      <!-- Compact Footer -->
      <div class="px-6 py-4 bg-accent/20 flex items-center justify-between border-t border-border/10">
        <button 
          @click="resetAll" 
          class="text-[11px] font-bold text-muted-foreground/50 hover:text-foreground transition-colors"
        >
          重置
        </button>
        <div class="flex gap-2">
          <Button variant="ghost" size="sm" @click="close" class="h-8 text-[12px]">取消</Button>
          <Button @click="confirm" size="sm" class="h-8 px-5 text-[12px] font-bold">确定</Button>
        </div>
      </div>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { X } from 'lucide-vue-next'
import { useUserSettings } from '@/composables/useUserSettings'
import type { TimeRange, Duration, ContentType } from '@/composables/useFeedFilters'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'

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

const localTimeRange = ref(props.timeRange); const localDuration = ref(props.duration)
const localContentType = ref(props.contentType); const localNsfw = ref(props.nsfw)
const localSortBy = ref(props.sortBy)

const filterSections = computed(() => {
  const sections = []
  if (props.scope === 'video') {
    sections.push({ title: '排序', model: localSortBy, options: sortOptions })
    sections.push({ title: '日期', model: localTimeRange, options: timeRangeOptions })
    sections.push({ title: '时长', model: localDuration, options: durationOptions })
    if (!props.subscriptionId) sections.push({ title: '类型', model: localContentType, options: contentTypeOptions })
  }
  if (settings.value.showNsfw) sections.push({ title: '分级', model: localNsfw, options: nsfwOptions })
  return sections
})

watch(() => props.modelValue, (open) => {
  if (open) {
    localTimeRange.value = props.timeRange; localDuration.value = props.duration
    localContentType.value = props.contentType; localNsfw.value = props.nsfw
    localSortBy.value = props.sortBy
  }
})

const close = () => emit('update:modelValue', false)
const confirm = () => {
  emit('update:timeRange', localTimeRange.value); emit('update:duration', localDuration.value)
  emit('update:contentType', localContentType.value); emit('update:nsfw', localNsfw.value)
  emit('update:sortBy', localSortBy.value); close()
}
const resetAll = () => {
  localTimeRange.value = 'all'; localDuration.value = 'all'; localContentType.value = 'all'
  localNsfw.value = 'all'; localSortBy.value = 'publish_date'
}

onMounted(async () => { await loadUserSettings() })

const timeRangeOptions = [{ value: 'all', label: '不限' }, { value: 'today', label: '今天' }, { value: 'week', label: '本周' }, { value: 'month', label: '本月' }]
const durationOptions = [{ value: 'all', label: '不限' }, { value: 'short', label: '短片' }, { value: 'medium', label: '常规' }, { value: 'long', label: '长片' }]
const contentTypeOptions = [{ value: 'all', label: '全部' }, { value: 'CHANNEL', label: '频道' }, { value: 'PLAYLIST', label: '列表' }]
const nsfwOptions = [{ value: 'all', label: '全部' }, { value: 'yes', label: 'NSFW' }, { value: 'no', label: '安全' }]
const sortOptions = [{ value: 'publish_date', label: '上传' }, { value: 'created_at', label: '添加' }]
</script>

<style scoped>
.setting-pill {
  @apply h-8 px-3 rounded-md text-[12px] font-semibold transition-all duration-150 select-none;
  background: hsl(var(--accent) / 0.4);
  color: hsl(var(--muted-foreground) / 0.8);
  border: 1px solid transparent;
}

.setting-pill:hover {
  background: hsl(var(--accent) / 0.7);
  color: hsl(var(--foreground));
}

.setting-pill.is-active {
  @apply bg-foreground text-background shadow-sm;
}

.setting-pill:active {
  @apply scale-95 opacity-80;
}

.no-scrollbar::-webkit-scrollbar { display: none; }
.no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
</style>
