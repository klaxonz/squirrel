<template>
  <div ref="videoPageRef" class="video-page terminal-viewport scrollbar-hide" :class="{ 'is-widescreen': isWidescreen }">
    <div :class="['video-page__container', isWidescreen ? 'is-widescreen' : '']">
      <!-- 左侧主内容区域 -->
      <div :class="['video-main', isWidescreen ? 'is-widescreen' : '']">
        <!-- 视频播放区域 -->
        <div ref="videoSectionRef" class="video-section">
          <div class="video-container">
            <Transition name="fade-player" appear>
              <div class="viewfinder-box">
                <div class="viewfinder-label">[正在监视]</div>
                <div class="viewfinder-corner viewfinder-corner--top-left"></div>
                <div class="viewfinder-corner viewfinder-corner--top-right"></div>
                <div class="viewfinder-corner viewfinder-corner--bottom-left"></div>
                <div class="viewfinder-corner viewfinder-corner--bottom-right"></div>
                <VideoPlayer
                  ref="videoPlayerRef"
                  v-if="video"
                  :source="playbackSource"
                  :subtitles="subtitleTracks"
                  :poster="video?.thumbnail"
                  :title="video?.title"
                  :initialTime="startTime"
                  :has-prev="hasPrevVideo"
                  :has-next="hasNextVideo"
                  :external-error="externalError"
                  :widescreen="isWidescreen"
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
              <!-- 标题 -->
              <h1 class="video-meta__title">
                {{ video?.title }}
              </h1>

              <div class="video-meta__header">
                <!-- 频道信息与订阅按钮 -->
                <div class="video-channel">
                  <div class="video-channel__primary">
                    <div class="video-channel__avatar-wrapper">
                      <img
                        v-if="video?.subscriptions?.[0]"
                        :src="getAvatarSrc(video.subscriptions[0].avatar, video.subscriptions[0].id)"
                        :alt="video.subscriptions[0].name"
                        class="video-channel__avatar"
                        :class="{ 'image-loaded': videoAvatarLoaded }"
                        referrerpolicy="no-referrer"
                        @load="videoAvatarLoaded = true"
                        @error="(e) => handleAvatarError(e, video.subscriptions[0].id)"
                      >
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
                    <button
                      v-if="video?.subscriptions?.[0]"
                      class="video-action video-action--primary is-active"
                      @click.stop="handleUnsubscribe(video.subscriptions[0].id)"
                    >
                      <span class="video-action__label">订阅</span>
                    </button>
                  </div>
                </div>

                <!-- 操作按钮组 -->
                <div class="video-meta__actions">
                  <template v-for="action in videoActions" :key="action.key">
                    <button
                      v-if="!action.href"
                      class="video-action video-action--secondary"
                      :class="{ 'is-active': action.active }"
                      @click="handleVideoAction(action)"
                    >
                      <Icon :icon="action.icon" class="video-action__icon" />
                      <span class="video-action__label">{{ action.label }}</span>
                    </button>
                    <a
                      v-else
                      :href="action.href"
                      target="_blank"
                      class="video-action video-action--secondary"
                    >
                      <Icon :icon="action.icon" class="video-action__icon" />
                      <span class="video-action__label">{{ action.label }}</span>
                    </a>
                  </template>
                </div>
              </div>
            </div>
            <div v-else class="video-meta-skeleton">
              <div class="skeleton-title w-3/4 h-8 bg-white/5 rounded"></div>
              <div class="flex items-center justify-between mt-6">
                <div class="flex items-center gap-3">
                  <div class="w-10 h-10 rounded-full bg-white/5"></div>
                  <div class="space-y-2">
                    <div class="w-24 h-4 bg-white/5 rounded"></div>
                    <div class="w-16 h-3 bg-white/5 rounded"></div>
                  </div>
                </div>
                <div class="flex gap-2">
                  <div v-for="i in 4" :key="i" class="w-20 h-8 bg-white/5 rounded"></div>
                </div>
              </div>
            </div>
          </Transition>
        </div>
      </div>

      <!-- 右侧区域 - 相关视频 -->
      <div :class="['video-aside', isWidescreen ? 'hidden' : '']">
        <div class="video-aside__panel">
          <div class="video-aside__header">
            <h2 class="video-aside__title">相关视频</h2>
            <div class="video-aside__status">[链路已建立]</div>
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
import VideoPlayer from '@/components/video-player/VideoPlayer.vue';
import RelatedVideoSkeleton from '@/components/video-player/RelatedVideoSkeleton.vue';
import { LocalStorageAdapter } from '@/components/video-player/core';
import { Icon } from '@iconify/vue';
import useVideoHistory from "../composables/useVideoHistory";
import { formatDate, formatDuration } from '../utils/dateFormat';
import { formatVideoCardId } from '@/utils/videoCard';
import useVideoInteraction from '../composables/useVideoInteraction';
import { useImageFallback } from '../composables/useImageFallback';
import { Logger } from '@/utils/logger'
import { getRandomVideo, unsubscribe as apiUnsubscribe } from '@/api'




const route = useRoute();
const router = useRouter();
const emitter = inject('emitter');
const { getImageSrc: getAvatarSrc, handleImageError: handleAvatarError } = useImageFallback();

const playerAdapter = new LocalStorageAdapter();
const { effectiveTheme } = useAppTheme()


// 内部切换不使用 router，所以不需要从 history.state 读取初始数据
const { video, startTime, relatedVideos, loadingRelated, playbackSource, subtitleTracks, loadAndPlayById, externalError } = usePlaybackOrchestrator(null);
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
const videoAvatarLoaded = ref(false)
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
  videoAvatarLoaded.value = false
})

watch(() => relatedVideos.value, () => {
  Object.keys(relatedImagesLoaded).forEach(key => delete relatedImagesLoaded[key])
}, { deep: true })

onUnmounted(() => {
  setWidescreenClass(false);
  syncWidescreenSidebarState(false);
});

</script>

<style scoped>
.terminal-viewport {
  background-color: #050505;
  background-image: 
    linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), 
    linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06));
  background-size: 100% 2px, 3px 100%;
  color: rgba(255, 255, 255, 0.8);
}

.video-page {
  min-height: 100%;
}

/* 视频页面容器对齐其它页面 */
.video-page__container {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  max-width: 1720px; /* YouTube 风格的最大宽度约束 */
  margin: 0 auto;
  width: 100%;
  padding: 1rem;
}

@media (min-width: 1280px) {
  .video-page__container {
    display: grid;
    /* 左侧主内容占大头，右侧相关视频固定宽度 */
    grid-template-columns: minmax(0, 1fr) 400px;
    align-items: start;
    padding: 1.5rem 2rem;
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
  /* 移除之前的 padding 和 border，让视频更沉浸 */
}

.video-container {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  background: #000;
}

/* 优化取景框，使其成为轻量级叠加层而非容器 */
.viewfinder-box {
  position: absolute;
  inset: 0;
  padding: 0;
  z-index: 5;
  pointer-events: none;
}

.video-container :deep(.sp-player) {
  border-radius: 0; /* 视频内部填满容器 */
}

.video-meta {
  margin-top: 1rem;
  padding: 0;
}

.video-meta__title {
  font-size: 1.25rem;
  font-weight: 700;
  line-height: 1.4;
  margin-bottom: 0.75rem;
  color: #fff;
}

/* 重新排列：频道信息和操作按钮在同一行 */
.video-meta__header {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

@media (min-width: 768px) {
  .video-meta__header {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
  }
}

.video-channel {
  padding: 0;
  border: none;
}

.video-channel__primary {
  gap: 0.75rem;
}

.video-channel__avatar {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 50%;
  object-fit: cover;
  opacity: 0;
  transition: opacity 0.5s ease;
}

.video-channel__avatar.image-loaded {
  opacity: 1;
}

.video-meta__actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0;
  border: none;
}

.video-aside {
  width: 100%;
}

@media (min-width: 1280px) {
  .video-aside {
    position: sticky;
    top: 1.5rem;
  }
}

.video-aside__panel {
  height: auto;
}

.related-video-card {
  grid-template-columns: 160px 1fr; /* 侧边栏卡片更宽一点，更像 YouTube */
  gap: 0.75rem;
  padding: 0.5rem 0;
  background: transparent;
  border: none;
}

.related-video-card:hover {
  background: rgba(255, 255, 255, 0.05);
  transform: none;
}

.related-video-card__thumb {
  border-radius: 8px;
}

.related-video-card__title {
  font-size: 0.875rem;
  font-weight: 600;
  -webkit-line-clamp: 2;
}


.video-aside__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.45rem 0.75rem; /* 减小头部内边距 */
  background: rgba(255, 77, 0, 0.04);
  border-bottom: 1px solid rgba(255, 77, 0, 0.15);
}

.video-aside__title {
  font-size: 0.72rem; /* 减小标题字号 */
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #ff4d00;
  font-family: 'JetBrains Mono', monospace;
}

.video-aside__status {
  font-size: 0.55rem; /* 减小状态字号 */
  color: rgba(255, 77, 0, 0.4);
  font-family: 'JetBrains Mono', monospace;
}

.video-aside__content {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem;
}

.video-aside__footer {
  height: 4px;
  background: linear-gradient(to right, #ff4d00 0%, transparent 100%);
  opacity: 0.3;
}

.related-videos-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem; /* 极致压缩间距 */
}

.related-video-card {
  position: relative;
  display: grid;
  grid-template-columns: 110px 1fr; /* 左侧固定宽度，右侧自适应 */
  gap: 0.6rem;
  padding: 0.25rem;
  border-radius: 3px;
  background: rgba(255, 255, 255, 0.015);
  border: 1px solid rgba(255, 255, 255, 0.03);
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.2, 0, 0.1, 1);
  align-items: flex-start;
}

@media (min-width: 1280px) {
  .related-video-card {
    grid-template-columns: 100px 1fr; /* 侧边栏更窄时微调比例 */
    padding: 0.25rem;
  }
}

/* 调整平板端的紧凑比例 */
@media (min-width: 640px) and (max-width: 1279px) {
  .related-video-card {
    grid-template-columns: 140px 1fr;
    gap: 0.8rem;
    padding: 0.35rem;
  }
}

.related-video-card:hover {
  background: rgba(255, 77, 0, 0.04);
  border-color: rgba(255, 77, 0, 0.2);
  transform: translateX(4px);
}


/* 视频区域容器样式 */
.video-section {
  position: relative;
  width: 100%;
  margin: 0 auto;
  background: transparent;
  border: none;
  border-radius: 0;
  overflow: hidden;
  box-shadow: none;
}

.video-container {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  background: transparent;
  border-radius: 0;
}

.viewfinder-box {
  position: relative;
  padding: 12px;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

@media (max-width: 640px) {
  .viewfinder-box {
    padding: 6px;
  }
}

.viewfinder-label {
  position: absolute;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  font-family: 'JetBrains Mono', 'Courier New', monospace;
  font-size: 0.68rem;
  color: #ff4d00;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  z-index: 10;
  text-shadow: 0 0 8px rgba(255, 77, 0, 0.4);
}

.viewfinder-corner {
  position: absolute;
  width: 15px;
  height: 15px;
  border: 1px solid #ff4d00;
  z-index: 10;
  pointer-events: none;
  box-shadow: 0 0 5px rgba(255, 77, 0, 0.2);
}

.viewfinder-corner--top-left { top: 0; left: 0; border-right: none; border-bottom: none; }
.viewfinder-corner--top-right { top: 0; right: 0; border-left: none; border-bottom: none; }
.viewfinder-corner--bottom-left { bottom: 0; left: 0; border-right: none; border-top: none; }
.viewfinder-corner--bottom-right { bottom: 0; right: 0; border-left: none; border-top: none; }

.video-container :deep(.sp-player) {
  background: hsl(var(--background));
  border-radius: 0;
  overflow: hidden;
}

.video-meta {
  margin-top: 0.875rem;
  padding: 0 12px;
}

@media (max-width: 640px) {
  .video-meta {
    padding: 0 6px;
  }
}

.video-meta__panel {
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
  padding: 0;
}

.video-meta__header {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.6rem;
}

.video-meta__eyebrow {
  display: flex;
  flex-wrap: wrap;
  gap: 0.2rem;
  margin-bottom: 0.45rem;
}

.video-meta__pill {
  display: inline-flex;
  align-items: center;
  min-height: 1.2rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.72rem;
  font-weight: 600;
}

.video-meta__title {
  width: 100%;
  font-size: clamp(0.96rem, 0.9rem + 0.2rem, 1.1rem);
  font-weight: 600;
  letter-spacing: -0.02em;
  line-height: 1.3;
  word-break: break-word;
  padding-bottom: 0.4rem; /* 减小底部 padding */
  border-bottom: none;
  margin-bottom: 0.4rem; /* 显著减小底部 margin */
}

.video-meta__eyebrow {
  display: flex;
  flex-wrap: wrap;
  gap: 0.2rem;
  margin-bottom: 0.25rem; /* 减小间距 */
}

.video-channel {
  padding: 0.25rem 0; /* 压缩频道区域高度 */
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.video-channel__avatar {
  width: 2.2rem; /* 缩小头像 */
  height: 2.2rem;
  border-radius: 50%;
  object-fit: cover;
}

.video-channel__name {
  font-size: 0.85rem; /* 稍微缩小字体 */
  font-weight: 600;
}

.video-meta__actions {
  display: flex;
  width: 100%;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.35rem;
  justify-content: flex-start;
  padding-top: 0.5rem; /* 压缩动作栏顶部间距 */
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}


.video-meta__title-prefix {
  opacity: 0.45;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.8em;
  margin-right: 0.5rem;
  color: #ff4d00;
}

.video-meta__actions {
  display: flex;
  width: 100%;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.4rem;
  justify-content: flex-start;
  padding-top: 0.75rem;
  border-top: 1px solid hsl(var(--border) / 0.68);
}

.video-action {
  display: inline-flex;
  align-items: center;
  gap: 0.24rem;
  min-height: 1.52rem;
  padding: 0 0.5rem;
  border-radius: 4px;
  color: rgba(255, 255, 255, 0.45);
  font-family: 'JetBrains Mono', monospace;
  text-transform: uppercase;
  font-size: 0.6rem;
  transition: all 0.2s;
}

.video-action:hover, .video-action.is-active {
  color: #ff4d00;
  background: rgba(255, 77, 0, 0.08);
}

.video-action__label::before { content: '['; opacity: 0.5; }
.video-action__label::after { content: ']'; opacity: 0.5; }

.video-channel {
  padding: 0.5rem 0;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.video-channel__primary {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.video-channel__avatar {
  width: 2.6rem;
  height: 2.6rem;
  border-radius: 50%;
  object-fit: cover;
}

.video-channel__name {
  font-size: 0.92rem;
  font-weight: 600;
}

.video-channel__unsubscribe {
  font-size: 0.6rem;
  color: rgba(255, 255, 255, 0.45);
}

.video-channel__stats {
  display: flex;
  gap: 0.6rem;
  font-size: 0.74rem;
  color: hsl(var(--muted-foreground));
}

.related-videos-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  overflow-y: auto;
  padding-right: 4px;
}

.related-video-card {
  position: relative;
  display: grid;
  grid-template-columns: 110px 1fr; /* 强制左封面右标题布局 */
  gap: 0.6rem;
  padding: 0.35rem;
  border-radius: 3px;
  background: rgba(255, 255, 255, 0.015);
  border: 1px solid rgba(255, 255, 255, 0.03);
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.2, 0, 0.1, 1);
  align-items: flex-start;
}

@media (min-width: 1280px) {
  .related-video-card {
    grid-template-columns: 100px 1fr; /* 侧边栏模式下微调 */
    padding: 0.35rem;
    flex-direction: row; /* 覆盖之前的 column */
  }
}

/* 调整平板端的布局比例 */
@media (min-width: 640px) and (max-width: 1279px) {
  .related-video-card {
    grid-template-columns: 140px 1fr;
    gap: 0.8rem;
    padding: 0.35rem;
  }
}


.related-video-card:hover {
  background: rgba(255, 77, 0, 0.04);
  border-color: rgba(255, 77, 0, 0.2);
  transform: translateX(4px);
}

.related-video-card__thumb {
  position: relative;
  overflow: hidden;
  border-radius: 2px;
  background: #000;
  aspect-ratio: 16 / 9;
  width: 100%;
}

.related-video-card__fallback {
  position: absolute;
  inset: 0;
  background: #0a0a0a;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.fallback-noise {
  position: absolute;
  inset: 0;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E");
  opacity: 0.05;
}

.fallback-content {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.3rem;
  z-index: 1;
}

.fallback-status {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.6rem;
  color: #ff4d00;
  letter-spacing: 0.3em;
  font-weight: 800;
  opacity: 0.6;
}

.fallback-id {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.5rem;
  color: rgba(255, 255, 255, 0.15);
  letter-spacing: 0.1em;
}

.related-video-card__image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0;
  transition: opacity 0.5s ease, transform 0.6s cubic-bezier(0.2, 0, 0.1, 1);
}

.related-video-card__image.image-loaded {
  opacity: 1;
}

.related-video-card:hover .related-video-card__image {
  transform: scale(1.08);
}

.related-video-card__scanline {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 2px;
  background: rgba(255, 77, 0, 0.3);
  box-shadow: 0 0 8px rgba(255, 77, 0, 0.6);
  opacity: 0;
  pointer-events: none;
  z-index: 5;
}

.related-video-card:hover .related-video-card__scanline {
  animation: scanline-anim 1.5s linear infinite;
  opacity: 1;
}

@keyframes scanline-anim {
  0% { top: 0; }
  100% { top: 100%; }
}

.related-video-card__data-overlay {
  position: absolute;
  top: 0.5rem;
  left: 0.5rem;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.15rem 0.4rem;
  background: rgba(0, 0, 0, 0.65);
  backdrop-filter: blur(4px);
  border-radius: 2px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.6rem;
  color: #ff4d00;
  border: 1px solid rgba(255, 77, 0, 0.2);
}

.related-video-card__status-dot {
  width: 5px;
  height: 5px;
  background: #ff4d00;
  border-radius: 50%;
  box-shadow: 0 0 6px #ff4d00;
  animation: status-pulse 1s ease infinite alternate;
}

@keyframes status-pulse {
  from { opacity: 0.4; }
  to { opacity: 1; }
}

.related-video-card__duration {
  position: absolute;
  right: 0.5rem;
  bottom: 0.5rem;
  padding: 0.15rem 0.35rem;
  background: rgba(0, 0, 0, 0.8);
  color: rgba(255, 255, 255, 0.85);
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.65rem;
  border-radius: 2px;
}

.related-video-card__title {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  font-size: 0.75rem; /* 极致字号压缩 */
  font-weight: 500;
  line-height: 1.3;
  color: hsl(var(--foreground));
  margin-bottom: 0.25rem;
}

.related-video-card__meta {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.58rem; /* 极致字号压缩 */
  color: rgba(255, 255, 255, 0.3);
}

.related-video-card__duration {
  position: absolute;
  right: 0.35rem;
  bottom: 0.35rem;
  padding: 0.05rem 0.25rem;
  background: rgba(0, 0, 0, 0.85);
  color: rgba(255, 255, 255, 0.9);
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.55rem;
  border-radius: 1px;
}

.related-video-card__data-overlay {
  position: absolute;
  top: 0.35rem;
  left: 0.35rem;
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.05rem 0.25rem;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(4px);
  border-radius: 1px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.5rem;
  color: #ff4d00;
  border: 1px solid rgba(255, 77, 0, 0.15);
}


.related-video-card__meta {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.65rem;
  color: rgba(255, 255, 255, 0.4);
}

.related-video-card__channel:hover {
  color: #ff4d00;
}

.video-aside__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0;
}

.video-aside__title {
  font-size: 1rem;
  font-weight: 600;
}


@media (min-width: 768px) {
  .video-meta__header {
    gap: 0.75rem;
  }

  .video-meta__title {
    padding-right: 0;
  }

  .video-meta__actions {
    width: 100%;
    max-width: none;
  }
}

@media (min-width: 1200px) {
  .video-meta__header {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: start;
    column-gap: 1rem;
  }

  .video-meta__copy {
    padding-right: 0.25rem;
  }

  .video-meta__actions {
    width: auto;
    max-width: min(28rem, 38vw);
    flex-wrap: nowrap;
    gap: 0.35rem;
    justify-content: flex-end;
    align-self: start;
    padding-top: 0;
    border-top: none;
  }

  .video-channel__primary {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    align-items: center;
  }
}

/* 滚动条样式统一到全局 .scrollbar */

.no-scrollbar {
  -ms-overflow-style: none;  /* IE and Edge */
  scrollbar-width: none;  /* Firefox */
}

.no-scrollbar::-webkit-scrollbar {
  display: none;  /* Chrome, Safari and Opera */
}

@media (max-width: 640px) {
  .video-section {
    border-radius: 0;
    box-shadow: none;
  }

  .video-container {
    height: auto;
    border-radius: 0;
    aspect-ratio: 16 / 9;
  }

  .video-container :deep(.sp-player) {
    border-radius: 0;
  }

  .video-meta__actions {
    gap: 0.375rem;
  }

  .video-action {
    min-height: 1.42rem;
    padding: 0 0.34rem;
  }

  .video-action__label {
    font-size: var(--font-size-2xs);
  }

  .video-meta__title {
    font-size: 0.9rem;
    margin-bottom: 0.75rem;
    padding-bottom: 0.5rem;
  }

  .video-meta__title-prefix {
    font-size: 0.7rem;
  }

  .video-channel {
    padding: 0.85rem;
  }

  .video-channel::before {
    font-size: 8px;
  }

  .video-channel__avatar-wrapper {
    font-size: 1.25rem;
  }

  .related-video-card__title {
    font-size: 0.78rem;
  }

  .related-video-card__channel,
  .related-video-card__date {
    font-size: 0.6rem;
  }
}

.related-video-card {
  grid-template-columns: minmax(6.8rem, 7.6rem) minmax(0, 1fr);
  gap: 0.7rem;
  padding: 0.45rem 0;
}

@supports not (aspect-ratio: 1 / 1) {
  .video-container {
    height: 0;
    padding-bottom: 56.25%;
  }
}


/* 平滑过渡动画 - 快速淡入淡出 */
.fade-meta-enter-active,
.fade-meta-leave-active,
.fade-aside-enter-active,
.fade-aside-leave-active,
.fade-player-enter-active {
  transition: opacity 0.5s ease, transform 0.5s cubic-bezier(0.2, 0, 0, 1);
}

.fade-meta-enter-from,
.fade-meta-leave-to,
.fade-aside-enter-from,
.fade-aside-leave-to,
.fade-player-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.related-list-enter-active {
  transition: all 0.4s ease;
}

.related-list-enter-from {
  opacity: 0;
  transform: translateX(10px);
}

.video-meta-skeleton {
  @apply animate-pulse;
}

.fade-enter-active {
  transition: opacity 0.15s cubic-bezier(0.2, 0, 0, 1), transform 0.15s cubic-bezier(0.2, 0, 0, 1);
}

.fade-leave-active {
  transition: opacity 0.1s cubic-bezier(0.2, 0, 0, 1), transform 0.1s cubic-bezier(0.2, 0, 0, 1);
}

.fade-enter-from {
  opacity: 0;
  transform: translateY(4px) scale(0.995);
}

.fade-leave-to {
  opacity: 0;
  transform: translateY(-4px) scale(0.995);
}

.channel-dismiss-enter-active,
.channel-dismiss-leave-active {
  transition: opacity 0.2s cubic-bezier(0.2, 0, 0, 1), transform 0.2s cubic-bezier(0.2, 0, 0, 1), max-height 0.2s ease;
  overflow: hidden;
}

.channel-dismiss-enter-from,
.channel-dismiss-leave-to {
  opacity: 0;
  transform: translateX(-10px);
  max-height: 0;
}

.channel-dismiss-enter-to,
.channel-dismiss-leave-from {
  opacity: 1;
  transform: translateX(0);
  max-height: 20rem;
}

@keyframes video-channel-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
