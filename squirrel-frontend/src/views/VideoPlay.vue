<template>
  <div ref="videoPageRef" class="video-page bg-bg-primary scrollbar-hide" :class="{ 'is-widescreen': isWidescreen }">
    <div :class="['video-page__container', isWidescreen ? 'is-widescreen' : '']">
      <!-- 左侧主内容区域 -->
      <div :class="['video-main', isWidescreen ? 'is-widescreen' : '']">
        <!-- 视频播放区域 -->
        <div ref="videoSectionRef" class="video-section">
          <div class="video-container">
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
              :theme-options="{ persist: true, storageKey: 'sp-theme' }"
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
        </div>

        <!-- 视频信息区域 -->
        <div ref="videoMetaRef" class="video-meta">
          <!-- 标题与操作按钮 -->
          <transition name="fade" mode="out-in">
            <div :key="video?.id" class="video-meta__header">
              <h1 class="video-meta__title text-text-primary">{{ video?.title }}</h1>

              <!-- 操作按钮组 -->
              <div class="video-meta__actions">
                <template v-for="action in videoPrimaryActions" :key="action.key">
                  <a
                    v-if="action.href"
                    :href="action.href"
                    target="_blank"
                    rel="noopener noreferrer"
                    :class="[
                      'video-action',
                      `video-action--${action.variant}`,
                      action.active ? 'is-active' : '',
                      action.active ? `is-active--${action.tone}` : ''
                    ]"
                    :aria-label="action.label"
                    :title="action.label"
                  >
                    <Icon :icon="action.icon" class="video-action__icon" />
                    <span class="video-action__label">{{ action.label }}</span>
                  </a>
                  <button
                    v-else
                    type="button"
                    :class="[
                      'video-action',
                      `video-action--${action.variant}`,
                      action.active ? 'is-active' : '',
                      action.active ? `is-active--${action.tone}` : ''
                    ]"
                    :aria-pressed="action.active ? 'true' : 'false'"
                    :title="action.label"
                    @click="handlePrimaryAction(action)"
                  >
                    <Icon :icon="action.icon" class="video-action__icon" />
                    <span class="video-action__label">{{ action.label }}</span>
                  </button>
                </template>

                <div ref="moreOptionsRef" class="relative">
                  <button
                    type="button"
                    @click="handleMoreOptionsClick"
                    class="video-action video-action--secondary"
                    :aria-expanded="showMoreOptions ? 'true' : 'false'"
                    aria-haspopup="menu"
                  >
                    <Icon icon="material-symbols:more-horiz" class="video-action__icon" />
                    <span class="video-action__label">更多</span>
                  </button>

                  <div
                    v-if="showMoreOptions"
                    class="video-action-menu"
                    @click.stop
                  >
                    <button
                      v-for="action in videoOverflowActions"
                      :key="action.key"
                      type="button"
                      class="video-action-menu__item"
                      :class="[
                        action.active ? 'is-active' : '',
                        action.active ? `is-active--${action.tone}` : ''
                      ]"
                      :aria-pressed="action.active ? 'true' : 'false'"
                      @click="handleOverflowAction(action)"
                    >
                      <span class="video-action-menu__main">
                        <Icon :icon="action.icon" class="video-action-menu__icon" />
                        <span class="video-action-menu__label">{{ action.label }}</span>
                      </span>
                      <span v-if="action.hint" class="video-action-menu__hint">{{ action.hint }}</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </transition>

          <!-- 频道信息 -->
          <transition name="fade" mode="out-in">
            <div :key="video?.id" class="video-channel mt-3 pb-3 border-b border-border-primary">
              <div v-if="video?.subscriptions?.length" class="flex flex-col space-y-3">
                <!-- 主订阅：完整行展示 -->
                <div class="video-channel__primary">
                  <img
                    :src="getAvatarSrc(video.subscriptions[0].avatar, video.subscriptions[0].id)"
                    :alt="video.subscriptions[0].name"
                    class="w-8 h-8 md:w-9 md:h-9 lg:w-10 lg:h-10 rounded-full object-cover"
                    referrerpolicy="no-referrer"
                    @error="(e) => handleAvatarError(e, video.subscriptions[0].id)"
                  >
                  <router-link
                    :to="`/subscription/${video.subscriptions[0].id}/all`"
                    class="video-channel__name text-xs md:text-sm lg:text-base text-text-primary font-medium hover:text-color-info transition-colors"
                  >
                    {{ video.subscriptions[0].name }}
                  </router-link>
                  <button
                    class="video-channel__unsubscribe px-3 py-1.5 text-xs bg-bg-elevated hover:bg-bg-hover text-text-primary rounded-full transition-colors font-medium"
                    @click.stop="handleUnsubscribe(video.subscriptions[0].id)"
                    :title="`取消订阅 ${video.subscriptions[0].name}`"
                    :aria-label="`取消订阅 ${video.subscriptions[0].name}`"
                  >取消订阅</button>
                </div>

                <!-- 主订阅统计信息 -->
                <div class="video-channel__stats text-2xs text-text-muted mt-1">
                  <span>
                    总视频: {{ video.subscriptions[0].total_videos || 0 }} | 已解析: {{ video.subscriptions[0].total_extract || 0 }}
                  </span>
                  <span v-if="video?.publish_date"> · {{ formatDate(video.publish_date) }}发布</span>
                </div>

                <!-- 额外订阅：紧凑 chip 风格 -->
                <div
                  v-if="video.subscriptions.length > 1"
                  class="video-channel__more flex flex-wrap gap-2 mt-3"
                >
                  <div
                    v-for="sub in video.subscriptions.slice(1)"
                    :key="sub.id"
                    class="flex items-center px-2 py-1 rounded-full bg-bg-tertiary/50 hover:bg-bg-tertiary/70 cursor-pointer transition-colors text-xs text-text-primary"
                    @click.stop="$router.push(`/subscription/${sub.id}/all`)"
                  >
                    <img
                      :src="getAvatarSrc(sub.avatar, sub.id)"
                      :alt="sub.name"
                      class="w-5 h-5 rounded-full object-cover mr-2"
                      referrerpolicy="no-referrer"
                      @error="(e) => handleAvatarError(e, sub.id)"
                    >
                    <span class="truncate max-w-[140px]">{{ sub.name }}</span>
                  </div>
                </div>
              </div>
            </div>
          </transition>

        </div>
      </div>

      <!-- 右侧区域 - 相关视频 -->
      <div :class="['video-aside', isWidescreen ? 'hidden' : '']">
        <div>
          <div class="video-aside__panel rounded-xl pb-4 pt-0 flex flex-col">
            <h2 class="text-text-primary text-base md:text-lg mb-4">相关视频</h2>
            <div>
              <div v-if="!relatedVideos.length && !loadingRelated" class="text-text-muted text-sm">暂无推荐</div>
              <div v-if="relatedVideos.length" class="related-videos-list space-y-3">
                <div
                  v-for="relatedVideo in relatedVideos"
                  :key="relatedVideo.id"
                  class="flex space-x-3 cursor-pointer group"
                  @click="goToVideo(relatedVideo.id, relatedVideo)"
                >
                  <div class="relative h-20 w-32 rounded-lg overflow-hidden bg-bg-tertiary/60 transform-gpu sm:h-24 sm:w-40">
                    <img
                      v-if="relatedVideo.thumbnail && !relatedThumbnailErrorIds.has(relatedVideo.id)"
                      :src="relatedVideo.thumbnail"
                      referrerpolicy="no-referrer"
                      class="w-full h-full object-cover transform-gpu will-change-transform transition-transform duration-200 group-hover:scale-105 pointer-events-none select-none"
                      draggable="false"
                      :alt="relatedVideo.title"
                      @error="() => relatedThumbnailErrorIds.add(relatedVideo.id)"
                    >
                    <div
                      v-else
                      class="w-full h-full absolute top-0 left-0 bg-bg-secondary flex items-center justify-center"
                    >
                      <div class="text-text-muted flex flex-col items-center">
                        <Icon icon="material-symbols:image" class="text-3xl mb-1" />
                        <span class="text-2xs">暂无封面</span>
                      </div>
                    </div>
                    <div class="absolute bottom-1 right-1 bg-bg-tertiary/70 text-text-primary text-2xs px-1 py-0.5 rounded">
                      {{ formatDuration(relatedVideo.duration) }}
                    </div>
                  </div>
                  <div class="flex-1 min-w-0">
                    <div class="text-text-primary text-xs leading-5 max-h-10 overflow-hidden group-hover:text-color-info transition-colors">
                      {{ relatedVideo.title }}
                    </div>
                    <div class="text-text-muted text-2xs mt-1 truncate">
                      <router-link
                        v-if="relatedVideo.subscriptions?.[0]?.id"
                        :to="`/subscription/${relatedVideo.subscriptions[0].id}/all`"
                        @click.stop
                        class="hover:text-color-info transition-colors"
                      >
                        {{ relatedVideo.subscriptions[0].name }}
                      </router-link>
                      <span v-else>
                        {{ relatedVideo.site }}
                      </span>
                    </div>
                    <div
                      v-if="relatedVideo.uploaded_at"
                      class="text-text-tertiary text-2xs mt-0.5 truncate"
                    >
                      {{ formatDate(relatedVideo.uploaded_at) }}
                    </div>
                  </div>
                </div>
              </div>
            </div>
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
import { useDropdown } from '@/composables/useDropdown';
import VideoPlayer from '@/components/video-player/VideoPlayer.vue';
import { LocalStorageAdapter } from '@/components/video-player/core';
import { Icon } from '@iconify/vue';
import useVideoHistory from "../composables/useVideoHistory";
import { formatDate, formatDuration } from '../utils/dateFormat';
import useVideoInteraction from '../composables/useVideoInteraction';
import { useImageFallback } from '../composables/useImageFallback';
import { Logger } from '@/utils/logger'
import { getRandomVideo, unsubscribe as apiUnsubscribe } from '@/api'




const route = useRoute();
const router = useRouter();
const emitter = inject('emitter');
const { getImageSrc: getAvatarSrc, handleImageError: handleAvatarError } = useImageFallback();

const playerAdapter = new LocalStorageAdapter();


// 内部切换不使用 router，所以不需要从 history.state 读取初始数据
const { video, startTime, relatedVideos, loadingRelated, playbackSource, subtitleTracks, loadAndPlayById, externalError } = usePlaybackOrchestrator(null);
const { sendReport } = useVideoHistory();
const { INTERACTION_TYPE, toggleLike, deleteInteraction } = useVideoInteraction();
const { onVideoPlay, onVideoPause, onVideoEnded, onVideoTimeUpdate } = usePlaybackReporting(video, sendReport);
const {
  isOpen: showMoreOptions,
  rootRef: moreOptionsRef,
  toggle: toggleMoreOptions,
  close: closeMoreOptions,
} = useDropdown({ closeOnEscape: true });

const handleMoreOptionsClick = (event) => {
  event.stopPropagation();
  toggleMoreOptions();
};

const currentInteractionType = computed(() => video.value?.interaction_type ?? null);

const videoPrimaryActions = computed(() => {
  const actions = [
    {
      key: 'like',
      label: currentInteractionType.value === INTERACTION_TYPE.LIKE ? '已喜欢' : '喜欢',
      icon: currentInteractionType.value === INTERACTION_TYPE.LIKE ? 'material-symbols:thumb-up' : 'material-symbols:thumb-up-outline',
      active: currentInteractionType.value === INTERACTION_TYPE.LIKE,
      tone: 'like',
      variant: 'primary',
      onClick: () => video.value && handleLike(video.value, INTERACTION_TYPE.LIKE)
    },
    {
      key: 'later',
      label: currentInteractionType.value === INTERACTION_TYPE.LATER ? '已稍后看' : '稍后看',
      icon: currentInteractionType.value === INTERACTION_TYPE.LATER ? 'material-symbols:schedule' : 'material-symbols:schedule-outline',
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
      icon: 'material-symbols:open-in-new',
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
    },
    {
      key: 'dislike',
      label: currentInteractionType.value === INTERACTION_TYPE.DISLIKE ? '取消不喜欢' : '不喜欢',
      icon: currentInteractionType.value === INTERACTION_TYPE.DISLIKE ? 'material-symbols:thumb-down' : 'material-symbols:thumb-down-outline',
      active: currentInteractionType.value === INTERACTION_TYPE.DISLIKE,
      tone: 'danger',
      hint: currentInteractionType.value === INTERACTION_TYPE.DISLIKE ? '当前' : '',
      onClick: () => video.value && handleLike(video.value, INTERACTION_TYPE.DISLIKE)
    }
  ];
});

const handlePrimaryAction = async (action) => {
  if (action.href || !action.onClick) return;
  await action.onClick();
};

const handleOverflowAction = async (action) => {
  closeMoreOptions();
  if (!action.onClick) return;
  await action.onClick();
};


// 视频播放器引用
const videoPlayerRef = ref(null);
const videoPageRef = ref(null);
const videoSectionRef = ref(null);
const videoMetaRef = ref(null);
let metaResizeObserver = null;

const syncVideoMetaHeight = () => {
  const root = document.documentElement;
  const metaEl = videoMetaRef.value;
  const sectionEl = videoSectionRef.value;
  if (!metaEl || !sectionEl) return;

  const metaHeight = Math.ceil(metaEl.getBoundingClientRect().height);
  const sectionRect = sectionEl.getBoundingClientRect();
  const sectionTop = sectionRect.top;
  const sectionHeight = Math.ceil(sectionRect.height);
  const viewportHeight = window.innerHeight || document.documentElement.clientHeight;
  const availableHeight = Math.max(0, Math.floor(viewportHeight - sectionTop));

  root.style.setProperty('--video-meta-height', `${metaHeight}px`);
  root.style.setProperty('--video-page-available-height', `${availableHeight}px`);
  root.style.setProperty('--related-panel-height', `${sectionHeight}px`);
};

const handleResize = () => syncVideoMetaHeight();

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
  if (!subscriptionId) return;
  try {
    await apiUnsubscribe(subscriptionId);
  } catch (e) {}
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

  await nextTick();
  syncVideoMetaHeight();
  window.addEventListener('resize', handleResize);
  if (videoMetaRef.value) {
    metaResizeObserver = new ResizeObserver(() => {
      syncVideoMetaHeight();
    });
    metaResizeObserver.observe(videoMetaRef.value);
  }

  setWidescreenClass(isWidescreen.value);
  syncWidescreenSidebarState(isWidescreen.value);
});

watch(() => route.params.videoId, async (newId, oldId) => {
  // 只有从外部导航进来才需要重新加载
  // 内部切换（goToVideo）已经调用了loadAndPlayById，不需要重复加载
  if (newId && newId !== oldId && video.value?.id !== newId) {
    await loadAndPlayById(newId);
    await focusVideoPlayer();
    await nextTick();
    syncVideoMetaHeight();
  }
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  if (metaResizeObserver) {
    metaResizeObserver.disconnect();
    metaResizeObserver = null;
  }
  setWidescreenClass(false);
  syncWidescreenSidebarState(false);
});

</script>

<style scoped>
.video-page {
  min-height: 100%;
}

/* 视频页面容器对齐其它页面 */
.video-page__container {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  max-width: min(1840px, calc(100vw - 32px));
  margin: 0 auto;
  width: 100%;
  padding: 0.75rem 0.75rem calc(var(--mobile-nav-height, 64px) + 1rem);
  --video-main-offset: 0px;
  --video-aside-width: clamp(320px, 22vw, 360px);
}

.video-page__container.is-widescreen {
  --video-main-offset: 0px;
}

.video-page__container.is-widescreen {
  max-width: 100%;
  padding-left: 0;
  padding-right: 0;
  padding-top: 0;
  padding-bottom: 0;
}

.video-page__container.is-widescreen .video-section {
  border-radius: 0;
}

@media (min-width: 640px) {
  .video-page__container {
    gap: 1.25rem;
    padding-left: 1.5rem;
    padding-right: 1.5rem;
    padding-bottom: 1.5rem;
  }
}

@media (min-width: 1024px) {
  .video-page__container {
    gap: 1.5rem;
    padding-left: 2rem;
    padding-right: 2rem;
    padding-bottom: 2rem;
  }
}

@media (min-width: 1280px) {
  .video-page__container {
    flex-direction: row;
    align-items: flex-start;
    --video-main-offset: 16px;
  }
}

.video-main {
  flex: 1 1 auto;
  min-width: 0;
  width: 100%;
  max-width: 100%;
  margin-left: auto;
  margin-right: auto;
  transform: none;
}

@media (min-width: 1280px) {
  .video-main {
    flex: 1 1 0%;
    max-width: clamp(1200px, 78vw, 1440px);
    transform: translateX(var(--video-main-offset, 0px));
  }
}

.video-main.is-widescreen {
  max-width: 100%;
  transform: none;
}

.video-main.is-widescreen .video-container {
  aspect-ratio: auto;
  height: min(
    calc(var(--video-page-available-height, 100vh) - var(--video-meta-height, 0px) - 24px - 12px),
    calc(100vw * 9 / 16)
  );
  max-height: min(
    calc(var(--video-page-available-height, 100vh) - var(--video-meta-height, 0px) - 24px - 12px),
    calc(100vw * 9 / 16)
  );
  padding-bottom: 0; /* 覆盖 16:9 padding hack，避免高度叠加 */
  min-height: 0;
}

.video-main:not(.is-widescreen) .video-container {
  height: auto;
  max-height: none;
}


.video-aside {
  width: 100%;
  flex: none;
}

.video-aside__panel {
  padding-left: 0;
  padding-right: 0;
}

.related-videos-list {
  max-height: none;
  overflow: visible;
  padding-right: 0;
}

.related-videos-list::-webkit-scrollbar {
  width: 6px;
}

.related-videos-list::-webkit-scrollbar-thumb {
  background: var(--border-primary);
  border-radius: 999px;
}

.related-videos-list::-webkit-scrollbar-track {
  background: transparent;
}

@media (min-width: 1280px) {
  .video-aside {
    width: var(--video-aside-width, 360px);
    flex: 0 0 var(--video-aside-width, 360px);
  }

  .video-aside__panel {
    padding-left: 1rem;
    padding-right: 1rem;
  }

  .related-videos-list {
    max-height: var(--related-panel-height, 75vh);
    overflow-y: auto;
    padding-right: 6px;
  }
}

@media (min-width: 1280px) {
  .video-page__container {
    --video-aside-width: clamp(340px, 24vw, 420px);
  }

  .video-main {
    max-width: clamp(1260px, 72vw, 1500px);
  }
}

@media (min-width: 1536px) {
  .video-page__container {
    --video-aside-width: clamp(380px, 22vw, 460px);
  }

  .video-main {
    max-width: clamp(1320px, 70vw, 1560px);
  }
}


/* 视频区域容器样式 */
.video-section {
  position: relative;
  width: 100%;
  background: var(--bg-media);
  margin: 0 auto;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: none;
}









.video-container {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  background: var(--bg-media);
}

.video-container :deep(iframe),
.video-container :deep(video),
.video-container :deep(.xgplayer) {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: var(--bg-media);
}

.video-meta {
  margin-top: 0.75rem;
}

.video-meta__header {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.75rem;
}

.video-meta__title {
  width: 100%;
  font-size: clamp(0.9375rem, 0.88rem + 0.3vw, 1.0625rem);
  font-weight: 500;
  line-height: 1.6;
  word-break: break-word;
}

.video-meta__actions {
  display: flex;
  width: 100%;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.video-action {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  min-height: 2.5rem;
  padding: 0 0.875rem;
  border: 1px solid var(--border-primary);
  border-radius: 9999px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  transition: background-color 0.18s ease, border-color 0.18s ease, color 0.18s ease, transform 0.18s ease;
}

.video-action:hover {
  background: var(--bg-elevated);
  border-color: var(--border-secondary);
  transform: translateY(-1px);
}

.video-action--secondary {
  background: transparent;
}

.video-action__icon {
  width: 1.125rem;
  height: 1.125rem;
  flex-shrink: 0;
}

.video-action__label {
  font-size: var(--font-size-xs);
  font-weight: 500;
  white-space: nowrap;
}

.video-action.is-active--like {
  color: #fff5f5;
  background: rgba(var(--color-primary-rgb), 0.16);
  border-color: rgba(var(--color-primary-rgb), 0.42);
}

.video-action.is-active--later {
  color: #dbeafe;
  background: rgba(59, 130, 246, 0.18);
  border-color: rgba(59, 130, 246, 0.36);
}

.video-action-menu {
  position: absolute;
  right: 0;
  top: calc(100% + 0.5rem);
  z-index: 50;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  min-width: 13rem;
  padding: 0.375rem;
  border: 1px solid var(--border-primary);
  border-radius: 1rem;
  background: var(--bg-card);
  box-shadow: var(--shadow-popup);
}

.video-action-menu__item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  width: 100%;
  min-height: 2.75rem;
  padding: 0.625rem 0.75rem;
  border: 1px solid transparent;
  border-radius: 0.75rem;
  background: transparent;
  color: var(--text-primary);
  text-align: left;
  transition: background-color 0.18s ease, border-color 0.18s ease, color 0.18s ease;
}

.video-action-menu__item:hover {
  background: var(--bg-elevated);
  border-color: var(--border-primary);
}

.video-action-menu__main {
  display: inline-flex;
  align-items: center;
  gap: 0.625rem;
  min-width: 0;
}

.video-action-menu__icon {
  width: 1.125rem;
  height: 1.125rem;
  flex-shrink: 0;
}

.video-action-menu__label {
  font-size: var(--font-size-xs);
  font-weight: 500;
}

.video-action-menu__hint {
  font-size: var(--font-size-2xs);
  color: var(--text-muted);
}

.video-action-menu__item.is-active--danger {
  background: rgba(239, 68, 68, 0.14);
  border-color: rgba(239, 68, 68, 0.24);
  color: #fee2e2;
}

.video-channel__primary {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.video-channel__name {
  min-width: 0;
  flex: 1 1 140px;
}

.video-channel__unsubscribe {
  flex-shrink: 0;
}

.video-channel__stats,
.video-channel__more {
  margin-left: 0;
}

@media (min-width: 768px) {
  .video-meta__header {
    flex-direction: row;
    justify-content: space-between;
  }

  .video-meta__title {
    flex: 1 1 360px;
    min-width: 0;
    padding-right: 1rem;
  }

  .video-meta__actions {
    width: auto;
    justify-content: flex-end;
    max-width: min(100%, 28rem);
  }

  .video-channel__stats,
  .video-channel__more {
    margin-left: 2.75rem;
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

  .video-meta__actions {
    gap: 0.375rem;
  }

  .video-action {
    padding: 0 0.75rem;
  }

  .video-action__label {
    font-size: var(--font-size-2xs);
  }

  .video-action-menu {
    min-width: min(13rem, calc(100vw - 2rem));
    max-width: calc(100vw - 1.5rem);
  }
}

@supports not (aspect-ratio: 1 / 1) {
  .video-container {
    height: 0;
    padding-bottom: 56.25%;
  }
}


/* 平滑过渡动画 - 快速淡入淡出 */
.fade-enter-active {
  transition: opacity 0.1s ease-out;
}

.fade-leave-active {
  transition: opacity 0.08s ease-in;
}

.fade-enter-from, .fade-leave-to {
  opacity: 0;
}

.fade-enter-to, .fade-leave-from {
  opacity: 1;
}
</style>
