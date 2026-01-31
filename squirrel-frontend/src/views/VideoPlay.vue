<template>
  <div ref="videoPageRef" class="video-page bg-bg-primary min-h-screen scrollbar-hide" :class="{ 'is-widescreen': isWidescreen }">
    <div :class="['video-page__container pt-6 flex gap-8', isWidescreen ? 'is-widescreen' : '']">
      <!-- 左侧主内容区域 -->
      <div :class="['video-main', isWidescreen ? 'is-widescreen' : '']">
        <!-- 视频播放区域 -->
        <div ref="videoSectionRef" class="video-section">
          <div class="video-container">
            <VideoPlayer
              ref="videoPlayerRef"
              v-if="video"
              :video="video"
              :initialTime="startTime"
              :has-prev="hasPrevVideo"
              :has-next="hasNextVideo"
              :external-error="externalError"
              :widescreen="isWidescreen"

              @play="onVideoPlay"
              @pause="onVideoPause"
              @ended="handleAutoplayNext"
              @timeupdate="onVideoTimeUpdate"
              @prev-video="handlePrevVideo"
              @next-video="handleNextVideo"
              @widescreenChange="toggleWidescreen"
              @retry="handlePlayerRetry"
            />
          </div>
        </div>

        <!-- 视频信息区域 -->
          <div ref="videoMetaRef" class="mt-3 px-4">
          <!-- 标题与操作按钮 -->
          <transition name="fade" mode="out-in">
            <div :key="video?.id" class="flex items-center justify-between">
              <h1 class="text-xs md:text-sm lg:text-base lg:font-medium text-text-primary">{{ video?.title }}</h1>

            <!-- 操作按钮组 -->
            <div class="flex items-center space-x-1">
              <!-- 随机播放按钮 -->
              <button
                @click="handlePlayRandom"
                class="p-2 rounded-full hover:bg-bg-elevated transition-colors border border-transparent text-text-accent"
                title="随机播放"
                aria-label="随机播放"
              >
                <Icon icon="lucide:shuffle" class="h-5 w-5" />
              </button>
              <!-- 主要按钮显示在外面 -->
              <button
                @click="handleLike(video, INTERACTION_TYPE.LIKE)"
                class="p-2 rounded-full hover:bg-bg-elevated transition-colors border border-transparent text-text-accent"
                :class="{ 'text-color-error': video?.interaction_type === INTERACTION_TYPE.LIKE }"
              >
                <Icon 
                  :icon="video?.interaction_type === INTERACTION_TYPE.LIKE ? 'material-symbols:thumb-up' : 'material-symbols:thumb-up-outline'" 
                  class="h-5 w-5" 
                />
              </button>

              <button
                @click="handleLike(video, INTERACTION_TYPE.DISLIKE)"
                class="p-2 rounded-full hover:bg-bg-elevated transition-colors border border-transparent text-text-accent"
                :class="{ 'text-text-secondary': video?.interaction_type === INTERACTION_TYPE.DISLIKE }"
              >
                <Icon 
                  :icon="video?.interaction_type === INTERACTION_TYPE.DISLIKE ? 'material-symbols:thumb-down' : 'material-symbols:thumb-down-outline'" 
                  class="h-5 w-5" 
                />
              </button>

              <button
                @click="handleLater(video)"
                class="p-2 rounded-full hover:bg-bg-elevated transition-colors border border-transparent text-text-accent"
                :class="{ 'text-color-info': video?.interaction_type === INTERACTION_TYPE.LATER }"
                title="稍后看"
                aria-label="稍后看"
              >
                <Icon 
                  :icon="video?.interaction_type === INTERACTION_TYPE.LATER ? 'material-symbols:schedule' : 'material-symbols:schedule-outline'" 
                  class="h-5 w-5" 
                />
              </button>

	                <!-- 原视频页按钮 -->
	                <a
	                  v-if="video && video.url"
	                  :href="video.url"
	                  target="_blank"
	                  rel="noopener noreferrer"
	                  class="p-2 rounded-full hover:bg-bg-elevated transition-colors border border-transparent text-text-accent"
	                  aria-label="打开原视频页"
	                  title="打开原视频页"
	                >
                <Icon icon="material-symbols:open-in-new" class="h-5 w-5" />
	                </a>


              <!-- 更多按钮 - 点击显示下拉菜单 -->
              <div class="relative">
                <button
                  @click="handleMoreOptionsClick"
	                  class="p-2 rounded-full hover:bg-bg-elevated transition-colors border border-transparent text-text-accent"
                >
                  <Icon icon="material-symbols:more-vert" class="h-5 w-5" />
                </button>

                <!-- 下拉菜单 -->
                <div v-if="showMoreOptions"
                     class="absolute right-0 mt-2 py-2 min-w-[40px] rounded-lg shadow-lg bg-bg-card border border-border-primary z-50"
                     @click.stop
                >
                  <div class="flex flex-col">

                  </div>
                </div>
              </div>
            </div>
            </div>
          </transition>

          <!-- 频道信息 -->
          <transition name="fade" mode="out-in">
            <div :key="video?.id" class="mt-3 pb-3 border-b border-border-primary">
              <div v-if="video?.subscriptions?.length" class="flex flex-col space-y-3">
                <!-- 主订阅：完整行展示 -->
                <div class="flex items-center space-x-3">
                  <img
                    :src="getAvatarSrc(video.subscriptions[0].avatar, video.subscriptions[0].id)"
                    :alt="video.subscriptions[0].name"
                    class="w-8 h-8 md:w-9 md:h-9 lg:w-10 lg:h-10 rounded-full object-cover"
                    referrerpolicy="no-referrer"
                    @error="(e) => handleAvatarError(e, video.subscriptions[0].id)"
                  >
                  <router-link
                    :to="`/subscription/${video.subscriptions[0].id}/all`"
                    class="text-xs md:text-sm lg:text-base text-text-primary font-medium hover:text-color-info transition-colors"
                  >
                    {{ video.subscriptions[0].name }}
                  </router-link>
                  <button
                    class="px-3 py-1.5 text-xs bg-bg-elevated hover:bg-bg-hover text-text-primary rounded-full transition-colors font-medium"
                    @click.stop="handleUnsubscribe(video.subscriptions[0].id)"
                    :title="`取消订阅 ${video.subscriptions[0].name}`"
                    :aria-label="`取消订阅 ${video.subscriptions[0].name}`"
                  >取消订阅</button>
                </div>

                <!-- 主订阅统计信息 -->
                <div class="ml-11 md:ml-12 text-2xs text-text-muted mt-1">
                  <span>
                    总视频: {{ video.subscriptions[0].total_videos || 0 }} | 已解析: {{ video.subscriptions[0].total_extract || 0 }}
                  </span>
                  <span v-if="video?.publish_date"> · {{ formatDate(video.publish_date) }}发布</span>
                </div>

                <!-- 额外订阅：紧凑 chip 风格 -->
                <div
                  v-if="video.subscriptions.length > 1"
                  class="ml-11 md:ml-12 flex flex-wrap gap-2 mt-3"
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
      <div :class="['video-aside', isWidescreen ? 'hidden' : 'hidden md:block']">
        <div>
          <div class="rounded-xl px-4 pb-4 pt-0 flex flex-col">
            <h2 class="text-text-primary text-lg mb-4">相关视频</h2>
            <div>
              <div v-if="!relatedVideos.length && !loadingRelated" class="text-text-muted text-sm">暂无推荐</div>
              <div v-if="relatedVideos.length" class="related-videos-list space-y-3">
                <div
                  v-for="relatedVideo in relatedVideos"
                  :key="relatedVideo.id"
                  class="flex space-x-3 cursor-pointer group"
                  @click="goToVideo(relatedVideo.id, relatedVideo)"
                >
                  <div class="relative w-40 h-24 rounded-lg overflow-hidden bg-bg-tertiary/60 transform-gpu">
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
import useOptionsDropdown from '../composables/useOptionsDropdown';
import VideoPlayer from '../components/video-player/VideoPlayer.vue';
import { Icon } from '@iconify/vue';
import useVideoHistory from "../composables/useVideoHistory";
import { formatDate, formatDuration } from '../utils/dateFormat';
import useVideoInteraction from "../composables/useVideoInteraction.js";
import { useImageFallback } from '../composables/useImageFallback';
import { usePlayerStore } from '../stores/playerStore';
import { Logger } from '../utils/logger'
import { unsubscribe as apiUnsubscribe } from '../api/subscription'
import { getRandomVideo } from '../api/video'




const route = useRoute();
const router = useRouter();
const emitter = inject('emitter');
const { getImageSrc: getAvatarSrc, handleImageError: handleAvatarError } = useImageFallback();


// 内部切换不使用 router，所以不需要从 history.state 读取初始数据
const { video, startTime, relatedVideos, loadingRelated, loadAndPlayById, externalError } = usePlaybackOrchestrator(null);
const { sendReport } = useVideoHistory();
const { INTERACTION_TYPE, toggleLike, deleteInteraction } = useVideoInteraction();
const { onVideoPlay, onVideoPause, onVideoEnded, onVideoTimeUpdate } = usePlaybackReporting(video, sendReport);
const { showMoreOptions, handleMoreOptionsClick } = useOptionsDropdown();
const playerStore = usePlayerStore();


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
      await router.push({ name: 'VideoPlay', params: { videoId: targetId }, state: simpleState });
    } catch (_) {
      await router.push(`/video/${targetId}`);
    }
  }
};

const handleAutoplayNext = async (evt) => {
  try {
    try { onVideoEnded(); } catch (_) {}
    const autoplayEnabled = evt?.autoplay !== undefined ? evt.autoplay : playerStore.autoplay;
    const autoplayNextEnabled = evt?.autoplayNext !== undefined ? evt.autoplayNext : playerStore.autoplayNext;
    const loopEnabled = evt?.loop !== undefined ? evt.loop : playerStore.loop;
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
/* 视频页面容器对齐其它页面 */
.video-page__container {
  max-width: min(1840px, calc(100vw - 32px));
  margin: 0 auto;
  width: 100%;
  padding-left: 1rem;
  padding-right: 1rem;
  --video-main-offset: 16px;
  --video-aside-width: clamp(320px, 22vw, 360px);
}

.video-page__container.is-widescreen {
  --video-main-offset: 0px;
}


.video-page__container.is-widescreen {
  max-width: 100%;
  padding-left: 0;
  padding-right: 0;
}

.video-page__container.is-widescreen .video-section {
  border-radius: 0;
}

@media (min-width: 640px) {
  .video-page__container {
    padding-left: 1.5rem;
    padding-right: 1.5rem;
  }
}

@media (min-width: 1024px) {
  .video-page__container {
    padding-left: 2rem;
    padding-right: 2rem;
  }
}



.video-main {
  flex: 1 1 0%;
  min-width: 0;
  max-width: clamp(1200px, 78vw, 1440px);
  margin-left: auto;
  margin-right: auto;
  transform: translateX(var(--video-main-offset, 0px));
}

.video-main.is-widescreen {
  max-width: 100%;
  transform: none;
}


.video-main.is-widescreen .video-container {
  /* 宽屏(剧场)模式：用视窗高度约束，不让播放器高到需要滚动 */
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
  padding-bottom: clamp(60%, 64vh, 68%);
  min-height: clamp(520px, 66vh, 860px);
  max-height: min(75vh, calc(100vw * 9 / 16));
}


.video-aside {
  width: var(--video-aside-width, 360px);
  flex: 0 0 var(--video-aside-width, 360px);
}

.related-videos-list {
  max-height: var(--related-panel-height, 75vh);
  overflow-y: auto;
  padding-right: 6px;
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
  height: 0;
  padding-bottom: 56.25%; /* 16:9 比例 */
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
