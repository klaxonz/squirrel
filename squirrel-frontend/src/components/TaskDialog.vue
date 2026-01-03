<template>
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
    <div class="bg-[#1f1f1f] rounded-xl p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
      <div class="flex items-center justify-between mb-6">
        <h2 class="text-xl font-semibold text-white">
          {{ isEditing ? '编辑任务' : '创建任务' }}
        </h2>
        <button
          @click="$emit('close')"
          class="text-gray-400 hover:text-white transition-colors"
        >
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
          </svg>
        </button>
      </div>

      <form @submit.prevent="handleSubmit" class="space-y-4">
        <!-- 基本信息 -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-300 mb-2">任务名称</label>
            <input
              v-model="formData.name"
              type="text"
              required
              class="w-full px-3 py-2 bg-[#2f2f2f] border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-blue-500"
              placeholder="输入任务名称"
            >
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-300 mb-2">任务类型</label>
            <select
              v-model="formData.task_type"
              class="w-full px-3 py-2 bg-[#2f2f2f] border border-gray-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
            >
              <option value="user">用户任务</option>
              <option value="system">系统任务</option>
              <option value="plugin">插件任务</option>
            </select>
          </div>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-300 mb-2">任务描述</label>
          <textarea
            v-model="formData.description"
            rows="3"
            class="w-full px-3 py-2 bg-[#2f2f2f] border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-blue-500 resize-none"
            placeholder="输入任务描述（可选）"
          ></textarea>
        </div>

        <!-- 任务类选择 -->
        <div>
          <label class="block text-sm font-medium text-gray-300 mb-2">任务类</label>
          <select
            v-model="formData.task_class"
            required
            class="w-full px-3 py-2 bg-[#2f2f2f] border border-gray-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
          >
            <option value="">请选择任务类</option>
            <optgroup v-for="(group, groupName) in groupedTaskClasses" :key="groupName" :label="groupName">
              <option
                v-for="(taskClass, className) in group"
                :key="className"
                :value="className"
              >
                {{ taskClass.name }} - {{ taskClass.description || '无描述' }}
              </option>
            </optgroup>
          </select>
        </div>

        <!-- 执行配置 -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-300 mb-2">执行间隔</label>
            <input
              v-model.number="formData.interval"
              type="number"
              min="1"
              required
              class="w-full px-3 py-2 bg-[#2f2f2f] border border-gray-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
            >
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-300 mb-2">时间单位</label>
            <select
              v-model="formData.unit"
              class="w-full px-3 py-2 bg-[#2f2f2f] border border-gray-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
            >
              <option value="seconds">秒</option>
              <option value="minutes">分钟</option>
              <option value="hours">小时</option>
              <option value="days">天</option>
            </select>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-300 mb-2">最大重试次数</label>
            <input
              v-model.number="formData.max_retries"
              type="number"
              min="0"
              max="10"
              class="w-full px-3 py-2 bg-[#2f2f2f] border border-gray-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
            >
          </div>
        </div>

        <!-- 选项 -->
        <div class="flex items-center space-x-6">
          <label class="flex items-center">
            <input
              v-model="formData.start_immediately"
              type="checkbox"
              class="mr-2"
            >
            <span class="text-sm text-gray-300">立即启动</span>
          </label>

          <label class="flex items-center">
            <input
              v-model="formData.is_active"
              type="checkbox"
              class="mr-2"
            >
            <span class="text-sm text-gray-300">激活状态</span>
          </label>
        </div>

        <!-- 任务参数 -->
        <div>
          <label class="block text-sm font-medium text-gray-300 mb-2">任务参数 (JSON)</label>
          <textarea
            v-model="taskParamsJson"
            rows="4"
            class="w-full px-3 py-2 bg-[#2f2f2f] border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-blue-500 font-mono text-sm"
            placeholder='{"key": "value"}'
          ></textarea>
          <div v-if="jsonError" class="text-red-400 text-sm mt-1">{{ jsonError }}</div>
        </div>

        <!-- 操作按钮 -->
        <div class="flex justify-end space-x-3 pt-4">
          <button
            type="button"
            @click="$emit('close')"
            class="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg transition-colors"
          >
            取消
          </button>
          <button
            type="submit"
            :disabled="loading || !!jsonError"
            class="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
          >
            {{ loading ? '保存中...' : (isEditing ? '更新' : '创建') }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'

const props = defineProps({
  task: {
    type: Object,
    default: null
  },
  taskClasses: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['close', 'save'])

const isEditing = computed(() => !!props.task)
const loading = ref(false)
const jsonError = ref('')

// 表单数据
const formData = ref({
  name: '',
  task_type: 'user',
  description: '',
  task_class: '',
  interval: 60,
  unit: 'seconds',
  start_immediately: true,
  max_retries: 3,
  task_params: {},
  is_active: true
})

// 任务参数JSON
const taskParamsJson = ref('{}')

// 计算属性：分组的任务类
const groupedTaskClasses = computed(() => {
  const groups = {}

  Object.entries(props.taskClasses).forEach(([className, taskClass]) => {
    const module = taskClass.module || 'unknown'
    if (!groups[module]) {
      groups[module] = {}
    }
    groups[module][className] = taskClass
  })

  return groups
})

// 监听任务参数JSON变化，验证JSON格式
watch(taskParamsJson, (newValue) => {
  try {
    formData.value.task_params = JSON.parse(newValue)
    jsonError.value = ''
  } catch (e) {
    jsonError.value = 'JSON格式错误'
  }
})

// 监听任务参数对象变化，更新JSON字符串
watch(() => formData.value.task_params, (newValue) => {
  try {
    taskParamsJson.value = JSON.stringify(newValue, null, 2)
  } catch (e) {
    // 忽略错误
  }
}, { deep: true })

// 初始化表单数据
const initializeForm = () => {
  if (props.task) {
    // 编辑模式
    Object.assign(formData.value, {
      name: props.task.name || '',
      task_type: props.task.task_type || 'user',
      description: props.task.description || '',
      task_class: props.task.task_class || '',
      interval: props.task.interval || 60,
      unit: props.task.unit || 'seconds',
      start_immediately: props.task.start_immediately !== false,
      max_retries: props.task.max_retries || 3,
      task_params: props.task.task_params || {},
      is_active: props.task.is_active !== false
    })
  } else {
    // 创建模式，重置表单
    Object.assign(formData.value, {
      name: '',
      task_type: 'user',
      description: '',
      task_class: '',
      interval: 60,
      unit: 'seconds',
      start_immediately: true,
      max_retries: 3,
      task_params: {},
      is_active: true
    })
  }
}

// 提交表单
const handleSubmit = async () => {
  if (jsonError.value) {
    return
  }

  loading.value = true
  try {
    const submitData = {
      ...formData.value,
      task_params: formData.value.task_params
    }

    emit('save', submitData)
  } catch (error) {
    console.error('提交表单失败:', error)
  } finally {
    loading.value = false
  }
}

// 初始化
onMounted(() => {
  initializeForm()
})

// 监听任务变化
watch(() => props.task, () => {
  initializeForm()
}, { deep: true })
</script>

<style scoped>
/* 自定义样式 */
</style>
