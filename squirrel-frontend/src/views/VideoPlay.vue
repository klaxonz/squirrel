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
        </div>

        <div class="video-detail-grid">
          <transition name="fade" mode="out-in">
            <section :key="`channel-${video?.id}`" class="video-module video-module--channel">
              <div class="video-module__header">
                <div>
                  <div class="video-module__eyebrow">当前归属</div>
                  <h2 class="video-module__title">频道信息</h2>
                </div>
                <div v-if="primarySubscriptionMeta" class="video-module__hint">{{ primarySubscriptionMeta }}</div>
              </div>

              <div v-if="primarySubscription" class="video-channel-card">
                <div class="video-channel-card__main">
                  <img
                    :src="getAvatarSrc(primarySubscription.avatar, primarySubscription.id)"
                    :alt="primarySubscription.name"
                    class="video-channel-card__avatar"
                    referrerpolicy="no-referrer"
                    @error="(e) => handleAvatarError(e, primarySubscription.id)"
                  >

                  <div class="video-channel-card__identity">
                    <div class="video-channel-card__name-row">
                      <router-link
                        :to="`/subscription/${primarySubscription.id}/all`"
                        class="video-channel-card__name"
                      >
                        {{ primarySubscription.name }}
                      </router-link>
                      <span class="video-channel-card__badge">已订阅</span>
                    </div>
                    <div v-if="primarySubscriptionMeta" class="video-channel-card__meta">{{ primarySubscriptionMeta }}</div>
                  </div>

                  <button
                    class="video-channel__unsubscribe video-channel-card__unsubscribe"
                    @click.stop="handleUnsubscribe(primarySubscription.id)"
                    :title="`取消订阅 ${primarySubscription.name}`"
                    :aria-label="`取消订阅 ${primarySubscription.name}`"
                  >取消订阅</button>
                </div>

                <div class="video-channel-card__stats">
                  <div
                    v-for="item in channelSummaryItems"
                    :key="item.label"
                    class="video-channel-stat"
                  >
                    <span class="video-channel-stat__label">{{ item.label }}</span>
                    <span class="video-channel-stat__value">{{ item.value }}</span>
                  </div>
                </div>

                <div v-if="secondarySubscriptions.length" class="video-channel-card__group">
                  <div class="video-channel-card__group-title">同时归属</div>
                  <div class="video-channel-card__chips">
                    <div
                      v-for="sub in secondarySubscriptions"
                      :key="sub.id"
                      class="video-channel-chip"
                      @click.stop="$router.push(`/subscription/${sub.id}/all`)"
                    >
                      <img
                        :src="getAvatarSrc(sub.avatar, sub.id)"
                        :alt="sub.name"
                        class="video-channel-chip__avatar"
                        referrerpolicy="no-referrer"
                        @error="(e) => handleAvatarError(e, sub.id)"
                      >
                      <span class="video-channel-chip__label">{{ sub.name }}</span>
                    </div>
                  </div>
                </div>
              </div>

              <div v-else class="video-module__empty">暂无频道信息</div>
            </section>
          </transition>

          <section class="video-module video-module--related">
            <div class="video-module__header">
              <div>
                <div class="video-module__eyebrow">下一步去哪里</div>
                <h2 class="video-module__title">相关视频</h2>
              </div>
              <div class="video-module__hint">{{ relatedModuleHint }}</div>
            </div>

            <div v-if="!relatedVideos.length && !loadingRelated" class="video-module__empty">暂无推荐</div>

            <div v-if="relatedVideos.length" class="related-feed">
              <article
                v-for="(relatedVideo, index) in relatedVideos"
                :key="relatedVideo.id"
                class="related-item"
                :class="{ 'is-priority': index === 0 }"
                @click="goToVideo(relatedVideo.id, relatedVideo)"
              >
                <div class="related-item__thumb">
                  <img
                    v-if="relatedVideo.thumbnail && !relatedThumbnailErrorIds.has(relatedVideo.id)"
                    :src="relatedVideo.thumbnail"
                    referrerpolicy="no-referrer"
                    class="related-item__image"
                    draggable="false"
                    :alt="relatedVideo.title"
                    @error="() => relatedThumbnailErrorIds.add(relatedVideo.id)"
                  >
                  <div
                    v-else
                    class="related-item__image-fallback"
                  >
                    <div class="text-text-muted flex flex-col items-center">
                      <Icon icon="material-symbols:image" class="text-3xl mb-1" />
                      <span class="text-2xs">暂无封面</span>
                    </div>
                  </div>
                  <div v-if="index === 0" class="related-item__badge">优先</div>
                  <div class="related-item__duration">
                    {{ formatDuration(relatedVideo.duration) }}
                  </div>
                </div>

                <div class="related-item__body">
                  <div v-if="index === 0" class="related-item__kicker">下一条候选</div>
                  <div class="related-item__title">
                    {{ relatedVideo.title }}
                  </div>
                  <div class="related-item__meta">
                    <router-link
                      v-if="relatedVideo.subscriptions?.[0]?.id"
                      :to="`/subscription/${relatedVideo.subscriptions[0].id}/all`"
                      @click.stop
                      class="related-item__channel"
                    >
                      {{ relatedVideo.subscriptions[0].name }}
                    </router-link>
                    <span v-else>
                      {{ relatedVideo.site }}
                    </span>
                  </div>
                  <div
                    v-if="relatedVideo.uploaded_at"
                    class="related-item__date"
                  >
                    {{ formatDate(relatedVideo.uploaded_at) }}
                  </div>
                </div>
              </article>
            </div>
          </section>
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
const primarySubscription = computed(() => video.value?.subscriptions?.[0] ?? null);
const secondarySubscriptions = computed(() => video.value?.subscriptions?.slice(1) ?? []);
const primarySubscriptionMeta = computed(() => {
  const metaParts = [];

  if (video.value?.site) {
    metaParts.push(video.value.site);
  }

  if (video.value?.publish_date) {
    metaParts.push(`${formatDate(video.value.publish_date)} 发布`);
  }

  return metaParts.join(' · ');
});

const channelSummaryItems = computed(() => {
  const items = [];

  if (primarySubscription.value) {
    items.push({ label: '总视频', value: primarySubscription.value.total_videos || 0 });
    items.push({ label: '已解析', value: primarySubscription.value.total_extract || 0 });
  }

  if (video.value?.publish_date) {
    items.push({ label: '发布时间', value: formatDate(video.value.publish_date) });
  }

  return items;
});

const relatedModuleHint = computed(() => {
  if (loadingRelated.value) return '整理中';
  if (!relatedVideos.value.length) return '暂无候选';
  return '自动衔接播放池';
});

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
  const viewportHeight = window.innerHeight || document.documentElement.clientHeight;
  const availableHeight = Math.max(0, Math.floor(viewportHeight - sectionTop));

  root.style.setProperty('--video-meta-height', `${metaHeight}px`);
  root.style.setProperty('--video-page-available-height', `${availableHeight}px`);
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
  max-width: min(1840px, calc(100vw - 32px));
  margin: 0 auto;
  width: 100%;
  padding: 0.75rem 0.75rem calc(var(--mobile-nav-height, 64px) + 1rem);
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
    padding-left: 1.5rem;
    padding-right: 1.5rem;
    padding-bottom: 1.5rem;
  }
}

@media (min-width: 1024px) {
  .video-page__container {
    padding-left: 2rem;
    padding-right: 2rem;
    padding-bottom: 2rem;
  }
}

.video-main {
  min-width: 0;
  width: 100%;
  max-width: 100%;
  margin-left: auto;
  margin-right: auto;
  max-width: clamp(980px, 100vw, 1480px);
}

.video-main.is-widescreen {
  max-width: 100%;
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

@media (min-width: 1280px) {
  .video-main {
    max-width: clamp(1180px, 86vw, 1500px);
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

.video-detail-grid {
  display: grid;
  gap: 1rem;
  margin-top: 1rem;
}

.video-module {
  min-width: 0;
  padding: 1rem;
  border: 1px solid var(--border-primary);
  border-radius: 1rem;
  background: color-mix(in srgb, var(--bg-secondary) 84%, transparent);
}

.video-module__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.video-module__eyebrow {
  font-size: var(--font-size-2xs);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-tertiary);
}

.video-module__title {
  margin-top: 0.25rem;
  font-size: clamp(1rem, 0.96rem + 0.2vw, 1.125rem);
  font-weight: 600;
  color: var(--text-primary);
}

.video-module__hint {
  font-size: var(--font-size-2xs);
  color: var(--text-muted);
  white-space: nowrap;
}

.video-module__empty {
  font-size: var(--font-size-sm);
  color: var(--text-muted);
}

.video-channel-card {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.video-channel-card__main {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 0.875rem;
  align-items: center;
}

.video-channel-card__avatar {
  width: 3rem;
  height: 3rem;
  border-radius: 9999px;
  object-fit: cover;
}

.video-channel-card__identity {
  min-width: 0;
}

.video-channel-card__name-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.video-channel-card__name {
  min-width: 0;
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--text-primary);
  transition: color 0.18s ease;
}

.video-channel-card__name:hover {
  color: var(--color-info);
}

.video-channel-card__badge {
  display: inline-flex;
  align-items: center;
  min-height: 1.5rem;
  padding: 0 0.625rem;
  border-radius: 9999px;
  background: rgba(59, 130, 246, 0.14);
  color: #dbeafe;
  font-size: var(--font-size-2xs);
  font-weight: 600;
}

.video-channel-card__meta {
  margin-top: 0.375rem;
  font-size: var(--font-size-xs);
  color: var(--text-muted);
}

.video-channel-card__unsubscribe {
  justify-self: start;
  min-height: 2.5rem;
  padding: 0 0.875rem;
  border: 1px solid rgba(239, 68, 68, 0.24);
  border-radius: 9999px;
  background: rgba(239, 68, 68, 0.1);
  color: #fecaca;
  font-size: var(--font-size-xs);
  font-weight: 600;
  transition: background-color 0.18s ease, border-color 0.18s ease, color 0.18s ease;
}

.video-channel-card__unsubscribe:hover {
  background: rgba(239, 68, 68, 0.16);
  border-color: rgba(239, 68, 68, 0.36);
  color: #fee2e2;
}

.video-channel-card__stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 0.75rem;
}

.video-channel-stat {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  padding: 0.875rem 0.9375rem;
  border-radius: 0.875rem;
  background: color-mix(in srgb, var(--bg-tertiary) 88%, transparent);
  border: 1px solid var(--border-primary);
}

.video-channel-stat__label {
  font-size: var(--font-size-2xs);
  color: var(--text-tertiary);
}

.video-channel-stat__value {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--text-primary);
}

.video-channel-card__group {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
}

.video-channel-card__group-title {
  font-size: var(--font-size-2xs);
  color: var(--text-tertiary);
}

.video-channel-card__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.625rem;
}

.video-channel-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  max-width: 100%;
  padding: 0.5rem 0.75rem;
  border-radius: 9999px;
  background: color-mix(in srgb, var(--bg-tertiary) 90%, transparent);
  color: var(--text-primary);
  transition: background-color 0.18s ease, transform 0.18s ease;
}

.video-channel-chip:hover {
  background: var(--bg-hover);
  transform: translateY(-1px);
}

.video-channel-chip__avatar {
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 9999px;
  object-fit: cover;
}

.video-channel-chip__label {
  min-width: 0;
  max-width: 10rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--font-size-xs);
  font-weight: 500;
}

.related-feed {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.related-item {
  display: grid;
  grid-template-columns: minmax(7.5rem, 8.5rem) minmax(0, 1fr);
  gap: 0.875rem;
  padding: 0.75rem;
  border: 1px solid transparent;
  border-radius: 1rem;
  background: color-mix(in srgb, var(--bg-tertiary) 84%, transparent);
  transition: border-color 0.18s ease, background-color 0.18s ease, transform 0.18s ease;
}

.related-item:hover {
  border-color: var(--border-secondary);
  background: var(--bg-hover);
  transform: translateY(-1px);
}

.related-item.is-priority {
  border-color: rgba(59, 130, 246, 0.24);
  background: linear-gradient(180deg, rgba(59, 130, 246, 0.12), rgba(59, 130, 246, 0.04));
}

.related-item__thumb {
  position: relative;
  aspect-ratio: 16 / 9;
  border-radius: 0.875rem;
  overflow: hidden;
  background: var(--bg-tertiary);
}

.related-item__image,
.related-item__image-fallback {
  width: 100%;
  height: 100%;
}

.related-item__image {
  object-fit: cover;
  transition: transform 0.2s ease;
}

.related-item:hover .related-item__image {
  transform: scale(1.04);
}

.related-item__image-fallback {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-secondary);
}

.related-item__badge,
.related-item__duration {
  position: absolute;
  border-radius: 9999px;
  font-size: var(--font-size-2xs);
  font-weight: 600;
}

.related-item__badge {
  top: 0.5rem;
  left: 0.5rem;
  padding: 0.2rem 0.5rem;
  background: rgba(59, 130, 246, 0.9);
  color: #eff6ff;
}

.related-item__duration {
  right: 0.5rem;
  bottom: 0.5rem;
  padding: 0.2rem 0.45rem;
  background: rgba(15, 15, 15, 0.76);
  color: var(--text-primary);
}

.related-item__body {
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 0.35rem;
}

.related-item__kicker {
  font-size: var(--font-size-2xs);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--color-info);
}

.related-item__title {
  display: -webkit-box;
  overflow: hidden;
  color: var(--text-primary);
  font-size: var(--font-size-sm);
  font-weight: 500;
  line-height: 1.45;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.related-item__meta,
.related-item__date {
  font-size: var(--font-size-2xs);
  color: var(--text-muted);
}

.related-item__channel {
  color: var(--text-muted);
  transition: color 0.18s ease;
}

.related-item__channel:hover {
  color: var(--color-info);
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

  .video-detail-grid {
    grid-template-columns: minmax(0, 1.35fr) minmax(0, 1fr);
    align-items: start;
  }

  .video-channel-card__main {
    grid-template-columns: auto minmax(0, 1fr) auto;
  }

  .video-channel-card__unsubscribe {
    justify-self: end;
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

  .video-detail-grid {
    gap: 0.875rem;
  }

  .video-module {
    padding: 0.875rem;
    border-radius: 0.875rem;
  }

  .video-module__header {
    flex-direction: column;
    gap: 0.375rem;
  }

  .video-module__hint {
    white-space: normal;
  }

  .video-channel-card__main {
    grid-template-columns: auto minmax(0, 1fr);
  }

  .video-channel-card__unsubscribe {
    grid-column: 1 / -1;
    width: 100%;
    justify-content: center;
  }

  .video-channel-card__stats {
    grid-template-columns: 1fr;
  }

  .related-item {
    grid-template-columns: 1fr;
    gap: 0.75rem;
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
