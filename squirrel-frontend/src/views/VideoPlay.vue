<template>
  <div ref="videoPageRef" class="video-page terminal-viewport scrollbar-hide" :class="{ 'is-widescreen': isWidescreen }">
    <div :class="['video-page__container', isWidescreen ? 'is-widescreen' : '']">
      <!-- 左侧主内容区域 -->
      <div :class="['video-main', isWidescreen ? 'is-widescreen' : '']">
        <!-- 视频播放区域 -->
        <div ref="videoSectionRef" class="video-section">
          <div class="video-container">
            <div class="viewfinder-box">
              <div class="viewfinder-label">[MONITOR_ACTIVE]</div>
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
          </div>
        </div>

        <!-- 视频信息区域 -->
        <div ref="videoMetaRef" class="video-meta">
          <div class="video-meta__panel">
            <!-- 标题与操作按钮 -->
            <transition name="fade" mode="out-in">
              <div :key="video?.id" class="video-meta__header">
                <div class="video-meta__copy">
                  <div
                    v-if="video?.site || video?.duration || video?.publish_date || relatedVideos.length"
                    class="video-meta__eyebrow"
                  >
                    <span v-if="video?.site" class="video-meta__pill">{{ video.site }}</span>
                    <span v-if="video?.duration" class="video-meta__pill">{{ formatDuration(video.duration) }}</span>
                    <span v-if="video?.publish_date" class="video-meta__pill">{{ formatDate(video.publish_date) }}</span>
                    <span v-if="relatedVideos.length" class="video-meta__pill video-meta__pill--muted">
                      推荐 {{ relatedVideos.length }}
                    </span>
                  </div>
                  <h1 class="video-meta__title text-foreground">
                    <span class="video-meta__title-prefix">[FILE_ENTRY]</span> {{ video?.title }}
                  </h1>
                  <transition name="channel-dismiss" mode="out-in">
                    <div v-if="video?.subscriptions?.length && isVideoChannelVisible" :key="`${video?.id}-${isVideoChannelVisible}`" class="video-channel">
                      <div class="video-channel__content">
                        <div class="video-channel__primary">
                          <div class="video-channel__avatar-wrapper">
                            <img
                              :src="getAvatarSrc(video.subscriptions[0].avatar, video.subscriptions[0].id)"
                              :alt="video.subscriptions[0].name"
                              class="video-channel__avatar"
                              referrerpolicy="no-referrer"
                              @error="(e) => handleAvatarError(e, video.subscriptions[0].id)"
                            >
                          </div>
                          <div class="video-channel__summary">
                            <div class="video-channel__identity">
                              <router-link
                                :to="`/subscription/${video.subscriptions[0].id}/all`"
                                class="video-channel__name"
                              >
                                {{ video.subscriptions[0].name }}
                              </router-link>
                              <button
                                class="video-channel__unsubscribe"
                                @click.stop="handleUnsubscribe(video.subscriptions[0].id)"
                                :disabled="isChannelUnsubscribing"
                                :aria-busy="isChannelUnsubscribing ? 'true' : 'false'"
                                :title="`取消订阅 ${video.subscriptions[0].name}`"
                                :aria-label="`取消订阅 ${video.subscriptions[0].name}`"
                              >
                                <span v-if="isChannelUnsubscribing" class="video-channel__spinner" aria-hidden="true"></span>
                                <span class="video-action__label">{{ isChannelUnsubscribing ? '正在取消' : '取消订阅' }}</span>
                              </button>
                            </div>

                            <div class="video-channel__stats">
                              <span class="video-channel__stat-pill">
                                总视频 {{ video.subscriptions[0].total_videos || 0 }}
                              </span>
                              <span class="video-channel__stat-pill">
                                已解析 {{ video.subscriptions[0].total_extract || 0 }}
                              </span>
                            </div>
                            <p v-if="videoChannelError" class="video-channel__error">{{ videoChannelError }}</p>
                          </div>
                        </div>

                        <div
                          v-if="video.subscriptions.length > 1"
                          class="video-channel__more"
                        >
                          <div
                            v-for="sub in video.subscriptions.slice(1)"
                            :key="sub.id"
                            class="video-channel__chip"
                            @click.stop="$router.push(`/subscription/${sub.id}/all`)"
                          >
                            <img
                              :src="getAvatarSrc(sub.avatar, sub.id)"
                              :alt="sub.name"
                              class="video-channel__chip-avatar"
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

                <!-- 操作按钮组 -->
                <div class="video-meta__actions">
                  <template v-for="action in videoActions" :key="action.key">
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
                      @click="handleVideoAction(action)"
                    >
                      <Icon :icon="action.icon" class="video-action__icon" />
                      <span class="video-action__label">{{ action.label }}</span>
                    </button>
                  </template>
                </div>
              </div>
            </transition>
          </div>
        </div>
      </div>

      <!-- 右侧区域 - 相关视频 -->
      <div :class="['video-aside', isWidescreen ? 'hidden' : '']">
        <div>
          <div class="video-aside__panel">
            <div class="video-aside__header">
              <div class="video-aside__title-row">
                <h2 class="video-aside__title">相关视频</h2>
              </div>
            </div>
            <div class="video-aside__content">
              <div v-if="!relatedVideos.length && !loadingRelated" class="video-aside__empty">暂无推荐</div>
              <div v-if="relatedVideos.length" class="related-videos-list">
                <article
                  v-for="(relatedVideo, index) in relatedVideos"
                  :key="relatedVideo.id"
                  class="related-video-card group"
                  @click="goToVideo(relatedVideo.id, relatedVideo)"
                >
                  <div class="related-video-card__index-bg">
                    {{ String(index + 1).padStart(2, '0') }}
                  </div>
                  <div class="related-video-card__thumb">
                    <img
                      v-if="relatedVideo.thumbnail && !relatedThumbnailErrorIds.has(relatedVideo.id)"
                      :src="relatedVideo.thumbnail"
                      referrerpolicy="no-referrer"
                      class="related-video-card__image"
                      draggable="false"
                      :alt="relatedVideo.title"
                      @error="() => relatedThumbnailErrorIds.add(relatedVideo.id)"
                    >
                    <div
                      v-else
                      class="related-video-card__fallback"
                    >
                      <div class="related-video-card__fallback-copy">
                        <Icon icon="material-symbols:image" class="related-video-card__fallback-icon" />
                        <span class="text-2xs">暂无封面</span>
                      </div>
                    </div>
                    <div class="related-video-card__data-overlay">
                      [DATA_READING...]
                    </div>
                    <div class="related-video-card__duration">
                      {{ formatDuration(relatedVideo.duration) }}
                    </div>
                  </div>
                  <div class="related-video-card__body">
                    <div class="related-video-card__title">
                      {{ relatedVideo.title }}
                    </div>
                    <div class="related-video-card__channel">
                      <router-link
                        v-if="relatedVideo.subscriptions?.[0]?.id"
                        :to="`/subscription/${relatedVideo.subscriptions[0].id}/all`"
                        @click.stop
                        class="related-video-card__channel-link"
                      >
                        {{ relatedVideo.subscriptions[0].name }}
                      </router-link>
                      <span v-else class="truncate">
                        {{ relatedVideo.site }}
                      </span>
                    </div>
                    <div
                      v-if="relatedVideo.uploaded_at"
                      class="related-video-card__date"
                    >
                      {{ formatDate(relatedVideo.uploaded_at) }}
                    </div>
                  </div>
                </article>
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
import { useAppTheme } from '@/composables/useAppTheme'
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

watch(() => video.value?.id, () => {
  isVideoChannelVisible.value = true
  isChannelUnsubscribing.value = false
  videoChannelError.value = ''
})

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
    gap: 2rem;
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

.video-main.is-widescreen .video-container,
.video-main:not(.is-widescreen) .video-container {
  aspect-ratio: auto;
  /* 核心修复：限制播放器最大高度，确保下方信息可见 */
  height: min(
    calc(var(--video-page-available-height, 100vh) - var(--video-meta-height, 280px) - 40px),
    calc(100vw * 9 / 16)
  );
  max-height: calc(var(--video-page-available-height, 100vh) - var(--video-meta-height, 280px) - 40px);
  padding-bottom: 0;
  min-height: 200px;
}


.video-aside {
  width: 100%;
  flex: none;
}

.video-aside__panel {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  padding: 0;
  border: none;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.video-aside__header {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.video-aside__eyebrow {
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: hsl(var(--muted-foreground));
}

.video-aside__title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.video-aside__title {
  font-size: 1rem;
  font-weight: 600;
  letter-spacing: -0.02em;
  color: hsl(var(--foreground));
}

.video-aside__count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 1.9rem;
  height: 1.9rem;
  padding: 0 0.625rem;
  border-radius: 9999px;
  border: 1px solid hsl(var(--border) / 0.8);
  background: hsl(var(--background) / 0.6);
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 600;
}

.video-aside__empty {
  font-size: 0.875rem;
  color: hsl(var(--muted-foreground));
}

.video-aside__content {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-height: 0;
}

.related-videos-list {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  gap: 0.75rem;
  min-height: 0;
  max-height: none;
  overflow: visible;
  padding-right: 0;
}

.related-videos-list::-webkit-scrollbar {
  width: 6px;
}

.related-videos-list::-webkit-scrollbar-thumb {
  background: hsl(var(--border));
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
    min-height: var(--related-panel-height, 75vh);
    height: var(--related-panel-height, 75vh);
    padding: 0;
  }

  .related-videos-list {
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

@media (max-width: 640px) {
  .viewfinder-label {
    font-size: 0.55rem;
    top: -2px;
  }
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

@media (max-width: 640px) {
  .viewfinder-corner {
    width: 10px;
    height: 10px;
  }
}

.viewfinder-corner--top-left {
  top: 0;
  left: 0;
  border-right: none;
  border-bottom: none;
}

.viewfinder-corner--top-right {
  top: 0;
  right: 0;
  border-left: none;
  border-bottom: none;
}

.viewfinder-corner--bottom-left {
  bottom: 0;
  left: 0;
  border-right: none;
  border-top: none;
}

.viewfinder-corner--bottom-right {
  bottom: 0;
  right: 0;
  border-left: none;
  border-top: none;
}

.video-container :deep(.sp-player) {
  background: hsl(var(--background));
  --sp-controls-bg: linear-gradient(
    to top,
    hsl(var(--background) / 0.9) 0%,
    hsl(var(--background) / 0.84) 18%,
    hsl(var(--background) / 0.62) 34%,
    hsl(var(--background) / 0.28) 56%,
    transparent 100%
  );
  border-radius: 12px;
  overflow: hidden;
}

.video-container :deep(iframe),
.video-container :deep(video) {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: #000;
}

.video-meta {
  margin-top: 0.875rem;
  padding: 0 12px; /* 与播放器对齐 */
}

@media (max-width: 640px) {
  .video-meta {
    padding: 0 6px; /* 移动端与播放器对齐 */
  }
}

.video-meta__title {
  width: 100%;
  font-size: clamp(0.9rem, 0.85rem + 0.2vw, 1.05rem);
  font-weight: 600;
  letter-spacing: -0.02em;
  line-height: 1.3;
  word-break: break-word;
  padding-bottom: 0.25rem;
  margin-bottom: 0.5rem;
  position: relative;
  border-bottom: none !important; /* 强制移除任何残留或继承的下划线 */
}

.video-meta__actions {
  display: flex;
  width: 100%;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.35rem;
  padding-top: 0.5rem; /* 减少顶部留白 */
  border-top: none;
  position: relative;
}

.video-meta__panel {
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
  padding: 0;
  border: none;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.video-meta__header {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.6rem; /* 压缩间距 */
}

.video-meta__title {
  width: 100%;
  font-size: clamp(0.9rem, 0.85rem + 0.2vw, 1.05rem); /* 缩小标题 */
  font-weight: 600;
  letter-spacing: -0.02em;
  line-height: 1.3;
  word-break: break-word;
  padding-bottom: 0.75rem;
  margin-bottom: 0.5rem;
  position: relative;
  border-bottom: none; /* 移除实线 */
}

/* 渐变衰减分割线 */
.video-meta__title::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 1px;
  background: linear-gradient(to right, 
    rgba(255, 77, 0, 0.4) 0%, 
    rgba(255, 77, 0, 0.1) 50%, 
    transparent 100%
  );
}

.video-meta__actions {
  display: flex;
  width: 100%;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.35rem; /* 更紧凑的动作栏 */
  padding-top: 1rem;
  border-top: none; /* 移除顶部实线 */
  position: relative;
}

/* 用微标代替分割线 */
.video-meta__actions::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 12px;
  height: 2px;
  background: #ff4d00;
  opacity: 0.3;
}

.video-channel {
  padding: 0.75rem 1rem; /* 压缩 ID 卡内边距 */
  background: rgba(255, 255, 255, 0.015);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-left: 2px solid #ff4d00;
  border-radius: 2px;
  position: relative;
  overflow: visible;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.video-meta__actions {
  display: flex;
  width: 100%;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.35rem; /* 更紧凑的动作栏 */
  justify-content: flex-start;
  padding-top: 0.6rem;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.video-meta__copy {
  width: 100%;
  min-width: 0;
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
  padding: 0;
  border: none;
  background: transparent;
  color: hsl(var(--muted-foreground));
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.01em;
}

.video-meta__pill + .video-meta__pill {
  position: relative;
  margin-left: 0.6rem;
}

.video-meta__pill + .video-meta__pill::before {
  content: '';
  position: absolute;
  left: -0.36rem;
  top: 50%;
  width: 3px;
  height: 3px;
  border-radius: 9999px;
  background: hsl(var(--border));
  transform: translateY(-50%);
}

.video-meta__pill--muted {
  color: hsl(var(--primary));
}

.video-meta__title {
  width: 100%;
  font-size: clamp(0.96rem, 0.9rem + 0.28vw, 1.16rem);
  font-weight: 600;
  letter-spacing: -0.03em;
  line-height: 1.4;
  word-break: break-word;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid rgba(255, 77, 0, 0.4);
  margin-bottom: 1rem;
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
  border: 1px solid transparent;
  border-radius: 4px;
  background: transparent;
  color: rgba(255, 255, 255, 0.45);
  box-shadow: none;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  font-family: 'JetBrains Mono', monospace;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.video-action:hover {
  background: rgba(255, 77, 0, 0.04);
  border-color: rgba(255, 77, 0, 0.3);
  color: #ff4d00;
  text-shadow: 0 0 8px rgba(255, 77, 0, 0.4);
}

.video-action.is-active {
  background: rgba(255, 77, 0, 0.08);
  border-color: #ff4d00;
  color: #ff4d00;
  box-shadow: 0 0 15px rgba(255, 77, 0, 0.15);
  text-shadow: 0 0 10px rgba(255, 77, 0, 0.5);
}

.video-action--secondary {
  opacity: 0.8;
}

.video-action__icon {
  width: 0.72rem;
  height: 0.72rem;
  flex-shrink: 0;
}

.video-action__label {
  font-size: 0.6rem; /* 稍微增大一点提高可读性 */
  font-weight: 600;
  white-space: nowrap;
  font-family: 'JetBrains Mono', monospace;
}

.video-action__label::before {
  content: '[';
  margin-right: 2px;
  opacity: 0.5;
}

.video-action__label::after {
  content: ']';
  margin-left: 2px;
  opacity: 0.5;
}

.video-action:hover .video-action__label::before,
.video-action:hover .video-action__label::after,
.video-action.is-active .video-action__label::before,
.video-action.is-active .video-action__label::after {
  opacity: 1;
  color: #ff4d00;
}

.video-channel__primary {
  display: flex;
  align-items: center;
  gap: 0.875rem;
  flex-wrap: wrap;
}

.video-channel__content {
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
  padding-top: 0.1rem;
}

.video-channel__avatar {
  width: 2.6rem;
  height: 2.6rem;
  border-radius: 9999px;
  object-fit: cover;
  flex-shrink: 0;
  box-shadow: 0 10px 24px hsl(var(--surface-shadow));
}

.video-channel__summary {
  display: flex;
  flex: 1 1 220px;
  min-width: 0;
  flex-direction: column;
  gap: 0.5rem;
}

.video-channel__identity {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  min-width: 0;
  flex-wrap: wrap;
}

.video-channel {
  padding: 0.5rem 0; /* 移除大内边距，仅保留垂直间距 */
  background: transparent; /* 移除背景色 */
  border: none; /* 移除所有边框 */
  border-radius: 0;
  position: relative;
  overflow: visible;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.video-channel__primary {
  display: flex;
  align-items: center; /* 恢复居中对齐，更自然 */
  gap: 1rem;
  flex-wrap: wrap;
}

.video-channel::before {
  display: none; /* 移除 SEC_ID_CARD 装饰 */
}

.video-channel__avatar-wrapper::after {
  content: '';
  position: absolute;
  inset: -4px; /* 缩小圈范围 */
  border: 1px solid rgba(255, 77, 0, 0.4); /* 调淡颜色 */
  border-radius: 50%;
  opacity: 0;
  animation: scanning-ring 3s cubic-bezier(0.4, 0, 0.2, 1) infinite;
}

.video-channel__primary {
  display: flex;
  align-items: flex-start; /* 顶部对齐，防止头像比例问题 */
  gap: 1.25rem;
  flex-wrap: wrap; /* 允许在窄屏时换行 */
}

.video-channel::before {
  content: 'SEC_ID_CARD';
  position: absolute;
  top: 4px;
  right: 6px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: rgba(255, 77, 0, 0.3);
  letter-spacing: 1px;
}

.video-channel__avatar-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 2.6rem;
  height: 2.6rem;
}

.video-channel__avatar-wrapper::after {
  content: '';
  position: absolute;
  inset: -6px;
  border: 1px solid #ff4d00;
  border-radius: 50%;
  opacity: 0;
  animation: scanning-ring 2.5s cubic-bezier(0.4, 0, 0.2, 1) infinite;
}

@keyframes scanning-ring {
  0% { transform: scale(0.8); opacity: 0; }
  50% { opacity: 0.4; }
  100% { transform: scale(1.3); opacity: 0; }
}

.video-channel__name {
  min-width: 0;
  width: fit-content;
  max-width: 100%;
  font-size: 0.92rem;
  font-weight: 600;
  letter-spacing: -0.02em;
  transition: color 0.2s ease;
}

.video-channel__name:hover {
  color: hsl(var(--primary));
}

.video-channel__unsubscribe {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.24rem; /* 统一间距 */
  flex-shrink: 0;
  min-height: 1.52rem; /* 统一高度 */
  padding: 0 0.5rem; /* 统一内边距 */
  border: 1px solid transparent; /* 统一默认边框 */
  border-radius: 4px;
  background: transparent;
  color: rgba(255, 255, 255, 0.45); /* 统一默认颜色 */
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.6rem;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.video-channel__unsubscribe:hover:not(:disabled) {
  background: rgba(255, 77, 0, 0.04);
  border-color: rgba(255, 77, 0, 0.3);
  color: #ff4d00;
  box-shadow: 0 0 10px rgba(255, 77, 0, 0.2);
  text-shadow: 0 0 8px rgba(255, 77, 0, 0.4);
}

.video-channel__unsubscribe:disabled {
  cursor: default;
  opacity: 0.72;
}

.video-channel__spinner {
  width: 0.68rem;
  height: 0.68rem;
  border: 1.5px solid hsl(var(--foreground) / 0.22);
  border-top-color: hsl(var(--foreground));
  border-radius: 9999px;
  animation: video-channel-spin 0.7s linear infinite;
}

.video-channel__stats {
  display: flex;
  flex-wrap: wrap;
  gap: 0.2rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.74rem;
  font-weight: 500;
}

.video-channel__stat-pill {
  display: inline-flex;
  align-items: center;
  min-height: 1.1rem;
  padding: 0;
  border: none;
  background: transparent;
  color: inherit;
  font-size: inherit;
  font-weight: inherit;
}

.video-channel__stat-pill + .video-channel__stat-pill {
  position: relative;
  margin-left: 0.6rem;
}

.video-channel__stat-pill + .video-channel__stat-pill::before {
  content: '';
  position: absolute;
  left: -0.36rem;
  top: 50%;
  width: 3px;
  height: 3px;
  border-radius: 9999px;
  background: hsl(var(--border));
  transform: translateY(-50%);
}

.video-channel__error {
  margin-top: 0.35rem;
  font-size: 0.72rem;
  color: hsl(var(--destructive));
}

.video-channel__more {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.video-channel__chip {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.42rem 0.78rem 0.42rem 0.42rem;
  border-radius: 9999px;
  background: hsl(var(--background) / 0.52);
  border: 1px solid hsl(var(--border) / 0.78);
  cursor: pointer;
  transition: background-color 0.18s ease, border-color 0.18s ease, transform 0.18s ease;
  font-size: 0.75rem;
  font-weight: 500;
  color: hsl(var(--foreground));
}

.video-channel__chip:hover {
  background: hsl(var(--accent));
  border-color: hsl(var(--ring) / 0.24);
  transform: translateY(-1px);
}

.video-channel__chip-avatar {
  width: 1.35rem;
  height: 1.35rem;
  border-radius: 9999px;
  object-fit: cover;
  flex-shrink: 0;
}

.related-video-card {
  position: relative;
  display: grid;
  grid-template-columns: minmax(7.5rem, 8.75rem) minmax(0, 1fr);
  gap: 0.875rem;
  padding: 0.5rem 0;
  border: none;
  border-radius: 0;
  background: transparent;
  cursor: pointer;
  transition: color 0.18s ease, opacity 0.18s ease;
  overflow: hidden;
}

.related-video-card__index-bg {
  position: absolute;
  left: -0.2rem;
  top: 50%;
  transform: translateY(-50%);
  font-family: 'JetBrains Mono', monospace;
  font-size: 4rem;
  font-weight: 800;
  color: rgba(255, 255, 255, 0.05);
  line-height: 1;
  pointer-events: none;
  z-index: 0;
  user-select: none;
}

.related-video-card:hover {
  opacity: 0.92;
}

.related-video-card__thumb {
  position: relative;
  overflow: hidden;
  border-radius: 2px;
  background: #000; /* 背景全黑，确保无白边 */
  aspect-ratio: 16 / 9; /* 修正比例 */
  z-index: 1;
}

.related-video-card__image {
  width: 100%;
  height: 100%;
  object-fit: cover; /* 封面自适应拉伸铺满 */
  pointer-events: none;
  user-select: none;
  transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

.related-video-card:hover .related-video-card__image {
  transform: scale(1.05); /* 悬停时稍微放大，更有沉浸感 */
}

.related-video-card__fallback {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: hsl(var(--card));
}

.related-video-card__fallback-copy {
  display: flex;
  flex-direction: column;
  align-items: center;
  color: hsl(var(--muted-foreground));
}

.related-video-card__fallback-icon {
  font-size: 1.75rem;
  margin-bottom: 0.2rem;
}

.related-video-card__data-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.4);
  color: #ff4d00;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.65rem;
  letter-spacing: 0.05em;
  opacity: 0;
  transition: opacity 0.2s ease;
  pointer-events: none;
  text-shadow: 0 0 8px rgba(255, 77, 0, 0.6);
}

@media (max-width: 640px) {
  .related-video-card__data-overlay {
    font-size: 0.5rem;
  }
}

.related-video-card:hover .related-video-card__data-overlay {
  opacity: 1;
}

.related-video-card__duration {
  position: absolute;
  right: 0.45rem;
  bottom: 0.45rem;
  display: inline-flex;
  align-items: center;
  min-height: 1.45rem;
  padding: 0 0.45rem;
  border-radius: 2px;
  background: hsl(var(--background) / 0.82);
  color: rgba(255, 255, 255, 0.5);
  font-family: 'JetBrains Mono', 'Courier New', monospace;
  font-size: 0.65rem;
  font-weight: 600;
  backdrop-filter: blur(10px);
}

.related-video-card__body {
  position: relative;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  z-index: 1;
}

.related-video-card__title {
  display: -webkit-box;
  overflow: hidden;
  color: hsl(var(--foreground));
  font-size: 0.83rem;
  font-weight: 600;
  line-height: 1.45;
  transition: color 0.18s ease;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.related-video-card:hover .related-video-card__title {
  color: hsl(var(--primary));
}

.related-video-card__channel,
.related-video-card__date {
  margin-top: 0.35rem;
  font-size: 0.65rem;
  font-family: 'JetBrains Mono', 'Courier New', monospace;
  color: rgba(255, 255, 255, 0.5);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.related-video-card__channel-link {
  transition: color 0.18s ease;
}

.related-video-card__channel-link:hover {
  color: hsl(var(--primary));
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

  .video-channel__avatar-wrapper,
  .related-video-card__fallback-icon {
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
