<template>
  <div class="message-trace-view bg-[#0f0f0f] text-white min-h-screen">
    <div class="px-4 pt-2 pb-3">
      <h1 class="text-xl font-semibold mb-1">消息追踪</h1>
      <p class="text-xs text-gray-400">追踪消息队列中的消息处理状态</p>
    </div>
    
    <MessageTraceViewer />
  </div>
</template>

<script setup>
import MessageTraceViewer from '../components/MessageTraceViewer.vue'
</script>

<style scoped>
</style>

