<template>
  <div 
    class="podcast-card bg-[#1f1f1f] rounded-lg overflow-hidden hover:bg-[#272727] transition-all duration-200 cursor-pointer"
    @click="handleClick"
  >
    <!-- 横向布局 -->
    <div class="flex p-3">
      <!-- 封面图 -->
      <div class="relative w-16 h-16 flex-shrink-0">
        <img 
          :src="podcast.cover_url" 
          :alt="podcast.title" 
          class="w-full h-full object-cover rounded"
          referrerpolicy="no-referrer"
        >
        <!-- 播放状态指示器 -->
        <div v-if="isPlaying" class="absolute bottom-1 right-1 bg-[#cc0000] text-white p-0.5 rounded-full">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd" />
          </svg>
        </div>
        <!-- 进度条 -->
        <div v-if="progress" class="absolute bottom-0 left-0 right-0 h-1 bg-black/40">
          <div 
            class="h-full bg-[#cc0000] transition-all duration-200"
            :style="{ width: `${progress * 100}%` }"
          ></div>
        </div>
      </div>

      <!-- 信息 -->
      <div class="ml-3 flex-grow min-w-0">
        <h3 class="text-sm font-medium line-clamp-1 group-hover:text-[#cc0000] transition-colors">
          {{ podcast.title }}
        </h3>
        <p class="text-xs text-[#aaaaaa] mt-0.5 line-clamp-1">{{ podcast.author }}</p>
        <!-- 集数和更新时间 -->
        <div class="flex items-center justify-between text-xs text-[#aaaaaa] mt-2">
          <div class="flex items-center">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
            </svg>
            <span>{{ formatEpisodeCount(podcast.total_count) }}</span>
          </div>
          <div class="flex items-center">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>{{ formatLastUpdate(podcast.last_updated) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>

const props = defineProps({
  podcast: {
    type: Object,
    required: true
  },
  isPlaying: {
    type: Boolean,
    default: false
  },
  progress: {
    type: Number,
    default: 0
  }
});

const emit = defineEmits(['click']);

const formatEpisodeCount = (count) => {
  if (!count && count !== 0) return '暂无剧集';
  return `${count} 集`;
};

const formatLastUpdate = (date) => {
  if (!date) return '未知';
  const updateDate = new Date(date);
  const now = new Date();
  const diffTime = Math.abs(now - updateDate);
  const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
  
  if (diffDays === 0) return '今天更新';
  if (diffDays === 1) return '昨天更新';
  if (diffDays < 7) return `${diffDays}天前更新`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}周前更新`;
  if (diffDays < 365) return `${Math.floor(diffDays / 30)}个月前更新`;
  return `${Math.floor(diffDays / 365)}年前更新`;
};

const handleClick = () => {
  // 确保有剧集信息
  if (props.podcast.episodes && props.podcast.episodes.length > 0) {
    emit('click', {
      ...props.podcast,
      currentEpisode: props.podcast.episodes[0]
    });
  } else {
    // 如果没有剧集，显示提示
    console.warn('No episodes available');
  }
};
</script>

<style scoped>
.podcast-card {
  width: 100%;
}

.line-clamp-1 {
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style> 