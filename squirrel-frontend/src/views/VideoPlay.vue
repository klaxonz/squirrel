<template>
  <div class="video-page bg-[#0f0f0f] min-h-screen scrollbar min-w-[1200px]">
    <div class="max-w-[1720px] mx-auto lg:px-6 pt-6 flex min-w-[1200px]">
      <!-- 左侧主内容区域 -->
      <div class="flex-1 max-w-[1280px]">
        <!-- 视频播放区域 -->
        <div class="video-section">
          <div class="video-container">
            <VideoPlayer
              :key="video?.id"
              v-if="video"
              :video="video"
              :initialTime="startTime"
              @play="onVideoPlay"
              @pause="onVideoPause"
              @ended="handleAutoplayNext"
              @timeupdate="onVideoTimeUpdate"
            />
          </div>
        </div>

        <!-- 视频信息区域 -->
        <div class="mt-3 px-4">
          <!-- 标题与操作按钮 -->
          <div class="flex items-center justify-between">
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
                <IconShuffle class="h-5 w-5" />
              </button>
              <!-- 主要按钮显示在外面 -->
              <button
                @click="handleLike(video, INTERACTION_TYPE.LIKE)"
                class="p-2 rounded-full hover:bg-[#272727] transition-colors"
                :class="{ 'text-red-500': video?.interaction_type === INTERACTION_TYPE.LIKE }"
              >
                <IconThumbUp class="h-5 w-5" :filled="video?.interaction_type === INTERACTION_TYPE.LIKE" />
              </button>

              <button
                @click="handleLike(video, INTERACTION_TYPE.DISLIKE)"
                class="p-2 rounded-full hover:bg-[#272727] transition-colors"
                :class="{ 'text-gray-400': video?.interaction_type === INTERACTION_TYPE.DISLIKE }"
              >
                <IconThumbDown class="h-5 w-5" :filled="video?.interaction_type === INTERACTION_TYPE.DISLIKE" />
              </button>

              <button
                @click="handleLater(video)"
                class="p-2 rounded-full hover:bg-[#272727] transition-colors"
                :class="{ 'text-blue-400': video?.interaction_type === INTERACTION_TYPE.LATER }"
                title="稍后看"
                aria-label="稍后看"
              >
                <IconClock class="h-5 w-5" :filled="video?.interaction_type === INTERACTION_TYPE.LATER" />
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
                <IconExternal class="h-5 w-5" />
	                </a>


              <!-- 更多按钮 - 点击显示下拉菜单 -->
              <div class="relative">
                <button
                  @click="handleMoreOptionsClick"
                  class="p-2 rounded-full hover:bg-[#272727] transition-colors"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
                  </svg>
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

          <!-- 频道信息 -->
          <div class="mt-3 pb-3 border-b border-[#272727]">
            <div class="flex flex-col space-y-3">
              <div v-for="sub in video?.subscriptions" :key="sub.id" class="flex flex-col">
                <!-- 头像、频道名称、取消订阅按钮在同一行 -->
                <div class="flex items-center space-x-3">
                  <img
                    :src="sub.avatar"
                    :alt="sub.name"
                    class="w-8 h-8 md:w-9 md:h-9 lg:w-10 lg:h-10 rounded-full object-cover"
                    referrerpolicy="no-referrer"
                  >
                  <router-link
                    :to="`/subscription/${sub.id}/all`"
                    class="text-xs md:text-sm lg:text-base text-white font-medium hover:text-[#3ea6ff] transition-colors"
                  >
                    {{ sub.name }}
                  </router-link>
                  <button
                    class="px-3 py-1.5 text-xs bg-white/10 hover:bg-white/15 text-white rounded-full transition-colors font-medium"
                    @click.stop="handleUnsubscribe(sub.id)"
                    :title="`取消订阅 ${sub.name}`"
                    :aria-label="`取消订阅 ${sub.name}`"
                  >取消订阅</button>
                </div>
                <!-- 统计信息单独一行 -->
                <div class="ml-11 md:ml-12 lg:ml-13 text-[10px] text-[#aaaaaa] mt-1">
                  总视频: {{ sub.total_videos || 0 }} | 已解析: {{ sub.total_extract || 0 }}
                </div>
              </div>
            </div>
          </div>

        </div>
      </div>

      <!-- 右侧区域 - 相关视频 -->
      <div class="hidden md:block md:w-[320px] lg:w-[400px] md:ml-6">
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
                  @click="goToVideo(relatedVideo.id)"
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
import { ref, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useSubscriptionApi } from '../composables/useSubscriptionApi';
import usePlaybackOrchestrator from '../composables/usePlaybackOrchestrator';
import usePlaybackReporting from '../composables/usePlaybackReporting';
import useOptionsDropdown from '../composables/useOptionsDropdown';
import VideoPlayer from '../components/video-player/VideoPlayer.vue';
import IconShuffle from '../components/icons/IconShuffle.vue';
import IconThumbUp from '../components/icons/IconThumbUp.vue';
import IconThumbDown from '../components/icons/IconThumbDown.vue';
import IconClock from '../components/icons/IconClock.vue';
import IconExternal from '../components/icons/IconExternal.vue';
import useOptionsMenu from '../composables/useOptionsMenu';
import useVideoHistory from "../composables/useVideoHistory";
import { formatDate, formatDuration } from '../utils/dateFormat';
import useVideoInteraction from "../composables/useVideoInteraction.js";
import { useVideoApi } from '../composables/useVideoApi';



const route = useRoute();
const router = useRouter();
const { video, startTime, relatedVideos, loadingRelated, loadAndPlayById } = usePlaybackOrchestrator();
const { sendReport } = useVideoHistory();
const { downloadVideo } = useOptionsMenu(video);
const { INTERACTION_TYPE, toggleLike, deleteInteraction } = useVideoInteraction();
const { onVideoPlay, onVideoPause, onVideoEnded, onVideoTimeUpdate } = usePlaybackReporting(video, sendReport);
const { showMoreOptions, handleMoreOptionsClick } = useOptionsDropdown();
const { unsubscribe: apiUnsubscribe } = useSubscriptionApi();
const { getRandomVideo } = useVideoApi();

// 记录最近播放的视频，防止循环播放
const recentlyPlayed = ref([]);

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
  const site = video.value?.domain || video.value?.site;
  if (site) params.site = site;
  
  // 尝试多次获取，跳过最近播放过的视频
  let attempts = 0;
  const maxAttempts = 3;
  
  while (attempts < maxAttempts) {
    const res = await getRandomVideo(params);
    if (res.success && res.data?.id) {
      // 如果这个视频不在最近播放历史中，就播放它
      if (!recentlyPlayed.value.includes(res.data.id)) {
        await goToVideo(res.data.id);
        return;
      }
    }
    attempts++;
  }
  
  // 如果尝试3次都是最近播放过的，就播放最后一个
  const res = await getRandomVideo(params);
  if (res.success && res.data?.id) {
    await goToVideo(res.data.id);
  }
};


const goToVideo = async (id) => {
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
  
  await router.replace(`/video/${id}`);
  await loadAndPlayById(id);
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
      await goToVideo(next.id);
      return;
    }
    
    // 如果所有相关视频都播放过，随机播放一个
    await handlePlayRandom();
  } catch (_) {}
};


onMounted(() => {
  loadAndPlayById(route.params.videoId);
});

watch(() => route.params.videoId, async () => {
  await loadAndPlayById(route.params.videoId);
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
</style>