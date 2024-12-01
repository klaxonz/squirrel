<template>
  <div class="podcasts-page flex flex-col h-full bg-[#0f0f0f] text-white">
    <SearchBar class="pt-4 px-4" @search="handleSearch" ref="searchBar"/>
    
    <!-- 主要内容区域 -->
    <div class="flex-grow overflow-y-auto px-4 py-4">
      <div class="max-w-[1800px] mx-auto">
        <!-- 播客列表 -->
        <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-4">
          <!-- 播客卡片 -->
          <div v-for="podcast in podcasts" :key="podcast.id" 
               class="bg-[#1f1f1f] rounded-lg overflow-hidden hover:bg-[#272727] transition-all duration-200">
            <div class="aspect-square">
              <img :src="podcast.cover_url" :alt="podcast.title" 
                   class="w-full h-full object-cover"
                   referrerpolicy="no-referrer">
            </div>
            <div class="p-4">
              <h3 class="text-sm font-medium line-clamp-2">{{ podcast.title }}</h3>
              <p class="text-xs text-[#aaaaaa] mt-1">{{ podcast.author }}</p>
            </div>
          </div>
        </div>

        <!-- 加载状态 -->
        <div v-if="loading" class="flex justify-center py-8">
          <div class="flex space-x-2">
            <div class="w-2 h-2 bg-[#cc0000] rounded-full animate-bounce"></div>
            <div class="w-2 h-2 bg-[#cc0000] rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
            <div class="w-2 h-2 bg-[#cc0000] rounded-full animate-bounce" style="animation-delay: 0.4s"></div>
          </div>
        </div>

        <!-- 无数据提示 -->
        <div v-if="!loading && podcasts.length === 0" class="text-center py-8 text-[#aaaaaa]">
          暂无播客内容
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import SearchBar from '../components/SearchBar.vue';

const searchBar = ref(null);
const loading = ref(false);
const podcasts = ref([]);

const handleSearch = (keyword) => {
  // 处理搜索逻辑
  console.log('Search:', keyword);
};
</script>

<style scoped>
.podcasts-page {
  height: 100vh;
}

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style> 