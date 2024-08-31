<template>
  <div class="app-container">
    <!-- 主要内容区域 -->
    <main class="content-area">
      <router-view />
    </main>

    <!-- 底部导航栏 -->
    <nav class="nav-bar">
      <router-link to="/" class="nav-item">
        <i class="fas fa-home"></i>
        <span>最新视频</span>
      </router-link>
      <router-link to="/subscribed" class="nav-item">
        <i class="fas fa-star"></i>
        <span>订阅</span>
      </router-link>
      <router-link to="/settings" class="nav-item">
        <i class="fas fa-cog"></i>
        <span>设置</span>
      </router-link>
    </nav>
  </div>
</template>

<script setup>
// 如果需要的话，这里可以添加组件逻辑
</script>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.content-area {
  flex: 1;
  overflow-y: auto;
  padding-bottom: 60px; /* 为底部导航栏留出空间 */
}
.nav-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  justify-content: space-around;
  background-color: #fff;
  box-shadow: 0 -2px 4px rgba(0, 0, 0, 0.1);
  padding: 10px 0;
}

.nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-decoration: none;
  color: #333;
}

.nav-item i {
  font-size: 20px;
  margin-bottom: 5px;
}

.nav-item span {
  font-size: 12px;
}
</style>