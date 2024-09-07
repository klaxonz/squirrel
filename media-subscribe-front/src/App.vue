<template>
  <div class="app-container bg-gray-100 flex flex-col h-screen">
    <!-- 主要内容区域 -->
    <main class="content-area flex-grow overflow-hidden">
      <keep-alive>
        <router-view v-if="$route.meta.keepAlive"/>
      </keep-alive>
      <router-view v-if="!$route.meta.keepAlive"/>
    </main>

    <!-- 底部导航栏（移动端）/ 侧边导航栏（桌面端） -->
    <nav class="nav-bar">
      <router-link to="/" class="nav-item" :class="{ active: $route.path === '/' }">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
        </svg>
        <span class="nav-text">最新</span>
      </router-link>
      <router-link to="/subscribed" class="nav-item" :class="{ active: $route.path === '/subscribed' }">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
        </svg>
        <span class="nav-text">订阅</span>
      </router-link>
      <router-link to="/download-tasks" class="nav-item" :class="{ active: $route.path === '/download-tasks' }">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        <span class="nav-text">下载</span>
      </router-link>
      <router-link to="/settings" class="nav-item" :class="{ active: $route.path === '/settings' }">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
        <span class="nav-text">设置</span>
      </router-link>
    </nav>
  </div>
</template>

<script setup>
// 如需要的话，这里可以添加组件逻辑
</script>

<style scoped>
.app-container {
  height: 100vh;
  overflow: hidden;
}

.content-area {
  overflow-y: auto;
}

.nav-bar {
  @apply fixed bottom-0 left-0 right-0 md:left-0 md:top-0 md:bottom-0 md:w-16 bg-white flex md:flex-col justify-around items-center shadow-md md:shadow-lg z-50;
}

.nav-item {
  @apply flex flex-col items-center justify-center p-2 w-full text-gray-600 hover:text-blue-500 transition-colors duration-200;
}

.nav-item.active {
  @apply text-blue-500;
}

.nav-item svg {
  @apply mb-1 md:mb-2;
}

.nav-text {
  @apply text-xs md:hidden;
}

@media (min-width: 768px) {
  .content-area {
    margin-left: 4rem; /* 16 * 0.25rem = 4rem, 对应于 md:w-16 */
  }

  .nav-bar {
    height: 100vh;
  }
}

/* 其他样式保持不变 */
</style>