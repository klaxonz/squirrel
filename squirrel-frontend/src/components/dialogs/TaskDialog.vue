<template>
  <div class="fixed inset-0 bg-overlay-strong backdrop-blur-sm flex items-center justify-center z-50 p-4">
    <div class="bg-card border border-border rounded-[1.5rem] w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col shadow-2xl">
      <div class="flex items-center justify-between px-6 py-4 border-b border-border">
        <h2 class="text-xl font-bold text-foreground">
          {{ isEditing ? '编辑任务' : '创建任务' }}
        </h2>
        <button
          @click="$emit('close')"
          class="text-foreground/50 hover:text-foreground transition-colors p-1 hover:bg-accent rounded-lg"
        >
          <XMarkIcon class="w-5 h-5" />
        </button>
      </div>

      <div class="flex-1 overflow-y-auto px-6 py-5">
        <form @submit.prevent="handleSubmit" class="space-y-5">
          <!-- 基本信息 -->
          <div class="space-y-4">
            <h3 class="text-sm font-semibold text-foreground/50 uppercase tracking-wider">基本信息</h3>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-foreground mb-2">任务名称 <span class="text-destructive">*</span></label>
                <input
                  v-model="formData.name"
                  type="text"
                  required
                  class="w-full px-4 py-2.5 bg-card border border-border rounded-lg text-foreground text-sm placeholder:text-muted-foreground focus:outline-none focus:border-destructive focus:ring-1 focus:ring-destructive transition-colors"
                  placeholder="输入任务名称"
                >
              </div>

              <div>
                <label class="block text-sm font-medium text-foreground mb-2">任务类型</label>
                <select
                  v-model="formData.task_type"
                  :disabled="isEditing"
                  class="w-full px-4 py-2.5 bg-card border border-border rounded-lg text-foreground text-sm focus:outline-none focus:border-destructive focus:ring-1 focus:ring-destructive transition-colors"
                >
                  <option value="user">用户任务</option>
                  <option value="system">系统任务</option>
                  <option value="plugin">插件任务</option>
                </select>
              </div>
            </div>

            <div>
              <label class="block text-sm font-medium text-foreground mb-2">任务描述</label>
              <textarea
                v-model="formData.description"
                rows="3"
                class="w-full px-4 py-2.5 bg-card border border-border rounded-lg text-foreground text-sm placeholder:text-muted-foreground focus:outline-none focus:border-destructive focus:ring-1 focus:ring-destructive transition-colors resize-none"
                placeholder="输入任务描述（可选）"
              ></textarea>
            </div>

            <div>
              <label class="block text-sm font-medium text-foreground mb-2">任务类 <span class="text-destructive">*</span></label>
              <select
                v-model="formData.task_class"
                required
                :disabled="isEditing"
                class="w-full px-4 py-2.5 bg-card border border-border rounded-lg text-foreground text-sm focus:outline-none focus:border-destructive focus:ring-1 focus:ring-destructive transition-colors"
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
          </div>

          <!-- 执行配置 -->
          <div class="space-y-4">
            <h3 class="text-sm font-semibold text-foreground/50 uppercase tracking-wider">执行配置</h3>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label class="block text-sm font-medium text-foreground mb-2">执行间隔 <span class="text-destructive">*</span></label>
                <input
                  v-model.number="formData.interval"
                  type="number"
                  min="1"
                  required
                  class="w-full px-4 py-2.5 bg-card border border-border rounded-lg text-foreground text-sm focus:outline-none focus:border-destructive focus:ring-1 focus:ring-destructive transition-colors"
                >
              </div>

              <div>
                <label class="block text-sm font-medium text-foreground mb-2">时间单位</label>
                <select
                  v-model="formData.unit"
                  class="w-full px-4 py-2.5 bg-card border border-border rounded-lg text-foreground text-sm focus:outline-none focus:border-destructive focus:ring-1 focus:ring-destructive transition-colors"
                >
                  <option value="seconds">秒</option>
                  <option value="minutes">分钟</option>
                  <option value="hours">小时</option>
                  <option value="days">天</option>
                </select>
              </div>

              <div>
                <label class="block text-sm font-medium text-foreground mb-2">最大重试次数</label>
                <input
                  v-model.number="formData.max_retries"
                  type="number"
                  min="0"
                  max="10"
                  class="w-full px-4 py-2.5 bg-card border border-border rounded-lg text-foreground text-sm focus:outline-none focus:border-destructive focus:ring-1 focus:ring-destructive transition-colors"
                >
              </div>
            </div>
          </div>

          <!-- 选项 -->
          <div class="space-y-4">
            <h3 class="text-sm font-semibold text-foreground/50 uppercase tracking-wider">选项</h3>
            <div class="flex items-center gap-6">
              <label class="flex items-center gap-2 cursor-pointer">
                <input
                  v-model="formData.start_immediately"
                  type="checkbox"
                  class="w-4 h-4 rounded border-border bg-card text-destructive focus:ring-2 focus:ring-destructive focus:ring-offset-0"
                >
                <span class="text-sm text-foreground">立即启动</span>
              </label>

              <label class="flex items-center gap-2 cursor-pointer">
                <input
                  v-model="formData.is_active"
                  type="checkbox"
                  class="w-4 h-4 rounded border-border bg-card text-destructive focus:ring-2 focus:ring-destructive focus:ring-offset-0"
                >
                <span class="text-sm text-foreground">激活状态</span>
              </label>
            </div>
          </div>

          <!-- 任务参数 -->
          <div class="space-y-4">
            <h3 class="text-sm font-semibold text-foreground/50 uppercase tracking-wider">高级配置</h3>
            <div>
              <label class="block text-sm font-medium text-foreground mb-2">任务参数 (JSON)</label>
              <textarea
                v-model="taskParamsJson"
                rows="5"
                class="w-full px-4 py-2.5 bg-card border border-border rounded-lg text-foreground text-sm placeholder:text-muted-foreground focus:outline-none focus:border-destructive focus:ring-1 focus:ring-destructive transition-colors font-mono resize-none"
                placeholder='{"key": "value"}'
              ></textarea>
              <div v-if="jsonError" class="flex items-center gap-2 text-destructive text-xs mt-2">
                <ExclamationTriangleIcon class="w-4 h-4" />
                <span>{{ jsonError }}</span>
              </div>
            </div>
          </div>
        </form>
      </div>

      <!-- 操作按钮 -->
      <div class="flex items-center justify-end gap-3 px-6 py-4 border-t border-border bg-card">
        <button
          type="button"
          @click="$emit('close')"
          class="px-5 py-2.5 bg-secondary hover:bg-accent text-foreground text-sm font-medium rounded-full transition-colors"
        >
          取消
        </button>
        <button
          type="submit"
          @click="handleSubmit"
          :disabled="loading || !!jsonError"
          class="px-5 py-2.5 bg-destructive hover:bg-destructive/90 disabled:opacity-50 disabled:cursor-not-allowed text-destructive-foreground text-sm font-medium rounded-full transition-colors"
        >
          {{ loading ? '保存中...' : (isEditing ? '更新任务' : '创建任务') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { XMarkIcon, ExclamationTriangleIcon } from '@heroicons/vue/24/outline'
import { Logger } from '@/utils/logger'

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
    Logger.error('Failed to submit form', error)
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
