<template>
  <section v-if="items.length > 0" class="group/container mb-6 px-6 pt-2">
    <div class="mb-4 flex items-center justify-between">
      <h2 class="flex items-center gap-2 text-xl font-bold tracking-tight text-foreground/90">
        <AppIcon name="star" class="size-5 fill-current text-amber-500" />
        特别关注
      </h2>
      <div class="flex items-center gap-2">
        <button
          type="button"
          class="flex h-8 items-center gap-1.5 rounded-md px-2.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted/60 hover:text-foreground"
          @click="emit('viewMore')"
        >
          查看更多
          <AppIcon name="chevronRight" class="size-3.5" />
        </button>
        <div class="flex gap-1 opacity-0 transition-opacity duration-200 group-hover/container:opacity-100" :class="{ 'opacity-100': canScrollLeft || canScrollRight }">
        <button
          class="flex size-8 items-center justify-center rounded-full border border-border bg-background/80 shadow-sm transition-all hover:bg-muted disabled:cursor-not-allowed disabled:opacity-30"
          :disabled="!canScrollLeft"
          @click="scroll('left')"
        >
          <AppIcon name="chevronLeft" class="size-4 text-foreground/70" />
        </button>
        <button
          class="flex size-8 items-center justify-center rounded-full border border-border bg-background/80 shadow-sm transition-all hover:bg-muted disabled:cursor-not-allowed disabled:opacity-30"
          :disabled="!canScrollRight"
          @click="scroll('right')"
        >
          <AppIcon name="chevronRight" class="size-4 text-foreground/70" />
        </button>
        </div>
      </div>
    </div>

    <div
      ref="scrollContainer"
      class="no-scrollbar flex gap-4 overflow-x-auto pb-4 scroll-smooth snap-x"
      @scroll="updateScrollState"
    >
      <article
        v-for="item in items"
        :key="item.id"
        class="group w-64 shrink-0 cursor-pointer snap-start"
        @click="emit('openModal', item)"
      >
        <div class="relative aspect-video overflow-hidden rounded-sm bg-muted transition-all duration-300 group-hover:brightness-110">
          <VideoThumbnail
            :src="item.thumbnail"
            :alt="item.title"
            fit="cover"
            interactive
          />
          <div v-if="item.duration" class="absolute bottom-1.5 right-1.5 inline-flex h-5 items-center rounded-md bg-black/65 px-1.5 text-[10px] font-medium tabular-nums text-white backdrop-blur-sm">
            {{ formatDuration(item.duration) }}
          </div>
          <div class="absolute inset-0 flex items-center justify-center bg-black/35 opacity-0 transition-opacity group-hover:opacity-100">
            <div class="flex size-10 scale-75 items-center justify-center rounded-full bg-primary/90 text-primary-foreground shadow-lg backdrop-blur-sm transition-transform group-hover:scale-100">
              <AppIcon name="play" class="ml-1 size-5" />
            </div>
          </div>
        </div>

        <h3 class="mt-2 line-clamp-2 text-sm font-medium text-foreground/80 transition-colors group-hover:text-primary">
          {{ item.title }}
        </h3>
        <button
          v-if="primarySubscription(item)"
          class="mt-1 flex max-w-full items-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
          type="button"
          @click.stop="emit('goToSubscription', primarySubscription(item)?.id)"
        >
          <SubscriptionAvatar
            :src="primarySubscription(item)?.avatar"
            :name="primarySubscription(item)?.name"
            size="sm"
            class="size-4"
          />
          <span class="truncate">{{ primarySubscription(item)?.name }}</span>
        </button>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import { getVideoList } from '@/api'
import AppIcon from '@/components/common/AppIcon.vue'
import SubscriptionAvatar from '@/components/common/SubscriptionAvatar.vue'
import VideoThumbnail from '@/components/feed/VideoThumbnail.vue'
import { formatDuration } from '@/utils/dateFormat'

const emit = defineEmits(['openModal', 'goToSubscription', 'viewMore'])

const items = ref<any[]>([])
const scrollContainer = ref<HTMLElement | null>(null)
const canScrollLeft = ref(false)
const canScrollRight = ref(false)

const updateScrollState = () => {
  if (!scrollContainer.value) return
  const { scrollLeft, scrollWidth, clientWidth } = scrollContainer.value
  canScrollLeft.value = scrollLeft > 0
  canScrollRight.value = scrollLeft < scrollWidth - clientWidth - 2
}

const scroll = (direction: 'left' | 'right') => {
  if (!scrollContainer.value) return

  const scrollAmount = 272 * 2
  scrollContainer.value.scrollTo({
    left: scrollContainer.value.scrollLeft + (direction === 'left' ? -scrollAmount : scrollAmount),
    behavior: 'smooth',
  })
}

const primarySubscription = (item: any) => {
  return Array.isArray(item?.subscriptions) ? item.subscriptions[0] : null
}

onMounted(async () => {
  const { data, error } = await getVideoList({
    page: 1,
    pageSize: 12,
    page_size: 12,
    category: 'all',
    sort_by: 'publish_date',
    nsfw: 'all',
    special: 'yes',
  })
  if (error) return

  items.value = (data?.data || []).slice(0, 12)
  await nextTick()
  updateScrollState()
})
</script>
