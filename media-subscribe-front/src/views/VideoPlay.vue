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
          <h1 class="text-xs md:text-sm lg:text-xl lg:font-medium text-white">{{ video?.title }}</h1>
          
          <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between mt-2 pb-3 border-b border-[#272727]">
            <!-- 频道信息 -->
            <div class="flex items-center">
              <img 
                :src="video?.channel_avatar" 
                :alt="video?.channel_name"
                class="w-6 h-6 md:w-7 md:h-7 lg:w-10 lg:h-10 rounded-full object-cover"
                referrerpolicy="no-referrer"
              >
              <div class="ml-2 md:ml-2.5 lg:ml-3">
                <router-link 
                  :to="`/channel/${video?.channel_id}/all`"
                  class="text-xs md:text-sm lg:text-base text-white font-medium hover:text-[#3ea6ff] transition-colors"
                >
                  {{ video?.channel_name }}
                </router-link>
              </div>
            </div>

            <!-- 操作按钮组 -->
            <div class="grid grid-cols-3 gap-1 mt-2 xl:flex xl:items-center xl:justify-start xl:space-x-2 xl:mt-0">
              <button 
                @click="handleLike"
                class="flex flex-col items-center justify-center px-1 py-1 xl:flex-row xl:space-x-1 xl:px-3 xl:py-1.5 rounded-full hover:bg-[#272727] transition-colors text-[10px] xl:text-xs"
                :class="{ 'text-[#3ea6ff]': video?.is_liked === 1 }"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 xl:h-5 xl:w-5" :fill="video?.is_liked === 1 ? 'currentColor' : 'none'" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" />
                </svg>
                <span class="mt-0.5 xl:mt-0">{{ video?.is_liked === 1 ? '已喜欢' : '喜欢' }}</span>
              </button>

              <button 
                @click="handleDownload"
                class="flex flex-col items-center justify-center px-1 py-1 xl:flex-row xl:space-x-1 xl:px-3 xl:py-1.5 rounded-full hover:bg-[#272727] transition-colors text-[10px] xl:text-xs"
                :class="{ 'text-[#3ea6ff]': video?.if_downloaded }"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 xl:h-5 xl:w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                <span class="mt-0.5 xl:mt-0">{{ video?.if_downloaded ? '已下载' : '下载' }}</span>
              </button>

              <button 
                @click="handleCopyLink"
                class="flex flex-col items-center justify-center px-1 py-1 xl:flex-row xl:space-x-1 xl:px-3 xl:py-1.5 rounded-full hover:bg-[#272727] transition-colors text-[10px] xl:text-xs"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 xl:h-5 xl:w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                <span class="mt-0.5 xl:mt-0">分享</span>
              </button>
            </div>
          </div>

          <!-- 视频描述 -->
          <div class="mt-4 p-3 bg-[#272727] rounded-xl">
            <div class="flex items-center text-[10px] md:text-xs lg:text-sm text-[#aaaaaa] space-x-4 mb-2">
              <span>{{ formatDuration(video?.duration) }}</span>
              <span>{{ formatDate(video?.uploaded_at) }}</span>
              <span>{{ video?.if_read ? '已观看' : '未观看' }}</span>
            </div>
            <p class="text-[10px] md:text-xs lg:text-sm text-white whitespace-pre-wrap">{{ video?.title }}</p>
          </div>
        </div>
      </div>

      <!-- 右侧区域 - 可以添加相关视频列表等内容 -->
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
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useToast } from 'vue-toastification';
import axios from '../utils/axios';
import VideoPlayer from '../components/VideoPlayer.vue';
import { useVideoHistory } from '../composables/useVideoHistory';

const toast = useToast();
const route = useRoute();
const { updateWatchHistory } = useVideoHistory();

const video = ref(null);
const channelId = computed(() => route.params.channelId);
const videoId = computed(() => route.params.videoId);

// 计算起始放时间
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

// 获取视频详情
const fetchVideoDetails = async () => {
  try {
    const response = await axios.get(`/api/channel-video/video?channel_id=${channelId.value}&video_id=${videoId.value}`);
    video.value = response.data.data;
  } catch (error) {
    console.error('Failed to fetch video details:', error);
    toast.error('获取视频信息失败');
  }
};

// 视频播放控制
const onVideoPlay = () => {
  video.value.isPlaying = true;
};

const onVideoPause = () => {
  video.value.isPlaying = false;
};

const onVideoEnded = () => {
  updateWatchHistory(
    video.value.video_id,
    video.value.channel_id,
    video.value.duration,
    video.value.duration
  );
  video.value.if_read = true;
};

const onVideoTimeUpdate = (currentTime) => {
  if (Math.floor(currentTime) % 5 === 0) {
    updateWatchHistory(
      video.value.video_id,
      video.value.channel_id,
      currentTime,
      video.value.duration
    );
    video.value.last_position = currentTime;
    video.value.progress = (currentTime / video.value.duration) * 100;
  }
};

// 操作处理
const handleLike = async () => {
  try {
    const response = await axios.post(`/api/videos/${videoId.value}/like`, {
      is_liked: video.value?.is_liked === 1 ? 0 : 1
    });
    video.value = { ...video.value, is_liked: response.data.is_liked };
    toast.success(response.data.is_liked === 1 ? '已添加到喜欢' : '已取消喜欢');
  } catch (error) {
    toast.error('操作失败');
  }
};

const handleDownload = async () => {
  if (video.value?.if_downloaded) {
    toast.info('视频已下载');
    return;
  }
  try {
    await axios.post(`/api/videos/${videoId.value}/download`);
    video.value.if_downloaded = true;
    toast.success('已添加到下载队列');
  } catch (error) {
    toast.error('添加下载任务失败');
  }
};

const handleCopyLink = () => {
  const link = video.value?.url || '';
  navigator.clipboard.writeText(link)
    .then(() => toast.success('链接已复制'))
    .catch(() => toast.error('复制失败'));
};

// 格式化函数
const formatDate = (date) => {
  if (!date) return '';
  return new Date(date).toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });
};

const formatDuration = (seconds) => {
  if (!seconds) return '00:00';
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
};

const getDomain = (domain) => {
  if (!domain) return '';
  return domain.charAt(0).toUpperCase() + domain.slice(1).replace('.com', '');
};

onMounted(() => {
  fetchVideoDetails();
});
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
</style> 