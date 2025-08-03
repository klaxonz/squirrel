<script setup>
import { onMounted, ref } from 'vue'
import { useSystemConfig } from '../composables/useSystemConfig'
import { useToast } from 'vue-toastification'

const { config, loading, loadSystemConfig, updateSystemConfig } = useSystemConfig()
const saving = ref(false)
const toast = useToast()

onMounted(async () => {
  await loadSystemConfig()
})

const onToggle = async (key, val) => {
  saving.value = true
  try {
    await updateSystemConfig({ [key]: val })
    toast.success('已应用')
  } catch (e) {
    toast.error('操作失败')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="settings-container bg-[#0f0f0f] text-white min-h-screen p-4 md:p-8">
    <h1 class="text-2xl font-bold mb-6">系统配置</h1>

    <div class="settings-section mb-8">
      <div class="setting-item flex justify-between items-center py-3 border-b border-gray-700">
        <div>
          <h3 class="font-medium">启用调度器（Scheduler）</h3>
          <p class="text-sm text-gray-400">按计划任务周期性执行订阅同步、重试等任务</p>
        </div>
        <label class="switch">
          <input
            type="checkbox"
            :checked="(config && config.enable_scheduler === 'true') || config?.enable_scheduler === true"
            :disabled="loading || saving"
            @change="onToggle('enable_scheduler', $event.target.checked)"
          >
          <span class="slider"></span>
        </label>
      </div>

      <div class="setting-item flex justify-between items-center py-3 border-b border-gray-700">
        <div>
          <h3 class="font-medium">启用 Worker（队列消费）</h3>
          <p class="text-sm text-gray-400">开启后启动 Dramatiq Worker 进行队列消费</p>
        </div>
        <label class="switch">
          <input
            type="checkbox"
            :checked="(config && config.enable_worker === 'true') || config?.enable_worker === true"
            :disabled="loading || saving"
            @change="onToggle('enable_worker', $event.target.checked)"
          >
          <span class="slider"></span>
        </label>
      </div>
    </div>
  </div>
</template>

<style scoped>
.settings-container {
  max-width: 800px;
  margin: 0 auto;
}
.setting-item {
  margin-bottom: 1.5rem;
}
.switch {
  position: relative;
  display: inline-block;
  width: 48px;
  height: 24px;
}
.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}
.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #4a4a4a;
  transition: .4s;
  border-radius: 24px;
}
.slider:before {
  position: absolute;
  content: "";
  height: 20px;
  width: 20px;
  left: 2px;
  bottom: 2px;
  background-color: white;
  transition: .4s;
  border-radius: 50%;
}
input:checked + .slider {
  background-color: #ef4444;
}
input:checked + .slider:before {
  transform: translateX(24px);
}
</style>