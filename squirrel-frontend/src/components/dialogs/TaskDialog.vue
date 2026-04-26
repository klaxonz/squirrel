<template>
  <div class="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-in fade-in duration-200">
    <div class="bg-white border border-slate-200 rounded-xl w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col shadow-2xl animate-in zoom-in-95 duration-200">
      <!-- Modal Header -->
      <div class="px-8 pt-8 pb-6 flex items-start justify-between border-b border-slate-50">
        <div class="space-y-1">
          <h2 class="text-lg font-semibold text-slate-900">
            {{ isEditing ? '编辑任务' : '新建任务' }}
          </h2>
          <p class="text-xs text-slate-500">
            配置自动化任务的执行逻辑与调度参数
          </p>
        </div>
        <Button
          variant="ghost"
          size="icon"
          @click="$emit('close')"
          class="h-8 w-8 rounded-md hover:bg-slate-100 transition-colors"
        >
          <X class="w-4 h-4 text-slate-400" />
        </Button>
      </div>

      <!-- Modal Body -->
      <div class="flex-1 overflow-y-auto px-8 py-6 custom-scrollbar">
        <form @submit.prevent="handleSubmit" class="space-y-8">
          <!-- Section: Basic -->
          <div class="space-y-5">
            <div class="space-y-2">
              <label class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">任务名称</label>
              <Input
                v-model="formData.name"
                required
                placeholder="输入任务名称..."
                class="h-10 bg-white border-slate-200 rounded-lg text-sm focus-visible:ring-slate-200 shadow-none"
              />
            </div>

            <div class="space-y-2">
              <label class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">逻辑类</label>
              <Select v-model="formData.task_class" :disabled="isEditing">
                <SelectTrigger class="h-10 bg-white border-slate-200 rounded-lg text-sm shadow-none">
                  <SelectValue placeholder="选择任务执行逻辑" />
                </SelectTrigger>
                <SelectContent class="border-slate-200 bg-white rounded-lg shadow-xl">
                  <template v-for="(group, groupName) in groupedTaskClasses" :key="groupName">
                    <SelectLabel class="text-[10px] font-bold text-slate-400 px-3 py-2 mt-1">{{ groupName }}</SelectLabel>
                    <SelectItem
                      v-for="(taskClass, className) in group"
                      :key="className"
                      :value="className"
                      class="py-2 px-3 focus:bg-slate-50 cursor-pointer rounded-md mx-1 text-sm text-slate-700"
                    >
                      <div class="flex flex-col">
                        <span class="font-medium">{{ taskClass.name }}</span>
                        <span class="text-[11px] text-slate-400 truncate max-w-[300px]">{{ taskClass.description || '暂无描述' }}</span>
                      </div>
                    </SelectItem>
                  </template>
                </SelectContent>
              </Select>
            </div>

            <div class="space-y-2">
              <label class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">描述</label>
              <Textarea
                v-model="formData.description"
                placeholder="简要说明任务用途..."
                class="min-h-[80px] bg-white border-slate-200 rounded-lg text-sm focus-visible:ring-slate-200 shadow-none py-3 px-4"
              />
            </div>
          </div>

          <!-- Section: Strategy -->
          <div class="grid grid-cols-3 gap-4 p-5 bg-slate-50 rounded-xl border border-slate-100">
            <div class="space-y-2">
              <label class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">执行间隔</label>
              <Input
                v-model.number="formData.interval"
                type="number"
                min="1"
                class="h-9 bg-white border-slate-200 rounded-md text-sm font-bold tabular-nums shadow-none"
              />
            </div>
            <div class="space-y-2">
              <label class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">单位</label>
              <Select v-model="formData.unit">
                <SelectTrigger class="h-9 bg-white border-slate-200 rounded-md text-sm shadow-none">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent class="rounded-lg">
                  <SelectItem value="seconds" class="text-xs">秒</SelectItem>
                  <SelectItem value="minutes" class="text-xs">分钟</SelectItem>
                  <SelectItem value="hours" class="text-xs">小时</SelectItem>
                  <SelectItem value="days" class="text-xs">天</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div class="space-y-2">
              <label class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">最大重试</label>
              <Input
                v-model.number="formData.max_retries"
                type="number"
                min="0"
                class="h-9 bg-white border-slate-200 rounded-md text-sm font-bold tabular-nums shadow-none"
              />
            </div>
          </div>

          <div class="flex items-center gap-8 px-2">
            <div class="flex items-center gap-3">
              <Switch v-model:checked="formData.is_active" />
              <span class="text-xs font-semibold text-slate-700">启用调度</span>
            </div>
            <div class="flex items-center gap-3">
              <Switch v-model:checked="formData.start_immediately" />
              <span class="text-xs font-semibold text-slate-700">立即执行一次</span>
            </div>
          </div>

          <!-- Section: Params -->
          <div class="space-y-2">
            <label class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">任务参数 (JSON)</label>
            <div class="relative">
              <Textarea
                v-model="taskParamsJson"
                rows="4"
                class="font-mono text-xs bg-slate-900 text-slate-300 rounded-lg border-none focus-visible:ring-2 focus-visible:ring-slate-200 py-4 px-5"
                placeholder='{ "key": "value" }'
              />
              <div v-if="jsonError" class="absolute bottom-3 right-3 flex items-center gap-1.5 px-2 py-1 rounded bg-rose-500/10 border border-rose-500/20 text-rose-600 text-[10px] font-bold">
                <AlertTriangle class="w-3 h-3" />
                格式错误
              </div>
            </div>
          </div>
        </form>
      </div>

      <!-- Modal Footer -->
      <div class="px-8 py-5 bg-slate-50 border-t border-slate-100 flex items-center justify-end gap-3">
        <Button
          variant="ghost"
          @click="$emit('close')"
          class="h-9 px-4 text-sm font-medium text-slate-500 hover:text-slate-900 transition-colors"
        >
          取消
        </Button>
        <Button
          @click="handleSubmit"
          :disabled="loading || !!jsonError"
          class="h-9 px-6 text-sm font-medium bg-slate-900 text-white hover:bg-slate-800 transition-colors shadow-sm"
        >
          <Loader2 v-if="loading" class="mr-2 h-4 w-4 animate-spin" />
          {{ isEditing ? '保存修改' : '创建任务' }}
        </Button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { X, AlertTriangle, Loader2 } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import { 
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue, SelectLabel 
} from '@/components/ui/select'
import { Logger } from '@/utils/logger'

const props = defineProps({
  task: { type: Object, default: null },
  taskClasses: { type: Object, default: () => ({}) }
})

const emit = defineEmits(['close', 'save'])

const isEditing = computed(() => !!props.task)
const loading = ref(false)
const jsonError = ref('')

const formData = ref({
  name: '',
  description: '',
  task_class: '',
  interval: 60,
  unit: 'seconds',
  start_immediately: true,
  max_retries: 3,
  task_params: {},
  is_active: true
})

const taskParamsJson = ref('{}')

const groupedTaskClasses = computed(() => {
  const groups = {}
  Object.entries(props.taskClasses).forEach(([className, taskClass]) => {
    const module = taskClass.module || '默认'
    if (!groups[module]) groups[module] = {}
    groups[module][className] = taskClass
  })
  return groups
})

watch(taskParamsJson, (newValue) => {
  try {
    const parsed = JSON.parse(newValue)
    if (typeof parsed !== 'object' || parsed === null) throw new Error()
    formData.value.task_params = parsed
    jsonError.value = ''
  } catch (e) {
    jsonError.value = 'ERR_JSON_FORMAT'
  }
})

watch(() => formData.value.task_params, (newValue) => {
  try {
    const currentJson = JSON.stringify(newValue, null, 2)
    if (JSON.stringify(JSON.parse(taskParamsJson.value)) !== JSON.stringify(newValue)) {
      taskParamsJson.value = currentJson
    }
  } catch (e) {}
}, { deep: true })

const initializeForm = () => {
  if (props.task) {
    Object.assign(formData.value, {
      name: props.task.name || '',
      description: props.task.description || '',
      task_class: props.task.task_class || '',
      interval: props.task.interval || 60,
      unit: props.task.unit || 'seconds',
      start_immediately: props.task.start_immediately !== false,
      max_retries: props.task.max_retries || 3,
      task_params: props.task.task_params || {},
      is_active: props.task.is_active !== false
    })
    taskParamsJson.value = JSON.stringify(formData.value.task_params, null, 2)
  }
}

const handleSubmit = async () => {
  if (jsonError.value) return
  loading.value = true
  try {
    emit('save', { ...formData.value })
  } catch (error) {
    Logger.error('TaskDialog: Submission failed', error)
  } finally {
    loading.value = false
  }
}

onMounted(initializeForm)
watch(() => props.task, initializeForm, { deep: true })
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #e2e8f0;
  border-radius: 10px;
}
</style>
