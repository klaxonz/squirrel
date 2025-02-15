<template>
  <div class="video-page bg-[#0f0f0f] min-h-screen">
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
                  @click="handleLike(1)"
                  class="p-2 rounded-full hover:bg-[#272727] transition-colors"
                  :class="{ 'text-red-500': video?.is_liked === 1 }"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" :fill="video?.is_liked === 1 ? 'currentColor' : 'none'" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" />
                  </svg>
                </button>

                <button 
                  @click="handleLike(0)"
                  class="p-2 rounded-full hover:bg-[#272727] transition-colors"
                  :class="{ 'text-gray-400': video?.is_liked === 0 }"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 transform rotate-180" :fill="video?.is_liked === 0 ? 'currentColor' : 'none'" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" />
                  </svg>
                </button>

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
                      <button
                        @click="handleCopyLink"
                        class="flex items-center w-full px-4 py-2 text-sm text-white hover:bg-[#3f3f3f]"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                        </svg>
                        <span class="whitespace-nowrap">分享</span>
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
import VideoPlayer from '../components/VideoPlayer.vue';
import { useVideoHistory } from '../composables/useVideoHistory';
import useOptionsMenu from '../composables/useOptionsMenu';
import { formatDate, formatDuration } from '../utils/dateFormat';

const route = useRoute();
const video = ref(null);

const { toggleLikeVideo, downloadVideo, copyVideoLink } = useOptionsMenu(video);

const handleLike = async (targetStatus) => {
  await toggleLikeVideo(targetStatus);
};

const handleDownload = async () => {
  await downloadVideo();
};

const handleCopyLink = () => {
  copyVideoLink();
};

const startTime = computed(() => {
  if (video.value?.last_position) {
    if (video.value.total_duration - video.value.last_position < 10) {
      return 0;
    } else {
      return video.value.last_position;
    }
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

const onVideoTimeUpdate = (currentTime) => {
  if (Math.floor(currentTime) % 5 === 0) {
    video.value.last_position = currentTime;
    video.value.progress = (currentTime / video.value.duration) * 100;
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
  fetchVideoDetails();
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
  background: #000;
  margin: 0 auto;
}

.video-container {
  position: relative;
  width: 100%;
  height: 0;
  padding-bottom: 56.25%; /* 16:9 比例 */
  overflow: hidden;
  border-radius: 4px;
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

/* 添加滚动条样式 */
.video-page {
  scrollbar-width: thin;
  scrollbar-color: #606060 #0f0f0f;
}

.video-page::-webkit-scrollbar {
  width: 8px;
}

.video-page::-webkit-scrollbar-track {
  background: #0f0f0f;
}

.video-page::-webkit-scrollbar-thumb {
  background-color: #606060;
  border-radius: 4px;
}

.video-page::-webkit-scrollbar-thumb:hover {
  background-color: #909090;
}

/* 隐藏滚动条但保持可滚动 */
.no-scrollbar {
  -ms-overflow-style: none;  /* IE and Edge */
  scrollbar-width: none;  /* Firefox */
}

.no-scrollbar::-webkit-scrollbar {
  display: none;  /* Chrome, Safari and Opera */
}
</style> 