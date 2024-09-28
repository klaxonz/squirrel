<template>
  <div class="latest-videos bg-gray-100 flex flex-col h-full">
    <SearchBar @search="handleSearch" ref="searchBar" />
    <TabBar v-model="activeTab" :tabs="tabsWithCounts" class="custom-tab-bar" />

    <div
      class="video-container flex-grow relative overflow-hidden"
      ref="videoContainer"
      @touchstart="handleTouchStart"
      @touchmove="handleTouchMove"
      @touchend="handleTouchEnd"
    >
      <div
        class="refresh-indicator flex items-center justify-center absolute top-0 left-0 right-0 z-10"
        :class="{ 'visible': showRefreshIndicator || isRefreshing }"
        :style="{ height: `${refreshHeight}px` }"
      >
        <svg class="animate-spin h-5 w-5 text-gray-500 mr-2" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <span class="text-gray-600">{{ isRefreshing ? '刷新中' : '下拉刷新' }}</span>
      </div>

      <div class="tab-content-wrapper">
        <div class="tab-content-inner">
          <div
            v-for="tab in tabs"
            :key="tab.value"
            v-show="activeTab === tab.value"
            class="tab-content"
            :ref="el => { if (el) tabContents[tab.value] = el.querySelector('.scroll-content') }"
          >
            <div
              class="refresh-wrapper"
              :style="{ transform: `translateY(${refreshHeight}px)` }"
            >
              <div
                class="scroll-content"
                @scroll="handleScroll($event, channelId)"
                :class="{ 'no-scroll': isResetting }"
              >
                <VideoList
                  :show-avatar="showAvatar"
                  :videos="filteredVideos[tab.value]"
                  :loading="loading && !isRefreshing"
                  :setVideoRef="setVideoRef"
                  @play="playVideo"
                  @videoPlay="onVideoPlay"
                  @videoPause="onVideoPause"
                  @videoEnded="onVideoEnded"
                  @toggleOptions="toggleOptions"
                  @goToChannel="goToChannelDetail"
                  @videoLeaveViewport="onVideoLeaveViewport"
                />

                <!-- 加载更多指示器 -->
                <div v-if="loading && !isRefreshing" class="loading-indicator text-center py-4">
                  <svg class="animate-spin h-5 w-5 text-gray-500 mx-auto" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <p class="mt-2">加载更多...</p>
                </div>

                <!-- 加载完成状态 -->
                <div v-if="allLoaded && !loading && !isRefreshing" class="text-center py-4">
                  <p>没有更多视频了</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- 使用 Teleport 将选项框移到 body 下 -->
  <Teleport to="body">
    <OptionsMenu
      v-if="activeOptions !== null"
      :position="optionsPosition"
      :is-read-page="isReadPage"
      @toggleReadStatus="toggleReadStatus"
      @markReadBatch="markReadBatch"
      @downloadVideo="downloadVideo"
      @copyVideoLink="copyVideoLink"
      @dislikeVideo="dislikeVideo"
      @close="closeOptions"
    />
  </Teleport>

  <!-- Error message display -->
  <div v-if="error" class="text-center py-4 text-red-500">
    {{ error }}
  </div>

  <!-- Add this near the end of your template -->
  <Teleport to="body">
    <div v-if="showToast" class="toast-message">
      {{ toastMessage }}
    </div>
  </Teleport>
</template>

<script setup>

</script>

<style src="./LatestVideos.css" scoped></style>

<style scoped>
/* Add this to your component's styles */

</style>