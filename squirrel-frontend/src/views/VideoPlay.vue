
<template>
  <div ref="videoPageRef" class="video-page terminal-viewport scrollbar-hide" :class="{ 'is-widescreen': isWidescreen }">
    <div :class="['video-page__container', { 'is-widescreen': isWidescreen }]">
      <!-- 左侧主内容区域 -->
      <div class="video-main">
        <!-- 视频播放区域 -->
        <div ref="videoSectionRef" class="video-section">
          <div class="video-container">
            <Transition name="fade-player" appear>
              <div class="viewfinder-box">
                <div class="viewfinder-corner viewfinder-corner--top-left"></div>
                <div class="viewfinder-corner viewfinder-corner--top-right"></div>
                <div class="viewfinder-corner viewfinder-corner--bottom-left"></div>
                <div class="viewfinder-corner viewfinder-corner--bottom-right"></div>
                <VideoPlayer
                  ref="videoPlayerRef"
                  v-if="video || playbackSource || isResolvingPlayback || externalError"
                  :source="playbackSource"
                  :subtitles="subtitleTracks"
                  :poster="video?.thumbnail"
                  :title="video?.title"
                  :initialTime="startTime"
                  :has-prev="hasPrevVideo"
                  :has-next="hasNextVideo"
                  :external-error="externalError"
                  :widescreen="isWidescreen"
                  :external-loading="isResolvingPlayback"
                  :external-loading-text="'正在建立播放链路'"
                  :adapter="playerAdapter"
                  :theme="effectiveTheme"
                  :i18n-options="{ persist: true, storageKey: 'sp-locale', applyToDocument: true, useGlobal: true }"
                  :enable-global-shortcuts="true"
                  :enable-click-outside-close-menu="true"
                  :enable-window-resize="true"

                  @play="onVideoPlay"
                  @pause="onVideoPause"
                  @ended="handleAutoplayNext"
                  @timeupdate="onVideoTimeUpdate"
                  @prev="handlePrevVideo"
                  @next="handleNextVideo"
                  @widescreenChange="toggleWidescreen"
                  @retry="handlePlayerRetry"
                />
              </div>
            </Transition>
          </div>
        </div>

        <!-- 视频信息区域 -->
        <div ref="videoMetaRef" class="video-meta">
          <Transition name="fade-meta" mode="out-in">
            <div v-if="video" :key="video.id">
              <!-- 标题行 -->
              <h1 class="video-meta__title">
                {{ video?.title }}
              </h1>

              <!-- 频道信息 + 操作按钮 -->
              <div class="video-meta__info-row">
                <!-- 频道信息 -->
                <div class="video-channel">
                  <div class="video-channel__primary">
                    <div class="video-channel__avatar-wrapper">
                      <SubscriptionAvatar
                        v-if="video?.subscriptions?.[0]"
                        :src="video.subscriptions[0].avatar"
                        :name="video.subscriptions[0].name"
                        size="lg"
                        class="video-channel__avatar"
                      />
                    </div>
                    <div class="video-channel__identity">
                      <router-link
                        v-if="video?.subscriptions?.[0]"
                        :to="`/subscription/${video.subscriptions[0].id}/all`"
                        class="video-channel__name"
                      >
                        {{ video.subscriptions[0].name }}
                      </router-link>
                      <div class="video-channel__stats">
                        {{ video?.subscriptions?.[0]?.total_videos || 0 }} 视频
                      </div>
                    </div>
                  </div>
                </div>
                <button
                  v-if="video?.subscriptions?.[0]"
                  class="subscribe-btn"
                  @click.stop="handleUnsubscribe(video.subscriptions[0].id)"
                >
                  <Icon icon="lucide:bell" class="subscribe-btn__icon" />
                  <span class="subscribe-btn__label">订阅</span>
                </button>

                <!-- 操作按钮 -->
                <div class="video-meta__actions">
                  <template v-for="action in videoActions" :key="action.key">
                    <button
                      v-if="!action.href"
                      class="action-btn"
                      :class="{ 'is-active': action.active, [`tone-${action.tone}`]: true }"
                      @click="handleVideoAction(action)"
                    >
                      <Icon :icon="action.icon" class="action-btn__icon" />
                      <span class="action-btn__label">{{ action.label }}</span>
                    </button>
                    <a
                      v-else
                      :href="action.href"
                      target="_blank"
                      class="action-btn"
                    >
                      <Icon :icon="action.icon" class="action-btn__icon" />
                      <span class="action-btn__label">{{ action.label }}</span>
                    </a>
                  </template>
                </div>
              </div>
            </div>
            <div v-else class="video-meta-skeleton">
              <div class="skeleton-title w-3/4 h-8 bg-muted rounded"></div>
              <div class="flex items-center justify-between mt-6">
                <div class="flex items-center gap-3">
                  <div class="w-10 h-10 rounded-full bg-muted"></div>
                  <div class="space-y-2">
                    <div class="w-24 h-4 bg-muted rounded"></div>
                    <div class="w-16 h-3 bg-muted rounded"></div>
                  </div>
                </div>
                <div class="flex gap-2">
                  <div v-for="i in 4" :key="i" class="w-20 h-8 bg-muted rounded"></div>
                </div>
              </div>
            </div>
          </Transition>
        </div>
      </div>

      <!-- 右侧区域 - 相关视频 -->
      <div class="video-aside">
        <div class="video-aside__panel">
          <div class="video-aside__header">
            <h2 class="video-aside__title">相关视频</h2>
          </div>
          <div class="video-aside__content scrollbar-hide">
            <Transition name="fade-aside" mode="out-in">
              <div v-if="loadingRelated && !relatedVideos.length" key="skeleton" class="related-videos-list">
                <RelatedVideoSkeleton v-for="i in 8" :key="i" :delay="i * 100" />
              </div>
              <div v-else-if="!relatedVideos.length && !loadingRelated" key="empty" class="video-aside__empty">暂无推荐</div>
              <div v-else key="list" class="related-videos-list">
                <TransitionGroup name="related-list">
                  <article
                    v-for="(relatedVideo, index) in relatedVideos"
                    :key="relatedVideo.id"
                    class="related-video-card group"
                    @click="goToVideo(relatedVideo.id, relatedVideo)"
                  >
                    <!-- 保持之前的卡片设计内容不变 -->
                    <div class="related-video-card__thumb-container">
                      <div class="related-video-card__thumb">
                        <img
                          v-if="relatedVideo.thumbnail && !relatedThumbnailErrorIds.has(relatedVideo.id)"
                          :src="relatedVideo.thumbnail"
                          referrerpolicy="no-referrer"
                          class="related-video-card__image"
                          :class="{ 'image-loaded': relatedImagesLoaded[relatedVideo.id] }"
                          draggable="false"
                          :alt="relatedVideo.title"
                          @load="relatedImagesLoaded[relatedVideo.id] = true"
                          @error="() => relatedThumbnailErrorIds.add(relatedVideo.id)"
                        >
                        <div v-else class="related-video-card__fallback">
                          <div class="fallback-noise"></div>
                          <div class="fallback-content">
                            <span class="fallback-status">信号丢失</span>
                            <span class="fallback-id">ID: {{ formatVideoCardId(relatedVideo.id) }}</span>
                          </div>
                        </div>
                        <div class="related-video-card__scanline"></div>
                        
                        <div class="related-video-card__duration">
                          {{ formatDuration(relatedVideo.duration) }}
                        </div>
                      </div>
                    </div>

                    <div class="related-video-card__body">
                      <div class="related-video-card__title">
                        {{ relatedVideo.title }}
                      </div>
                      <div class="related-video-card__meta">
                        <SubscriptionAvatar
                          v-if="relatedVideo.subscriptions?.[0]"
                          :src="relatedVideo.subscriptions[0].avatar"
                          :name="relatedVideo.subscriptions[0].name"
                          size="sm"
                          class="related-video-card__avatar"
                        />
                        <router-link
                          v-if="relatedVideo.subscriptions?.[0]?.id"
                          :to="`/subscription/${relatedVideo.subscriptions[0].id}/all`"
                          @click.stop
                          class="related-video-card__channel"
                        >
                          {{ relatedVideo.subscriptions[0].name }}
                        </router-link>
                        <span v-else class="related-video-card__site">
                          {{ relatedVideo.site }}
                        </span>
                        <span class="related-video-card__separator">/</span>
                        <span v-if="relatedVideo.uploaded_at" class="related-video-card__date">
                          {{ formatDate(relatedVideo.uploaded_at) }}
                        </span>
                      </div>
                    </div>
                  </article>
                </TransitionGroup>
              </div>
            </Transition>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed, nextTick, reactive, inject } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import usePlaybackOrchestrator from '../composables/usePlaybackOrchestrator';
import usePlaybackReporting from '../composables/usePlaybackReporting';
import { useAppTheme } from '@/composables/useAppTheme'
import SubscriptionAvatar from '@/components/common/SubscriptionAvatar.vue'
import VideoPlayer from '@/components/video-player/VideoPlayer.vue';
import RelatedVideoSkeleton from '@/components/video-player/RelatedVideoSkeleton.vue';
import { LocalStorageAdapter } from '@/components/video-player/core';
import { Icon } from '@iconify/vue';
import useVideoHistory from "../composables/useVideoHistory";
import { formatDate, formatDuration } from '../utils/dateFormat';
import { formatVideoCardId } from '@/utils/videoCard';
import useVideoInteraction from '../composables/useVideoInteraction';
import { Logger } from '@/utils/logger'
import { getRandomVideo, unsubscribe as apiUnsubscribe } from '@/api'




const route = useRoute();
const router = useRouter();
const emitter = inject('emitter');
const APP_TITLE = 'Squirrel'

const playerAdapter = new LocalStorageAdapter();
const { effectiveTheme } = useAppTheme()


// 内部切换不使用 router，所以不需要从 history.state 读取初始数据
const { video, startTime, relatedVideos, loadingRelated, playbackSource, subtitleTracks, loadAndPlayById, externalError, isResolvingPlayback } = usePlaybackOrchestrator(null);
const { sendReport } = useVideoHistory();
const { INTERACTION_TYPE, toggleLike, deleteInteraction } = useVideoInteraction();
const { onVideoPlay, onVideoPause, onVideoEnded, onVideoTimeUpdate } = usePlaybackReporting(video, sendReport);

const currentInteractionType = computed(() => video.value?.interaction_type ?? null);

const videoPrimaryActions = computed(() => {
  const actions = [
    {
      key: 'like',
      label: '喜欢',
      icon: currentInteractionType.value === INTERACTION_TYPE.LIKE ? 'lucide:thumbs-up' : 'lucide:thumbs-up',
      active: currentInteractionType.value === INTERACTION_TYPE.LIKE,
      tone: 'like',
      variant: 'primary',
      onClick: () => video.value && handleLike(video.value, INTERACTION_TYPE.LIKE)
    },
    {
      key: 'dislike',
      label: '不喜欢',
      icon: 'lucide:thumbs-down',
      active: currentInteractionType.value === INTERACTION_TYPE.DISLIKE,
      tone: 'danger',
      variant: 'secondary',
      onClick: () => video.value && handleLike(video.value, INTERACTION_TYPE.DISLIKE)
    },
    {
      key: 'later',
      label: '稍后看',
      icon: currentInteractionType.value === INTERACTION_TYPE.LATER ? 'lucide:list-plus' : 'lucide:list-plus',
      active: currentInteractionType.value === INTERACTION_TYPE.LATER,
      tone: 'later',
      variant: 'primary',
      onClick: () => video.value && handleLater(video.value)
    }
  ];

  if (video.value?.url) {
    actions.push({
      key: 'source',
      label: '原视频',
      icon: 'lucide:external-link',
      active: false,
      tone: 'neutral',
      variant: 'secondary',
      href: video.value.url
    });
  }

  return actions;
});

const videoOverflowActions = computed(() => {
  return [
    {
      key: 'random',
      label: '随机播放',
      icon: 'lucide:shuffle',
      active: false,
      tone: 'neutral',
      hint: '',
      onClick: () => handlePlayRandom()
    }
  ];
});

const videoActions = computed(() => [...videoPrimaryActions.value, ...videoOverflowActions.value]);

const handleVideoAction = async (action) => {
  if (action.href || !action.onClick) return;
  await action.onClick();
};


// 视频播放器引用
const videoPlayerRef = ref(null);
const videoPageRef = ref(null);
const videoSectionRef = ref(null);
const videoMetaRef = ref(null);


// 宽屏模式
const isWidescreen = ref(false);
const toggleWidescreen = (value) => {
  isWidescreen.value = value;
  setWidescreenClass(isWidescreen.value);
  syncWidescreenSidebarState(isWidescreen.value);
};

const setWidescreenClass = (enabled) => {
  document.documentElement.classList.toggle('video-widescreen', !!enabled);
};

const syncWidescreenSidebarState = (enabled) => {
  if (!emitter) return;
  emitter.emit('videoWidescreenStateChanged', !!enabled);
};


const relatedThumbnailErrorIds = reactive(new Set());
const relatedImagesLoaded = reactive({})
const isVideoChannelVisible = ref(true)
const isChannelUnsubscribing = ref(false)
const videoChannelError = ref('')
const VIDEO_CHANNEL_DISMISS_MS = 180

const wait = (ms) => new Promise((resolve) => {
  window.setTimeout(resolve, ms)
})

const handlePlayerRetry = async () => {
  if (!video.value?.id) return;
  await loadAndPlayById(video.value.id, video.value, { forceRefresh: true });   
};

// 记录最近播放的视频，防止循环播放
const recentlyPlayed = ref([]);

// 是否有上一个视频（相关视频列表有数据就可以切换）
const hasPrevVideo = computed(() => {
  return relatedVideos.value && relatedVideos.value.length > 0;
});

// 是否有下一个视频（相关视频列表有数据就可以切换）
const hasNextVideo = computed(() => {
  return relatedVideos.value && relatedVideos.value.length > 0;
});

// 切换到上一个视频（从相关视频列表末尾开始找一个未播放的）
const handlePrevVideo = async () => {
  if (!relatedVideos.value?.length) return;
  
  // 从末尾往前找第一个未在最近播放历史中的视频
  for (let i = relatedVideos.value.length - 1; i >= 0; i--) {
    const prevVideo = relatedVideos.value[i];
    if (prevVideo?.id && !recentlyPlayed.value.includes(prevVideo.id)) {
      await goToVideo(prevVideo.id, prevVideo);
      return;
    }
  }
  
  // 如果所有视频都播放过，就播放最后一个
  const lastVideo = relatedVideos.value[relatedVideos.value.length - 1];
  if (lastVideo?.id) {
    await goToVideo(lastVideo.id, lastVideo);
  }
};

// 切换到下一个视频（从相关视频列表开头找一个未播放的）
const handleNextVideo = async () => {
  if (!relatedVideos.value?.length) return;
  
  // 查找第一个未在最近播放历史中的视频
  const nextVideo = relatedVideos.value.find(v => !recentlyPlayed.value.includes(v.id));
  if (nextVideo?.id) {
    await goToVideo(nextVideo.id, nextVideo);
    return;
  }
  
  // 如果所有视频都播放过，就播放第一个
  const firstVideo = relatedVideos.value[0];
  if (firstVideo?.id) {
    await goToVideo(firstVideo.id, firstVideo);
  }
};

const handleUnsubscribe = async (subscriptionId) => {
  if (!subscriptionId || isChannelUnsubscribing.value) return

  isChannelUnsubscribing.value = true
  videoChannelError.value = ''

  const { error } = await apiUnsubscribe(subscriptionId)

  if (error) {
    videoChannelError.value = error?.message || '取消订阅失败'
    isChannelUnsubscribing.value = false
    return
  }

  isVideoChannelVisible.value = false
  await wait(VIDEO_CHANNEL_DISMISS_MS)
  isChannelUnsubscribing.value = false
};

const handleLike = async (video, interactionType) => {
  if (video.interaction_type !== interactionType) {
    const { error } = await toggleLike(video.id, interactionType)
    if (!error) {
      video.interaction_type = interactionType;
    }
  } else {
    const { error } = await deleteInteraction(video.id)
    if (!error) {
      video.interaction_type = null;
    }
  }
};

const handleLater = async (video) => {
  if (video.interaction_type !== INTERACTION_TYPE.LATER) {
    const { error } = await toggleLike(video.id, INTERACTION_TYPE.LATER)
    if (!error) {
      video.interaction_type = INTERACTION_TYPE.LATER;
    }
  } else {
    const { error } = await deleteInteraction(video.id)
    if (!error) {
      video.interaction_type = null;
    }
  }
};


const handlePlayRandom = async () => {
  const params = {};
  
  // 尝试多次获取，跳过最近播放过的视频
  let attempts = 0;
  const maxAttempts = 3;
  
  while (attempts < maxAttempts) {
    const res = await getRandomVideo(params);
    if (!res.error && res.data?.id) {
      // 如果这个视频不在最近播放历史中，就播放它
      if (!recentlyPlayed.value.includes(res.data.id)) {
        await goToVideo(res.data.id, res.data);
        return;
      }
    }
    attempts++;
  }
  
  // 如果尝试3次都是最近播放过的，就播放最后一个
  const res = await getRandomVideo(params);
  if (!res.error && res.data?.id) {
    await goToVideo(res.data.id, res.data);
  }
};


  // 聚焦到视频播放器，使键盘控制生效
  const focusVideoPlayer = async () => {
    await nextTick();
    // 延迟一点，确保 DOM 已经完全渲染
    setTimeout(() => {
      try {
        const rootEl = videoPlayerRef.value?.$el;
        const containerEl = rootEl instanceof HTMLElement ? rootEl : null;
        const playerContainer = containerEl?.classList?.contains('sp-player')
          ? containerEl
          : containerEl?.querySelector('.sp-player');
        if (playerContainer && typeof playerContainer.focus === 'function') {
          playerContainer.focus({ preventScroll: true });
        }
      } catch (e) {
        Logger.debug('Failed to focus video player', e);
      }
    }, 100);
  };

const goToVideo = async (id, videoData = null) => {
  if (!id) return;
  const targetId = String(id);
  if (String(video.value?.id ?? '') === targetId) return;
  
  // 记录当前视频到播放历史（如果有的话）
  if (video.value?.id && !recentlyPlayed.value.includes(video.value.id)) {
    recentlyPlayed.value.push(video.value.id);
    // 只保留最近5个视频的历史
    if (recentlyPlayed.value.length > 5) {
      recentlyPlayed.value.shift();
    }
  }
  
  // 切换到新视频前，先停止当前播放并重置状态
  try {
    videoPlayerRef.value?.stop();
  } catch (_) {}

  // 使用 Vue Router 进行导航，确保路由参数更新、后退可用，并触发依赖路由的逻辑
  // 注意：state 只能存储可序列化的数据，避免传入响应式对象
  if (String(route.params.videoId ?? '') !== targetId) {
    const simpleState = videoData ? {
      videoId: videoData.id,
      title: videoData.title,
      thumbnail: videoData.thumbnail,
    } : {};

    try {
      await router.replace({ name: 'VideoPlay', params: { videoId: targetId }, state: simpleState });
    } catch (_) {
      await router.replace(`/video/${targetId}`);
    }
  }
};

const handleAutoplayNext = async (evt) => {
  try {
    try { onVideoEnded(); } catch (_) {}
    const autoplayEnabled = evt?.autoplay ?? true;
    const autoplayNextEnabled = evt?.autoplayNext ?? true;
    const loopEnabled = evt?.loop ?? false;
    if (!autoplayEnabled || !autoplayNextEnabled || loopEnabled) return;

    const relatedList = Array.isArray(relatedVideos.value) ? relatedVideos.value : [];
    if (!relatedList.length) return;

    // 查找第一个未在最近播放历史中的视频
    const next = relatedList.find(v => !recentlyPlayed.value.includes(v.id));
    if (next?.id) {
      await goToVideo(next.id, next);
      return;
    }

    // 相关视频已播完则停止
  } catch (_) {}
};



onMounted(async () => {
  // 初始加载时从API获取数据
  await loadAndPlayById(route.params.videoId);
  await focusVideoPlayer();

  setWidescreenClass(isWidescreen.value);
  syncWidescreenSidebarState(isWidescreen.value);
});

watch(() => route.params.videoId, async (newId, oldId) => {
  // 只有从外部导航进来才需要重新加载
  // 内部切换（goToVideo）已经调用了loadAndPlayById，不需要重复加载
  if (newId && newId !== oldId && video.value?.id !== newId) {
    await loadAndPlayById(newId);
    await focusVideoPlayer();
  }
});

watch(() => video.value?.id, () => {
  isVideoChannelVisible.value = true
  isChannelUnsubscribing.value = false
  videoChannelError.value = ''
})

watch(
  () => [route.params.videoId, video.value?.title],
  ([videoId, videoTitle]) => {
    const resolvedTitle = String(videoTitle || '').trim()
    if (resolvedTitle) {
      document.title = `${resolvedTitle} - ${APP_TITLE}`
      return
    }

    const fallbackId = String(videoId || '').trim()
    document.title = `${fallbackId ? `视频 ${fallbackId}` : '视频播放'} - ${APP_TITLE}`
  },
  { immediate: true }
)

watch(() => relatedVideos.value, () => {
  Object.keys(relatedImagesLoaded).forEach(key => delete relatedImagesLoaded[key])
}, { deep: true })

onUnmounted(() => {
  setWidescreenClass(false);
  syncWidescreenSidebarState(false);
});

</script>

<style scoped>
/* 基础容器 */
.terminal-viewport {
  background-color: hsl(var(--background));
  background-image: 
    linear-gradient(hsl(var(--foreground) / 0.02) 1px, transparent 1px),
    linear-gradient(90deg, hsl(var(--foreground) / 0.02) 1px, transparent 1px);
  background-size: 40px 40px;
  color: hsl(var(--foreground) / 0.8);
}

.video-page {
  min-height: 100%;
}

.video-page__container {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  width: 100%;
  padding: 1rem;
}

@media (min-width: 640px) {
  .video-page__container {
    padding: 1.5rem;
  }
}

@media (min-width: 1024px) {
  .video-page__container {
    padding: 2rem;
  }
}

@media (min-width: 1280px) {
  .video-page__container {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 400px;
    align-items: start;
  }
}

.video-main {
  width: 100%;
  min-width: 0;
}

.video-section {
  width: 100%;
  background: #000;
  border-radius: 0;
  overflow: hidden;
}

.video-container {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  background: #000;
}

/* 推荐视频列表项 - 彻底移除卡片效果 */
.related-video-card {
  position: relative;
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 0.65rem;
  padding: 0.4rem 0;
  background: transparent !important;
  border: none !important;
  border-radius: 0 !important;
  box-shadow: none !important;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.2, 0, 0.1, 1);
  align-items: flex-start;
}

@media (max-width: 640px) {
  .related-video-card {
    grid-template-columns: 110px 1fr;
    gap: 0.5rem;
  }
}

.related-video-card:hover {
  transform: translateX(4px);
  background: hsl(var(--foreground) / 0.03) !important;
}

.related-video-card__thumb-container {
  width: 100%;
}

.related-video-card__thumb {
  position: relative;
  overflow: hidden;
  border-radius: 4px; /* 进一步减小圆角，更显精致 */
  background: hsl(var(--background));
  aspect-ratio: 16 / 9;
  width: 100%;
}

.related-video-card__image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.related-video-card__image.image-loaded {
  opacity: 1;
}

.related-video-card__title {
  font-size: 0.82rem; /* 稍微调小字号 */
  font-weight: 600;
  line-height: 1.3;
  color: hsl(var(--foreground));
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: 0.2rem;
  transition: color 0.2s;
}

.related-video-card:hover .related-video-card__title {
  color: hsl(var(--primary));
}

.related-video-card__meta {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.7rem; /* 稍微调小字号 */
  color: hsl(var(--muted-foreground) / 0.8);
}

.related-video-card__avatar {
  width: 1.1rem !important;
  height: 1.1rem !important;
  border-radius: calc(var(--radius-sm) - 1px);
  flex-shrink: 0;
}

.related-video-card__channel {
  max-width: 6rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.related-video-card__duration {
  position: absolute;
  right: 0.25rem;
  bottom: 0.25rem;
  padding: 0.05rem 0.25rem;
  background: rgba(0, 0, 0, 0.8);
  color: #fff;
  font-size: 0.65rem;
  border-radius: 2px;
  font-family: 'JetBrains Mono', monospace;
}

/* 宽屏/剧院模式适配 - 优化可视区域 */
.video-page__container.is-widescreen {
  --video-theater-top-offset: calc(var(--app-topbar-height, 0px) + 0.5rem);
  /* 增加保底高度，从 8.5rem 提升到更安全的 11rem，确保标题+两行信息可见 */
  --video-theater-meta-peek: clamp(10rem, 20vh, 14rem); 
  --video-theater-bottom-gap: 0.5rem;
  --video-theater-max-height: calc(100vh - var(--video-theater-top-offset) - var(--video-theater-meta-peek) - var(--video-theater-bottom-gap));
  --video-theater-max-height: calc(100dvh - var(--video-theater-top-offset) - var(--video-theater-meta-peek) - var(--video-theater-bottom-gap));
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  max-width: none;
  width: 100%;
}

.video-page__container.is-widescreen .video-section {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100vw;
  height: var(--video-theater-max-height);
  margin-inline: calc(50% - 50vw);
  background: #000;
  overflow: hidden; /* 防止溢出 */
}

/* 关键修复：确保容器在高度受限时也能完整显示 */
.video-page__container.is-widescreen .video-container {
  height: 100%;
  width: 100%;
  max-height: var(--video-theater-max-height);
  aspect-ratio: 16 / 9;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
}

.video-page__container.is-widescreen .video-container :deep(.sp-player) {
  height: 100%;
  width: 100%;
  max-height: 100%;
}

/* 宽屏模式下信息区域适配 */
.video-page__container.is-widescreen .video-meta {
  margin-top: 0.75rem;
}

.video-page__container.is-widescreen .video-meta__title {
  font-size: 1rem;
  margin-bottom: 0.5rem;
}

.video-page__container.is-widescreen .video-meta__info-row {
  gap: 0.375rem;
}

.video-page__container.is-widescreen .video-channel__avatar {
  width: 2rem !important;
  height: 2rem !important;
}

.video-page__container.is-widescreen .video-channel__name {
  font-size: 0.85rem;
}

.video-page__container.is-widescreen .video-channel__stats {
  font-size: 0.65rem;
}

.video-page__container.is-widescreen .subscribe-btn {
  padding: 0.3rem 0.75rem;
  font-size: 0.7rem;
}

.video-page__container.is-widescreen .subscribe-btn__icon {
  width: 12px;
  height: 12px;
}

.video-page__container.is-widescreen .video-meta__divider {
  height: 20px;
  margin: 0 0.125rem;
}

.video-page__container.is-widescreen .action-btn {
  padding: 0.3rem 0.6rem;
  font-size: 0.7rem;
  gap: 0.2rem;
}

.video-page__container.is-widescreen .action-btn__icon {
  width: 14px;
  height: 14px;
}

.video-page__container.is-widescreen .video-aside {
  position: static;
  top: auto;
  margin-top: 1rem;
}

/* 侧边栏整体样式 */
.video-aside__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 0;
  border-bottom: 1px solid hsl(var(--border) / 0.5);
  margin-bottom: 1rem;
}

.video-aside__title {
  font-size: 1rem;
  font-weight: 700;
  color: hsl(var(--foreground));
}

.video-aside__status {
  font-size: 0.7rem;
  color: hsl(var(--primary) / 0.6);
  font-family: 'JetBrains Mono', monospace;
}

.related-videos-list {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

/* 视频元数据区域 */
.video-meta {
  margin-top: 0.875rem;
}

/* 标题 */
.video-meta__title {
  font-size: clamp(1rem, 1rem + 0.3rem, 1.2rem);
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.4;
  word-break: break-word;
  color: hsl(var(--foreground));
  margin-bottom: 0.75rem;
}

/* 信息行：频道 + 操作按钮 */
.video-meta__info-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

/* 频道信息 */
.video-channel {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.video-channel__primary {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.video-channel__avatar-wrapper {
  flex-shrink: 0;
}

.video-channel__avatar {
  width: 2.5rem !important;
  height: 2.5rem !important;
  border-radius: calc(var(--radius-sm) - 1px);
  border: 2px solid hsl(var(--border));
}

.video-channel__identity {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  min-width: 0;
}

.video-channel__name {
  font-size: 0.9rem;
  font-weight: 600;
  color: hsl(var(--foreground));
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.video-channel__name:hover {
  color: hsl(var(--primary));
}

.video-channel__stats {
  font-size: 0.7rem;
  color: hsl(var(--muted-foreground));
}

/* 订阅按钮 */
.subscribe-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.4rem 0.875rem;
  border-radius: 20px;
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
  font-size: 0.75rem;
  font-weight: 600;
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.subscribe-btn:hover {
  background: hsl(var(--primary) / 0.9);
}

.subscribe-btn__icon {
  width: 14px;
  height: 14px;
}

/* 操作按钮 - 靠右 */
.video-meta__actions {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  margin-left: auto;
  flex-wrap: nowrap;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.4rem 0.75rem;
  border-radius: 20px;
  background: hsl(var(--accent) / 0.1);
  color: hsl(var(--foreground) / 0.7);
  font-size: 0.75rem;
  font-weight: 500;
  border: 1px solid hsl(var(--border) / 0.4);
  cursor: pointer;
  transition: all 0.2s ease;
  text-decoration: none;
  flex-shrink: 0;
}

.action-btn:hover {
  background: hsl(var(--accent) / 0.2);
  color: hsl(var(--foreground));
  border-color: hsl(var(--border));
}

.action-btn.is-active {
  background: hsl(var(--primary) / 0.12);
  color: hsl(var(--primary));
  border-color: hsl(var(--primary) / 0.4);
}

.action-btn__icon {
  width: 16px;
  height: 16px;
  opacity: 0.8;
}

.action-btn.is-active .action-btn__icon {
  opacity: 1;
}

/* 特殊色调 */
.action-btn.tone-like.is-active {
  background: hsl(142 76% 36% / 0.12);
  color: hsl(142 76% 36%);
  border-color: hsl(142 76% 36% / 0.4);
}

.action-btn.tone-danger.is-active {
  background: hsl(var(--destructive) / 0.12);
  color: hsl(var(--destructive));
  border-color: hsl(var(--destructive) / 0.4);
}

.action-btn.tone-later.is-active {
  background: hsl(var(--accent) / 0.12);
  color: hsl(var(--accent));
  border-color: hsl(var(--accent) / 0.4);
}

/* 响应式适配 */
@media (max-width: 640px) {
  .video-channel__avatar {
    width: 2.25rem !important;
    height: 2.25rem !important;
  }

  .video-channel__name {
    font-size: 0.85rem;
  }

  .action-btn {
    padding: 0.35rem 0.6rem;
    font-size: 0.7rem;
    gap: 0.25rem;
  }

  .action-btn__icon {
    width: 14px;
    height: 14px;
  }
}

/* 过渡动画 */
.fade-player-enter-active {
  transition: opacity 0.5s ease;
}
.fade-player-enter-from {
  opacity: 0;
}

.related-list-enter-active {
  transition: all 0.3s ease;
}
.related-list-enter-from {
  opacity: 0;
  transform: translateY(10px);
}
</style>
