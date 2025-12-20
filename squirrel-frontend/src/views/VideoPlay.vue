<template>
  <div class="video-page bg-[#0f0f0f] min-h-screen scrollbar min-w-[1200px]">
    <div class="max-w-[1720px] mx-auto lg:px-6 pt-6 flex min-w-[1200px]">
      <!-- 左侧主内容区域 -->
      <div :class="['flex-1', isWidescreen ? '' : 'max-w-[1280px]']">
        <!-- 视频播放区域 -->
        <div class="video-section">
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
            />
          </div>
        </div>

        <!-- 视频信息区域 -->
        <div class="mt-3 px-4">
          <!-- 标题与操作按钮 -->
          <transition name="fade" mode="out-in">
            <div :key="video?.id" class="flex items-center justify-between">
              <h1 class="text-xs md:text-sm lg:text-base lg:font-medium text-white">{{ video?.title }}</h1>

            <!-- 操作按钮组 -->
            <div class="flex items-center space-x-1">
              <!-- 随机播放按钮 -->
              <button
                @click="handlePlayRandom"
                class="p-2 rounded-full hover:bg-[#272727] transition-colors"
                title="随机播放"
                aria-label="随机播放"
              >
                <Icon icon="lucide:shuffle" class="h-5 w-5" />
              </button>
              <!-- 主要按钮显示在外面 -->
              <button
                @click="handleLike(video, INTERACTION_TYPE.LIKE)"
                class="p-2 rounded-full hover:bg-[#272727] transition-colors"
                :class="{ 'text-red-500': video?.interaction_type === INTERACTION_TYPE.LIKE }"
              >
                <Icon 
                  :icon="video?.interaction_type === INTERACTION_TYPE.LIKE ? 'material-symbols:thumb-up' : 'material-symbols:thumb-up-outline'" 
                  class="h-5 w-5" 
                />
              </button>

              <button
                @click="handleLike(video, INTERACTION_TYPE.DISLIKE)"
                class="p-2 rounded-full hover:bg-[#272727] transition-colors"
                :class="{ 'text-gray-400': video?.interaction_type === INTERACTION_TYPE.DISLIKE }"
              >
                <Icon 
                  :icon="video?.interaction_type === INTERACTION_TYPE.DISLIKE ? 'material-symbols:thumb-down' : 'material-symbols:thumb-down-outline'" 
                  class="h-5 w-5" 
                />
              </button>

              <button
                @click="handleLater(video)"
                class="p-2 rounded-full hover:bg-[#272727] transition-colors"
                :class="{ 'text-blue-400': video?.interaction_type === INTERACTION_TYPE.LATER }"
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
	                  class="p-2 rounded-full hover:bg-[#272727] transition-colors"
	                  aria-label="打开原视频页"
	                  title="打开原视频页"
	                >
                <Icon icon="material-symbols:open-in-new" class="h-5 w-5" />
	                </a>


              <!-- 更多按钮 - 点击显示下拉菜单 -->
              <div class="relative">
                <button
                  @click="handleMoreOptionsClick"
                  class="p-2 rounded-full hover:bg-[#272727] transition-colors"
                >
                  <Icon icon="material-symbols:more-vert" class="h-5 w-5" />
                </button>

                <!-- 下拉菜单 -->
                <div v-if="showMoreOptions"
                     class="absolute right-0 mt-2 py-2 min-w-[40px] rounded-lg shadow-lg bg-[#282828] z-50"
                     @click.stop
                >
                  <div class="flex flex-col">
                    <button
                      @click="handleDownload"
                      class="flex items-center w-full px-4 py-2 text-sm text-white hover:bg-[#3f3f3f]"
                    >
                      <svg v-if="!video?.if_downloaded"
                           xmlns="http://www.w3.org/2000/svg"
                           class="h-5 w-5 mr-4"
                           fill="none"
                           viewBox="0 0 24 24"
                           stroke="currentColor"
                      >
                        <path stroke-linecap="round"
                              stroke-linejoin="round"
                              stroke-width="2"
                              d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                        />
                      </svg>

                      <svg v-else
                           xmlns="http://www.w3.org/2000/svg"
                           class="h-5 w-5 mr-4"
                           viewBox="0 0 24 24"
                           fill="currentColor"
                      >
                        <path fill-rule="evenodd"
                              d="M12 2a1 1 0 011 1v10.586l2.293-2.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 111.414-1.414L11 13.586V3a1 1 0 011-1zM4.5 19A1.5 1.5 0 003 20.5v.5a2 2 0 002 2h14a2 2 0 002-2v-.5a1.5 1.5 0 00-1.5-1.5h-15z"
                              clip-rule="evenodd"
                        />
                      </svg>

                      <span class="whitespace-nowrap">下载</span>
                    </button>

                  </div>
                </div>
              </div>
            </div>
            </div>
          </transition>

          <!-- 频道信息 -->
          <transition name="fade" mode="out-in">
            <div :key="video?.id" class="mt-3 pb-3 border-b border-[#272727]">
              <div v-if="video?.subscriptions?.length" class="flex flex-col space-y-3">
                <!-- 主订阅：完整行展示 -->
                <div class="flex items-center space-x-3">
                  <img
                    :src="video.subscriptions[0].avatar"
                    :alt="video.subscriptions[0].name"
                    class="w-8 h-8 md:w-9 md:h-9 lg:w-10 lg:h-10 rounded-full object-cover"
                    referrerpolicy="no-referrer"
                  >
                  <router-link
                    :to="`/subscription/${video.subscriptions[0].id}/all`"
                    class="text-xs md:text-sm lg:text-base text-white font-medium hover:text-[#3ea6ff] transition-colors"
                  >
                    {{ video.subscriptions[0].name }}
                  </router-link>
                  <button
                    class="px-3 py-1.5 text-xs bg-white/10 hover:bg-white/15 text-white rounded-full transition-colors font-medium"
                    @click.stop="handleUnsubscribe(video.subscriptions[0].id)"
                    :title="`取消订阅 ${video.subscriptions[0].name}`"
                    :aria-label="`取消订阅 ${video.subscriptions[0].name}`"
                  >取消订阅</button>
                </div>

                <!-- 主订阅统计信息 -->
                <div class="ml-11 md:ml-12 text-[10px] text-[#aaaaaa] mt-1">
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
                    class="flex items-center px-2 py-1 rounded-full bg-white/5 hover:bg-white/10 cursor-pointer transition-colors text-[11px] text-[#e5e5e5]"
                    @click.stop="$router.push(`/subscription/${sub.id}/all`)"
                  >
                    <img
                      :src="sub.avatar"
                      :alt="sub.name"
                      class="w-5 h-5 rounded-full object-cover mr-2"
                      referrerpolicy="no-referrer"
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
      <div :class="['md:w-[320px] lg:w-[400px] md:ml-6', isWidescreen ? 'hidden' : 'hidden md:block']">
        <div class="sticky top-4">
          <div class="rounded-xl px-4 pb-4 pt-0 flex flex-col">
            <h2 class="text-white text-lg mb-4">相关视频</h2>
            <div>
              <div v-if="!relatedVideos.length && !loadingRelated" class="text-gray-400 text-sm">暂无推荐</div>
              <div v-if="relatedVideos.length" class="space-y-3">
                <div
                  v-for="relatedVideo in relatedVideos"
                  :key="relatedVideo.id"
                  class="flex space-x-3 cursor-pointer group"
                  @click="goToVideo(relatedVideo.id, relatedVideo)"
                >
                  <div class="relative w-40 h-24 rounded-lg overflow-hidden bg-black/60">
                    <img
                      :src="relatedVideo.thumbnail"
                      referrerpolicy="no-referrer"
                      class="w-full h-full object-cover transition-transform duration-200 group-hover:scale-105 pointer-events-none select-none"
                      draggable="false"
                      :alt="relatedVideo.title"
                    >
                    <div class="absolute bottom-1 right-1 bg-black/70 text-white text-[10px] px-1 py-0.5 rounded">
                      {{ formatDuration(relatedVideo.duration) }}
                    </div>
                  </div>
                  <div class="flex-1 min-w-0">
                    <div class="text-white text-xs leading-5 max-h-10 overflow-hidden group-hover:text-[#3ea6ff] transition-colors">
                      {{ relatedVideo.title }}
                    </div>
                    <div class="text-[#aaaaaa] text-[10px] mt-1 truncate">
                      <router-link
                        v-if="relatedVideo.subscriptions?.[0]?.id"
                        :to="`/subscription/${relatedVideo.subscriptions[0].id}/all`"
                        @click.stop
                        class="hover:text-[#3ea6ff] transition-colors"
                      >
                        {{ relatedVideo.subscriptions[0].name }}
                      </router-link>
                      <span v-else>
                        {{ relatedVideo.site }}
                      </span>
                    </div>
                    <div
                      v-if="relatedVideo.uploaded_at"
                      class="text-[#777777] text-[10px] mt-0.5 truncate"
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
import { ref, onMounted, watch, computed, nextTick } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useSubscriptionApi } from '../composables/useSubscriptionApi';
import usePlaybackOrchestrator from '../composables/usePlaybackOrchestrator';
import usePlaybackReporting from '../composables/usePlaybackReporting';
import useOptionsDropdown from '../composables/useOptionsDropdown';
import VideoPlayer from '../components/video-player/VideoPlayer.vue';
import { Icon } from '@iconify/vue';
import useOptionsMenu from '../composables/useOptionsMenu';
import useVideoHistory from "../composables/useVideoHistory";
import { formatDate, formatDuration } from '../utils/dateFormat';
import useVideoInteraction from "../composables/useVideoInteraction.js";
import { useVideoApi } from '../composables/useVideoApi';



const route = useRoute();
const router = useRouter();

// 内部切换不使用 router，所以不需要从 history.state 读取初始数据
const { video, startTime, relatedVideos, loadingRelated, loadAndPlayById, externalError } = usePlaybackOrchestrator(null);
const { sendReport } = useVideoHistory();
const { downloadVideo } = useOptionsMenu(video);
const { INTERACTION_TYPE, toggleLike, deleteInteraction } = useVideoInteraction();
const { onVideoPlay, onVideoPause, onVideoEnded, onVideoTimeUpdate } = usePlaybackReporting(video, sendReport);
const { showMoreOptions, handleMoreOptionsClick } = useOptionsDropdown();
const { unsubscribe: apiUnsubscribe } = useSubscriptionApi();
const { getRandomVideo } = useVideoApi();

// 视频播放器引用
const videoPlayerRef = ref(null);

// 宽屏模式
const isWidescreen = ref(false);
const toggleWidescreen = (value) => {
  isWidescreen.value = value;
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
    await toggleLike(video.id, interactionType).then(() => {
      video.interaction_type = interactionType;
    });
  } else {
    await deleteInteraction(video.id).then(() => {
      video.interaction_type = null;
    })
  }
};

const handleLater = async (video) => {
  if (video.interaction_type !== INTERACTION_TYPE.LATER) {
    await toggleLike(video.id, INTERACTION_TYPE.LATER).then(() => {
      video.interaction_type = INTERACTION_TYPE.LATER;
    });
  } else {
    await deleteInteraction(video.id).then(() => {
      video.interaction_type = null;
    });
  }
};

const handleDownload = async () => {
  await downloadVideo();
};

const handlePlayRandom = async () => {
  const params = {};
  
  // 尝试多次获取，跳过最近播放过的视频
  let attempts = 0;
  const maxAttempts = 3;
  
  while (attempts < maxAttempts) {
    const res = await getRandomVideo(params);
    if (res.success && res.data?.id) {
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
  if (res.success && res.data?.id) {
    await goToVideo(res.data.id, res.data);
  }
};


// 聚焦到视频播放器，使键盘控制生效
const focusVideoPlayer = async () => {
  await nextTick();
  // 延迟一点，确保 DOM 已经完全渲染
  setTimeout(() => {
    try {
      const playerContainer = videoPlayerRef.value?.$el?.querySelector('.video-player-container');
      if (playerContainer && typeof playerContainer.focus === 'function') {
        playerContainer.focus({ preventScroll: true });
      }
    } catch (e) {
      console.debug('Failed to focus video player:', e);
    }
  }, 100);
};

const goToVideo = async (id, videoData = null) => {
  if (!id) return;
  if (video.value?.id === id) return;
  
  // 记录当前视频到播放历史（如果有的话）
  if (video.value?.id && !recentlyPlayed.value.includes(video.value.id)) {
    recentlyPlayed.value.push(video.value.id);
    // 只保留最近5个视频的历史
    if (recentlyPlayed.value.length > 5) {
      recentlyPlayed.value.shift();
    }
  }
  
  // 切换到新视频前，先停止当前播放，避免在新视频无法获取播放链接时旧视频继续播放
  try {
    const core = videoPlayerRef.value?.videoPlayerRef?.videoCore || videoPlayerRef.value?.videoCore;
    if (core?.videoElement) {
      try {
        core.videoElement.pause();
        core.videoElement.removeAttribute('src');
        core.videoElement.load();
      } catch (_) {}
    }
    if (core?.audioElement) {
      try {
        core.audioElement.pause();
        core.audioElement.removeAttribute('src');
        core.audioElement.load();
      } catch (_) {}
    }
  } catch (_) {}
  
  // 使用 history.replaceState 直接更新 URL，不触发 Vue Router 的任何逻辑
  // 注意：history.state 只能存储可序列化的简单数据，不能存储复杂对象
  if (route.params.videoId !== id) {
    const newUrl = `/video/${id}`;
    try {
      // 只传递基础的、可序列化的数据
      const simpleState = videoData ? {
        videoId: videoData.id,
        title: videoData.title,
        thumbnail: videoData.thumbnail,
      } : {};
      window.history.replaceState(simpleState, '', newUrl);
    } catch (e) {
      console.warn('Failed to update history state:', e);
      // 如果失败，仍然更新URL，只是不带state
      window.history.replaceState({}, '', newUrl);
    }
  }
  
  // 直接加载视频，不依赖路由watch
  await loadAndPlayById(id, videoData);
  // 视频加载后自动聚焦播放器
  await focusVideoPlayer();
};

const handleAutoplayNext = async (evt) => {
  try {
    try { onVideoEnded(); } catch (_) {}
    const autoplayEnabled = evt?.autoplay !== undefined ? evt.autoplay : true;
    const autoplayNextEnabled = evt?.autoplayNext !== undefined ? evt.autoplayNext : true;
    const loopEnabled = evt?.loop !== undefined ? evt.loop : false;
    if (!autoplayEnabled || !autoplayNextEnabled || loopEnabled) return;

    // 查找第一个未在最近播放历史中的视频
    const next = relatedVideos.value?.find(v => !recentlyPlayed.value.includes(v.id));
    if (next?.id) {
      await goToVideo(next.id, next);
      return;
    }
    
    // 如果所有相关视频都播放过，随机播放一个
    await handlePlayRandom();
  } catch (_) {}
};


onMounted(async () => {
  // 初始加载时从API获取数据
  await loadAndPlayById(route.params.videoId);
  await focusVideoPlayer();
});

watch(() => route.params.videoId, async (newId, oldId) => {
  // 只有从外部导航进来才需要重新加载
  // 内部切换（goToVideo）已经调用了loadAndPlayById，不需要重复加载
  if (newId && newId !== oldId && video.value?.id !== newId) {
    await loadAndPlayById(newId);
    await focusVideoPlayer();
  }
});

</script>

<style scoped>
/* 视频区域容器样式 */
.video-section {
  position: relative;
  width: 100%;
  background: #000000;
  margin: 0 auto;
  border-radius: 4px;
  overflow: hidden;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.4);
}

.video-container {
  position: relative;
  width: 100%;
  height: 0;
  padding-bottom: 56.25%; /* 16:9 比例 */
  overflow: hidden;
  background: #000000;
}

.video-container :deep(iframe),
.video-container :deep(video),
.video-container :deep(.xgplayer) {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: #000;
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
    border-radius: 0;
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