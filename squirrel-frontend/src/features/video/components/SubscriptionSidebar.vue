<template>
  <aside class="flex w-[320px] shrink-0 flex-col border-r border-border/20 bg-muted/10">
    <div class="flex h-20 shrink-0 items-center justify-between border-b border-border/20 px-5 bg-background/50 backdrop-blur-sm">
      <div class="min-w-0 flex flex-col justify-center">
        <h1 class="app-h2 truncate">订阅频道</h1>
        <p class="mt-0.5 text-xs font-medium text-muted-foreground/70">{{ channels.length }} 个频道</p>
      </div>
      <Button variant="ghost" size="icon" class="h-9 w-9 rounded-full bg-primary/5 hover:bg-primary/10 text-primary transition-colors" @click="$emit('add')">
        <AppIcon name="plus" class="w-5 h-5" />
      </Button>
    </div>

    <div class="shrink-0 space-y-2.5 border-b border-border/10 p-3 bg-background/20 backdrop-blur-sm z-10">
      <div class="relative group">
        <AppIcon name="search" class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground/60 transition-colors group-focus-within:text-primary" />
        <input
          :value="search"
          @input="$emit('update:search', ($event.target as HTMLInputElement).value)"
          type="text"
          placeholder="搜索订阅..."
          aria-label="搜索订阅"
          class="h-9 w-full rounded-lg border border-transparent bg-muted/40 pl-9 pr-3 text-sm font-medium outline-none transition-all placeholder:text-muted-foreground/50 hover:bg-muted/60 focus:border-primary/30 focus:bg-background focus:ring-2 focus:ring-primary/15"
        />
      </div>

      <div class="flex items-center gap-2">
        <div ref="siteFilterRef" class="relative flex-1">
          <button
            class="flex h-9 w-full items-center justify-between rounded-lg border border-transparent bg-muted/40 px-3 text-xs font-semibold transition-all outline-none hover:bg-muted/60 focus-visible:ring-2 focus-visible:ring-ring/40"
            :class="site ? 'border-primary/20 bg-primary/5 text-foreground' : 'text-muted-foreground'"
            :aria-expanded="siteDropdownOpen"
            aria-haspopup="listbox"
            @click="$emit('update:siteDropdownOpen', !siteDropdownOpen)"
          >
            <div class="flex items-center gap-2">
              <AppIcon name="filter" class="h-3.5 w-3.5" :class="site ? 'text-primary' : ''" />
              <span>{{ activeSiteLabel }}</span>
            </div>
            <AppIcon name="chevronRight" class="h-3.5 w-3.5 transition-transform duration-200" :class="{ 'rotate-90': siteDropdownOpen }" />
          </button>

          <div v-if="siteDropdownOpen" class="absolute left-0 right-0 top-full z-dropdown mt-1.5 rounded-xl border border-border/50 bg-popover p-1.5 shadow-xl ring-1 ring-black/5">
            <div class="max-h-[280px] overflow-y-auto custom-scrollbar pr-1">
              <button @click="$emit('update:site', ''); $emit('update:siteDropdownOpen', false)" class="flex h-9 w-full items-center rounded-lg px-3 text-left text-sm font-medium transition-colors hover:bg-accent" :class="!site ? 'text-foreground bg-accent/50' : 'text-muted-foreground'">全部来源</button>
              <div class="h-px w-full bg-border/50 my-1"></div>
              <button v-for="opt in siteOptions" :key="opt.value" @click="$emit('update:site', opt.value); $emit('update:siteDropdownOpen', false)" class="flex h-9 w-full items-center gap-2.5 rounded-lg px-3 text-left text-sm font-medium transition-colors hover:bg-accent" :class="site === opt.value ? 'text-foreground bg-accent/50' : 'text-muted-foreground'">
                <SiteIcon :site="opt.value" class="h-4 w-4 rounded-sm" />
                <span class="flex-1 truncate">{{ opt.label }}</span>
              </button>
            </div>
          </div>
        </div>

        <button
          type="button"
          class="flex h-9 flex-1 items-center justify-center gap-2 rounded-lg border border-transparent bg-muted/40 px-3 text-xs font-semibold transition-all outline-none hover:bg-muted/60 focus-visible:ring-2 focus-visible:ring-ring/40"
          :class="specialFilter === 'yes' ? 'border-warning/30 bg-warning/10 text-warning' : 'text-muted-foreground hover:text-foreground'"
          :aria-pressed="specialFilter === 'yes'"
          @click="$emit('toggle-special-filter')"
        >
          <AppIcon name="star" class="h-3.5 w-3.5" :class="{ 'fill-current drop-shadow-sm': specialFilter === 'yes' }" />
          <span>特别关注</span>
        </button>
      </div>
    </div>

    <div ref="listContainerRef" class="flex-1 space-y-1 overflow-y-auto p-3 custom-scrollbar relative">
      <div
        v-for="sub in channels"
        :key="sub.id"
        role="button"
        tabindex="0"
        @click="$emit('select-channel', sub.id)"
        @keydown.enter.prevent="$emit('select-channel', sub.id)"
        @keydown.space.prevent="$emit('select-channel', sub.id)"
        class="group relative flex h-[3.25rem] w-full items-center gap-3 rounded-xl px-3 text-left text-sm transition-all overflow-hidden"
        :class="activeChannelId === sub.id ? 'bg-primary/10 text-primary shadow-sm ring-1 ring-primary/20' : 'text-muted-foreground hover:bg-accent/60 hover:text-foreground'"
      >
        <div class="relative shrink-0">
          <SubscriptionAvatar :src="sub.avatar" :name="sub.name" size="md" :class="activeChannelId === sub.id ? 'ring-2 ring-primary/30' : ''" />
          <div v-if="sub.unread_count > 0" class="absolute -right-1.5 -top-1.5 flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-primary px-1 text-2xs font-bold text-primary-foreground ring-2 ring-background shadow-sm">
            {{ sub.unread_count > 99 ? '99+' : sub.unread_count }}
          </div>
        </div>

        <div class="flex-1 min-w-0" :class="{'pr-8': sub.is_special_followed}">
          <span class="block truncate" :class="activeChannelId === sub.id ? 'font-bold' : 'font-medium'">{{ sub.name }}</span>
        </div>

        <button
          v-if="sub.is_special_followed"
          type="button"
          class="shrink-0 inline-flex h-8 w-8 items-center justify-center rounded-lg text-warning hover:bg-warning/10 transition-colors"
          aria-label="取消特别关注"
          @click.stop="$emit('toggle-special', sub)"
        >
          <AppIcon name="star" class="h-4 w-4 fill-current drop-shadow-sm" />
        </button>

        <button
          v-else
          type="button"
          class="absolute right-2 top-1/2 -translate-y-1/2 inline-flex h-8 w-8 items-center justify-center rounded-lg opacity-0 transition-all group-hover:opacity-100 text-muted-foreground/50 hover:text-foreground hover:bg-background/90 backdrop-blur-sm"
          aria-label="设为特别关注"
          @click.stop="$emit('toggle-special', sub)"
        >
          <AppIcon name="star" class="h-4 w-4" />
        </button>
      </div>

      <div v-if="loading" class="space-y-2 p-2">
        <div v-for="i in 5" :key="i" class="h-12 w-full animate-pulse rounded-xl bg-accent/40" />
      </div>

      <div ref="loadMoreRef" class="flex h-12 w-full items-center justify-center">
        <AppSpinner v-if="loadingMore" />
      </div>

      <AppEmptyState
        v-if="finished && !channels.length"
        class="py-10"
        variant="plain"
        icon="inbox"
        title="暂无匹配订阅"
        copy="请尝试更换筛选条件"
      />
    </div>

    <div class="shrink-0 border-t border-border/30 p-4 bg-background/50 backdrop-blur-sm">
      <Button variant="outline" class="h-10 w-full justify-start rounded-xl border-border/50 hover:bg-background shadow-sm font-medium" @click="$emit('import')">
        <AppIcon name="download" class="mr-2 h-4 w-4 text-muted-foreground" />
        导入订阅
      </Button>
    </div>
  </aside>
</template>

<script setup lang="ts">
/**
 * Subscription channel sidebar for the Subscribed view. Extracted from
 * Subscribed.vue (was a ~130-line template block). Pure presentational +
 * controlled: the parent owns all state (channel list, filters, selection) and
 * passes it down via props; user actions emit back. The load-more sentinel ref
 * is exposed so the parent can attach its IntersectionObserver.
 */
import { ref } from 'vue'
import { onClickOutside } from '@vueuse/core'
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppSpinner from '@/shared/components/AppSpinner.vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import { Button } from '@/shared/ui/button'
import SubscriptionAvatar from '@/features/video/components/SubscriptionAvatar.vue'
import SiteIcon from '@/shared/components/SiteIcon.vue'
import type { SubscriptionListItem } from '@/features/video/types/subscription'

defineProps<{
  channels: SubscriptionListItem[]
  loading: boolean
  loadingMore: boolean
  finished: boolean
  search: string
  site: string
  siteOptions: { value: string; label: string }[]
  activeSiteLabel: string
  siteDropdownOpen: boolean
  specialFilter: 'all' | 'yes'
  activeChannelId: string | number | null
}>()

const emit = defineEmits<{
  'add': []
  'import': []
  'select-channel': [id: string | number]
  'toggle-special': [sub: SubscriptionListItem]
  'toggle-special-filter': []
  'update:search': [value: string]
  'update:site': [value: string]
  'update:siteDropdownOpen': [value: boolean]
}>()

// Local click-outside for the site filter dropdown. The parent owns the open
// state but the dropdown's trigger lives here, so the outside-click handler
// emits the close.
const siteFilterRef = ref<HTMLElement | null>(null)
onClickOutside(siteFilterRef, () => emit('update:siteDropdownOpen', false))

// Expose the list container + load-more sentinel so the parent can attach its
// IntersectionObserver for infinite scroll (the observer needs the actual DOM).
const listContainerRef = ref<HTMLElement | null>(null)
const loadMoreRef = ref<HTMLElement | null>(null)
defineExpose({ listContainer: listContainerRef, loadMore: loadMoreRef })
</script>
