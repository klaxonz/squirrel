<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-background/80 p-4 backdrop-blur-sm">
    <div class="flex max-h-[90vh] w-full max-w-xl flex-col overflow-hidden rounded-lg border border-border/50 bg-background shadow-lg">
      <div class="flex shrink-0 items-start justify-between border-b border-border/50 p-5">
        <div class="min-w-0">
          <h2 class="text-base font-semibold text-foreground">
            {{ isEditing ? '编辑任务' : '新建任务' }}
          </h2>
          <p class="mt-1 text-sm text-muted-foreground">
            配置任务逻辑、调度间隔和运行参数。
          </p>
        </div>
        <Button variant="ghost" size="icon" class="h-9 w-9 rounded-md" @click="$emit('close')">
          <AppIcon name="close" class="h-4 w-4" />
        </Button>
      </div>

      <div class="flex-1 overflow-y-auto custom-scrollbar">
        <form class="space-y-6 p-5" @submit.prevent="handleSubmit">
          <section class="space-y-4">
            <div class="space-y-2">
              <label class="text-xs font-medium text-muted-foreground">任务名称</label>
              <Input
                v-model="formData.name"
                required
                placeholder="输入任务名称"
                class="h-9 rounded-md border-border/50 text-sm shadow-none"
              />
            </div>

            <div class="space-y-2">
              <label class="text-xs font-medium text-muted-foreground">逻辑类</label>
              <Select v-model="formData.task_class" :disabled="isEditing">
                <SelectTrigger class="h-9 rounded-md border-border/50 bg-background text-sm shadow-none">
                  <SelectValue placeholder="选择任务执行逻辑" />
                </SelectTrigger>
                <SelectContent class="rounded-lg border-border/50 bg-background shadow-lg">
                  <SelectGroup v-for="(group, groupName) in groupedTaskClasses" :key="groupName">
                    <SelectLabel class="px-3 py-2 text-xs font-medium text-muted-foreground">{{ groupName }}</SelectLabel>
                    <SelectItem
                      v-for="(taskClass, className) in group"
                      :key="className"
                      :value="className"
                      :text-value="taskClass.name"
                      class="mx-1 rounded-md px-3 py-2 text-sm"
                    >
                      <div class="flex min-w-0 flex-col">
                        <span class="font-medium">{{ taskClass.name }}</span>
                        <span v-if="taskClass.description" class="max-w-[300px] truncate text-xs text-muted-foreground">{{ taskClass.description }}</span>
                      </div>
                    </SelectItem>
                  </SelectGroup>
                </SelectContent>
              </Select>
            </div>

            <div class="space-y-2">
              <label class="text-xs font-medium text-muted-foreground">描述</label>
              <Textarea
                v-model="formData.description"
                placeholder="简要说明任务用途"
                class="min-h-20 rounded-md border-border/50 text-sm shadow-none"
              />
            </div>
          </section>

          <section class="space-y-4 border-t border-border/50 pt-5">
            <div class="grid gap-4 md:grid-cols-3">
            <div class="space-y-2">
              <label class="text-xs font-medium text-muted-foreground">执行间隔</label>
              <Input
                v-model.number="formData.interval"
                type="number"
                min="1"
                class="h-9 rounded-md border-border/50 text-sm tabular-nums shadow-none"
              />
            </div>
            <div class="space-y-2">
              <label class="text-xs font-medium text-muted-foreground">单位</label>
              <Select v-model="formData.unit">
                <SelectTrigger class="h-9 rounded-md border-border/50 bg-background text-sm shadow-none">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent class="rounded-lg border-border/50 bg-background">
                  <SelectItem value="seconds">秒</SelectItem>
                  <SelectItem value="minutes">分钟</SelectItem>
                  <SelectItem value="hours">小时</SelectItem>
                  <SelectItem value="days">天</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div class="space-y-2">
              <label class="text-xs font-medium text-muted-foreground">最大重试</label>
              <Input
                v-model.number="formData.max_retries"
                type="number"
                min="0"
                class="h-9 rounded-md border-border/50 text-sm tabular-nums shadow-none"
              />
            </div>
            </div>

            <div class="grid gap-2">
              <label class="flex h-10 items-center justify-between rounded-md border border-border/50 px-3">
                <span class="text-sm font-medium text-foreground">启用调度</span>
                <Switch v-model:checked="formData.is_active" />
              </label>
              <label class="flex h-10 items-center justify-between rounded-md border border-border/50 px-3">
                <span class="text-sm font-medium text-foreground">立即执行一次</span>
                <Switch v-model:checked="formData.start_immediately" />
              </label>
            </div>
          </section>

          <section class="space-y-2 border-t border-border/50 pt-5">
            <label class="text-xs font-medium text-muted-foreground">任务参数</label>
            <div class="relative">
              <Textarea
                v-model="taskParamsJson"
                rows="5"
                class="font-mono rounded-md border-border/50 bg-muted/30 px-4 py-3 text-xs text-foreground shadow-none"
                placeholder='{ "名称": "内容" }'
              />
              <div v-if="jsonError" class="absolute bottom-3 right-3 inline-flex items-center gap-1.5 rounded-md border border-destructive/20 bg-background px-2 py-1 text-xs font-medium text-destructive">
                <AppIcon name="alert" class="h-3 w-3" />
                格式错误
              </div>
            </div>
          </section>
        </form>
      </div>

      <div class="flex shrink-0 items-center justify-end gap-2 border-t border-border/50 bg-muted/30 p-4">
        <Button variant="outline" class="h-9 rounded-md" @click="$emit('close')">取消</Button>
        <Button class="h-9 rounded-md" :disabled="loading || !!jsonError" @click="handleSubmit">
          <AppIcon v-if="loading" name="loadingSpinner" class="h-4 w-4 animate-spin" />
          {{ isEditing ? '保存' : '创建' }}
        </Button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'
import { Textarea } from '@/shared/ui/textarea'
import { Switch } from '@/shared/ui/switch'
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
  SelectLabel
} from '@/shared/ui/select'
import { Logger } from '@/shared/lib/logger'

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
  } catch {
    jsonError.value = 'ERR_JSON_FORMAT'
  }
})

watch(() => formData.value.task_params, (newValue) => {
  try {
    const currentJson = JSON.stringify(newValue, null, 2)
    if (JSON.stringify(JSON.parse(taskParamsJson.value)) !== JSON.stringify(newValue)) {
      taskParamsJson.value = currentJson
    }
  } catch { /* ponytail: user-typed task params may be invalid JSON; ignore */ }
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
.custom-scrollbar::-webkit-scrollbar { width: 5px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(var(--primary), 0.1); border-radius: 10px; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(var(--primary), 0.2); }

.tabular-nums {
  font-variant-numeric: tabular-nums;
}
</style>
