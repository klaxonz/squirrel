<template>
  <div class="video-page bg-[#0f0f0f] min-h-screen scrollbar">
    <div class="max-w-[1720px] mx-auto lg:px-6 pt-6 flex">
      <!-- 左侧主内容区域 -->
      <div class="flex-1 max-w-[1280px]">
        <!-- 视频播放区域 -->
        <div class="video-section">
          <div class="video-container">
            <VideoPlayer
              v-if="video"
              :video="video"
              :initialTime="startTime"
              @play="onVideoPlay"
              @pause="onVideoPause"
              @ended="onVideoEnded"
              @timeupdate="onVideoTimeUpdate"
            />
          </div>
        </div>

        <!-- 视频信息区域 -->
        <div class="mt-3 px-4">
          <!-- 视频标题 -->
          <h1 class="text-xs md:text-sm lg:text-base lg:font-medium text-white">{{ video?.video_title }}</h1>

          <!-- 频道信息和操作按钮区域 -->
          <div class="mt-3 pb-3 border-b border-[#272727]">
            <div class="flex items-center justify-between">
              <!-- 订阅信息 -->
              <div class="flex items-center">
                <!-- 层叠的头像 -->
                <div class="flex -space-x-3">
                  <img
                    v-for="(sub, index) in video?.subscriptions"
                    :key="sub.id"
                    :src="sub.avatar"
                    :alt="sub.name"
                    class="w-8 h-8 md:w-9 md:h-9 lg:w-10 lg:h-10 rounded-full object-cover ring-2 ring-[#0f0f0f]"
                    :class="{'relative z-30': index === 0, 'relative z-20': index === 1, 'relative z-10': index === 2}"
                    referrerpolicy="no-referrer"
                  >
                </div>
                <!-- 订阅名称 -->
                <div class="ml-3 flex items-center">
                  <router-link
                    v-for="(sub, index) in video?.subscriptions"
                    :key="sub.id"
                    :to="`/subscription/${sub.id}/all`"
                    class="text-xs md:text-sm lg:text-base text-white font-medium hover:text-[#3ea6ff] transition-colors"
                  >
                    {{ sub.name }}{{ index < video?.subscriptions.length - 1 ? ',' : '' }}
                    <span v-if="index < video?.subscriptions.length - 1" class="mx-1 text-[#aaaaaa]"></span>
                  </router-link>
                </div>
              </div>

              <!-- 操作按钮组 -->
              <div class="flex items-center space-x-1">
                <!-- 主要按钮显示在外面 -->
                <button
                  @click="handleLike(video, INTERACTION_TYPE.LIKE)"
                  class="p-2 rounded-full hover:bg-[#272727] transition-colors"
                  :class="{ 'text-red-500': video?.interaction_type === INTERACTION_TYPE.LIKE }"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" :fill="video?.interaction_type === INTERACTION_TYPE.LIKE ? 'currentColor' : 'none'" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" />
                  </svg>
                </button>

                <button
                  @click="handleLike(video, INTERACTION_TYPE.DISLIKE)"
                  class="p-2 rounded-full hover:bg-[#272727] transition-colors"
                  :class="{ 'text-gray-400': video?.interaction_type === INTERACTION_TYPE.DISLIKE }"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 transform rotate-180" :fill="video?.interaction_type === INTERACTION_TYPE.DISLIKE ? 'currentColor' : 'none'" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" />
                  </svg>
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
	                  <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
	                    <path d="M14 3h7v7h-2V6.414l-9.293 9.293-1.414-1.414L17.586 5H14V3z" />
	                    <path d="M5 5h6v2H7v10h10v-4h2v6H5V5z" />
	                  </svg>
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
          </div>

          <!-- 视频描述 -->
          <div class="mt-4 p-3 bg-[#272727] rounded-xl">
            <div class="flex items-center text-[10px] md:text-xs lg:text-sm text-[#aaaaaa] space-x-4 mb-2">
              <span>{{ formatDuration(video?.duration) }}</span>
              <span>{{ formatDate(video?.publish_date) }}</span>
              <span>{{ video?.if_read ? '已观看' : '未观看' }}</span>
            </div>
            <p class="text-[10px] md:text-xs lg:text-sm text-white whitespace-pre-wrap">{{ video?.title }}</p>
          </div>
        </div>
      </div>

      <!-- 右侧区域 - 可以加相关视频列表等内容 -->
      <div class="hidden lg:block w-[400px] ml-6">
        <div class="sticky top-4">
          <!-- 这里可以添加相关视频列表或其他内容 -->
          <div class="bg-[#272727] rounded-xl p-4">
            <h2 class="text-white text-lg mb-4">相关视频</h2>
            <!-- 相关视频列表将在这里添加 -->
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useRoute } from 'vue-router';
import axios from '../utils/axios';
import VideoPlayer from '../components/video-player/VideoPlayer.vue';
import useOptionsMenu from '../composables/useOptionsMenu';
import useVideoHistory from "../composables/useVideoHistory";
import { formatDate, formatDuration } from '../utils/dateFormat';
import useVideoInteraction from "../composables/useVideoInteraction.js";

const route = useRoute();
const video = ref(null);
const { sendReport } = useVideoHistory();
const { downloadVideo } = useOptionsMenu(video);
const { INTERACTION_TYPE, toggleLike, deleteInteraction } = useVideoInteraction();

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

const handleDownload = async () => {
  await downloadVideo();
};





const startTime = computed(() => {
  if (video.value?.last_position) {
    const { last_position, total_duration } = video.value;

    if (!total_duration || total_duration <= 0 || !last_position || last_position <= 0) {
      return 0;
    }

    const progress = (last_position / total_duration) * 100;
    const remainingTime = total_duration - last_position;

    // 判断是否接近结尾，如果是则从头开始
    let isNearEnd = false;

    if (total_duration < 300) {
      // 短视频（少于5分钟），85%就算看完
      isNearEnd = progress >= 85;
    } else if (total_duration < 1800) {
      // 中等长度视频（5-30分钟），90%或剩余时间少于2分钟就算看完
      isNearEnd = progress >= 90 || remainingTime < 120;
    } else {
      // 长视频（超过30分钟），95%或剩余时间少于3分钟就算看完
      isNearEnd = progress >= 95 || remainingTime < 180;
    }

    return isNearEnd ? 0 : last_position;
  }
  return 0;
});

const fetchVideoDetails = async () => {
  try {
    const response = await axios.get(`/api/video/detail?video_id=${route.params.videoId}`);
    video.value = response.data.data;
  } catch (error) {
    console.error('Failed to fetch video details:', error);
  }
};

const onVideoPlay = () => {
  video.value.isPlaying = true;
};

const onVideoPause = () => {
  video.value.isPlaying = false;
};

const onVideoEnded = () => {
  video.value.if_read = true;
};

let lastReportedTime = 0;
const onVideoTimeUpdate = (currentTime) => {
  if (Math.floor(currentTime) - lastReportedTime >= 2) {
    lastReportedTime = Math.floor(currentTime);
    video.value.last_position = currentTime;
    video.value.progress = (currentTime / video.value.duration) * 100;
    // Fire-and-forget report without waiting for response
    (async () => {
      try {
        await sendReport(video.value.id, currentTime);
      } catch (e) {
        // Silently ignore reporting errors
      }
    })();
  }
};

const showMoreOptions = ref(false);

const handleClickOutside = (event) => {
  const dropdown = document.querySelector('.relative');
  if (dropdown && !dropdown.contains(event.target)) {
    showMoreOptions.value = false;
  }
};

const handleEscKey = (event) => {
  if (event.key === 'Escape') {
    showMoreOptions.value = false;
  }
};

onMounted(() => {
  document.addEventListener('click', handleClickOutside);
  document.addEventListener('keydown', handleEscKey);
    fetchVideoDetails().then(async () => {
      try {
        // 注入字幕：仅对 bilibili 视频尝试获取 ai-zh SRT
        if (video.value && /bilibili\.com/.test(video.value.url)) {
          const subResp = await axios.get(`/api/video/subtitles`, {
            params: { video_id: route.params.videoId, lang: 'ai-zh', fmt: 'srt' },
            responseType: 'text'
          });

          if (subResp && typeof subResp.data === 'string' && subResp.data.length > 0) {
            // 生成一个 blob URL 供播放器拉取，避免跨域问题
            const blob = new Blob([subResp.data], { type: 'text/plain;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            const subtitle = { id: 'bili-ai-zh', language: '简体中文(AI)', url };
            if (!video.value.subtitles) video.value.subtitles = [];
            // 置顶并作为默认
            video.value.subtitles = [subtitle, ...video.value.subtitles];
          }
        }
      } catch (e) {
        // 静默失败，不影响播放
      }

    });
});

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside);
  document.removeEventListener('keydown', handleEscKey);
});

const handleMoreOptionsClick = (event) => {
  event.stopPropagation();
  showMoreOptions.value = !showMoreOptions.value;
};


</script>

<style scoped>
/* 视频区域容器样式 */
.video-section {
  position: relative;
  width: 100%;
  background: #000000;
  margin: 0 auto;
  border-radius: 12px;
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