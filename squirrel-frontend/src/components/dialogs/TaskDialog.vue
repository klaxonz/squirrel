<template>
  <div class="fixed inset-0 bg-background/60 backdrop-blur-xl flex items-center justify-center z-50 p-6 animate-in fade-in duration-300">
    <div class="bg-card border border-border/40 rounded-[2rem] w-full max-w-xl max-h-[85vh] overflow-hidden flex flex-col shadow-2xl shadow-foreground/5 animate-in zoom-in-95 duration-300">
      <!-- Modal Header -->
      <div class="px-10 pt-8 pb-6 flex items-start justify-between">
        <div class="space-y-1.5">
          <h2 class="text-lg font-bold tracking-tight text-foreground/90">
            {{ isEditing ? '编辑任务配置' : '创建新任务' }}
          </h2>
          <p class="text-[10px] font-bold text-muted-foreground/30 uppercase tracking-[0.2em]">
            {{ isEditing ? '任务 ID: ' + props.task.id : '部署清单' }}
          </p>
        </div>
        <Button
          variant="ghost"
          size="sm"
          @click="$emit('close')"
          class="h-8 w-8 p-0 text-muted-foreground/20 hover:text-foreground hover:bg-muted/50 transition-all rounded-full"
        >
          <X class="w-4 h-4" />
        </Button>
      </div>

      <!-- Modal Body -->
      <div class="flex-1 overflow-y-auto px-10 py-2 custom-scrollbar">
        <form @submit.prevent="handleSubmit" class="space-y-10">
          <!-- Section: Basic -->
          <div class="space-y-6">
            <div class="flex items-center gap-3">
              <span class="text-[9px] font-bold uppercase tracking-[0.3em] text-primary/40">01 任务定义</span>
              <div class="flex-1 h-px bg-border/20"></div>
            </div>
            
            <div class="grid grid-cols-1 gap-5">
              <div class="space-y-2">
                <label class="text-[9px] font-bold uppercase tracking-widest text-muted-foreground/30 ml-1">任务名称</label>
                <Input
                  v-model="formData.name"
                  required
                  placeholder="输入任务名称"
                  class="bg-muted/5 border-border/20 h-9 text-[11px] font-semibold rounded-lg focus:bg-muted/10 transition-all placeholder:text-muted-foreground/20"
                />
              </div>

              <div class="grid grid-cols-2 gap-4">
                <div class="space-y-2">
                  <label class="text-[9px] font-bold uppercase tracking-widest text-muted-foreground/30 ml-1">逻辑类</label>
                  <Select v-model="formData.task_class" :disabled="isEditing">
                    <SelectTrigger class="bg-muted/5 border-border/20 h-9 rounded-lg text-[10px] font-bold uppercase tracking-widest">
                      <SelectValue placeholder="选择逻辑类" />
                    </SelectTrigger>
                    <SelectContent class="max-h-[240px] border-border/40 bg-card/95 backdrop-blur-xl rounded-xl">
                      <template v-for="(group, groupName) in groupedTaskClasses" :key="groupName">
                        <SelectLabel class="text-[8px] font-bold uppercase tracking-[0.2em] text-primary/30 px-3 py-2">{{ groupName }}</SelectLabel>
                        <SelectItem
                          v-for="(taskClass, className) in group"
                          :key="className"
                          :value="className"
                          class="py-2.5 px-3 focus:bg-primary/5 cursor-pointer rounded-lg mx-1"
                        >
                          <div class="flex flex-col gap-0.5">
                            <span class="text-[11px] font-bold text-foreground/70 tracking-tight">{{ taskClass.name }}</span>
                            <span class="text-[9px] font-medium text-muted-foreground/30 truncate max-w-[180px] uppercase tracking-tighter">{{ taskClass.description || '暂无描述' }}</span>
                          </div>
                        </SelectItem>
                      </template>
                    </SelectContent>
                  </Select>
                </div>

                <div class="space-y-2">
                  <label class="text-[9px] font-bold uppercase tracking-widest text-muted-foreground/30 ml-1">归属类型</label>
                  <Select v-model="formData.task_type" :disabled="isEditing">
                    <SelectTrigger class="bg-muted/5 border-border/20 h-9 rounded-lg text-[10px] font-bold uppercase tracking-widest">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent class="border-border/40 bg-card/95 backdrop-blur-xl rounded-xl">
                      <SelectItem value="user" class="text-[10px] font-bold uppercase tracking-widest rounded-lg mx-1">用户</SelectItem>
                      <SelectItem value="system" class="text-[10px] font-bold uppercase tracking-widest rounded-lg mx-1">核心</SelectItem>
                      <SelectItem value="plugin" class="text-[10px] font-bold uppercase tracking-widest rounded-lg mx-1">插件</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div class="space-y-2">
                <label class="text-[9px] font-bold uppercase tracking-widest text-muted-foreground/30 ml-1">描述</label>
                <Textarea
                  v-model="formData.description"
                  placeholder="任务详细规格说明"
                  class="bg-muted/5 border-border/20 focus:bg-muted/10 min-h-[60px] text-[11px] font-medium rounded-lg transition-all resize-none py-3 placeholder:text-muted-foreground/20"
                />
              </div>
            </div>
          </div>

          <!-- Section: Execution -->
          <div class="space-y-6">
            <div class="flex items-center gap-3">
              <span class="text-[9px] font-bold uppercase tracking-[0.3em] text-blue-500/30">02 执行策略</span>
              <div class="flex-1 h-px bg-border/20"></div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div class="space-y-2">
                <label class="text-[9px] font-bold uppercase tracking-widest text-muted-foreground/30 ml-1">执行频率</label>
                <Input
                  v-model.number="formData.interval"
                  type="number"
                  min="1"
                  class="bg-muted/5 border-border/20 h-9 rounded-lg text-[11px] font-bold tabular-nums focus:bg-muted/10"
                />
              </div>

              <div class="space-y-2">
                <label class="text-[9px] font-bold uppercase tracking-widest text-muted-foreground/30 ml-1">单位</label>
                <Select v-model="formData.unit">
                  <SelectTrigger class="bg-muted/5 border-border/20 h-9 rounded-lg text-[10px] font-bold uppercase tracking-widest">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent class="border-border/40 bg-card/95 backdrop-blur-xl rounded-xl">
                    <SelectItem value="seconds" class="text-[10px] font-bold rounded-lg mx-1">秒</SelectItem>
                    <SelectItem value="minutes" class="text-[10px] font-bold rounded-lg mx-1">分钟</SelectItem>
                    <SelectItem value="hours" class="text-[10px] font-bold rounded-lg mx-1">小时</SelectItem>
                    <SelectItem value="days" class="text-[10px] font-bold rounded-lg mx-1">天</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div class="space-y-2">
                <label class="text-[9px] font-bold uppercase tracking-widest text-muted-foreground/30 ml-1">重试限制</label>
                <Input
                  v-model.number="formData.max_retries"
                  type="number"
                  min="0"
                  max="10"
                  class="bg-muted/5 border-border/20 h-9 rounded-lg text-[11px] font-bold tabular-nums focus:bg-muted/10"
                />
              </div>
            </div>

            <div class="flex items-center gap-10 px-4 py-4 rounded-xl bg-muted/5 border border-border/20">
              <div class="flex items-center gap-3">
                <Switch v-model:checked="formData.is_active" />
                <span class="text-[9px] font-bold uppercase tracking-widest text-foreground/40">启用调度</span>
              </div>
              <div class="flex items-center gap-3">
                <Switch v-model:checked="formData.start_immediately" />
                <span class="text-[9px] font-bold uppercase tracking-widest text-foreground/40">立即执行</span>
              </div>
            </div>
          </div>

          <!-- Section: Parameters -->
          <div class="space-y-6">
            <div class="flex items-center gap-3">
              <span class="text-[9px] font-bold uppercase tracking-[0.3em] text-amber-500/30">03 任务参数</span>
              <div class="flex-1 h-px bg-border/20"></div>
            </div>
            <div class="relative group">
              <Textarea
                v-model="taskParamsJson"
                rows="4"
                class="bg-muted/5 border-border/20 focus:bg-muted/10 font-mono text-[10px] leading-relaxed rounded-xl transition-all resize-none py-4 px-5"
                placeholder='{ "JSON": "载荷" }'
              />
              <div v-if="jsonError" class="absolute top-4 right-4 flex items-center gap-1.5 px-2 py-1 rounded-md bg-rose-500/10 border border-rose-500/20 text-rose-500 text-[8px] font-bold tracking-[0.1em]">
                <AlertTriangle class="w-2.5 h-2.5" />
                <span>{{ jsonError }}</span>
              </div>
            </div>
          </div>
        </form>
      </div>

      <!-- Modal Footer -->
      <div class="px-10 py-8 flex items-center justify-end gap-2">
        <Button
          variant="ghost"
          size="sm"
          @click="$emit('close')"
          class="h-8 px-5 text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/30 hover:text-foreground transition-all"
        >
          放弃更改
        </Button>
        <Button
          @click="handleSubmit"
          :disabled="loading || !!jsonError"
          variant="ghost"
          size="sm"
          class="h-8 px-6 text-[10px] font-bold uppercase tracking-[0.2em] border border-border/40 bg-muted/20 text-foreground/60 hover:text-foreground hover:bg-muted/40 transition-all disabled:opacity-20"
        >
          <Loader2 v-if="loading" class="mr-2 h-3 w-3 animate-spin" />
          {{ isEditing ? '更新配置' : '部署任务' }}
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

const taskParamsJson = ref('{}')

const groupedTaskClasses = computed(() => {
  const groups = {}
  Object.entries(props.taskClasses).forEach(([className, taskClass]) => {
    const module = taskClass.module || 'DEFAULT'
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
  background: hsl(var(--border) / 0.1);
  border-radius: 10px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: hsl(var(--border) / 0.2);
}

/* Typography refinement */
.tabular-nums {
  font-variant-numeric: tabular-nums;
}
</style>
