<template>
  <div v-if="show" class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center">
    <div class="bg-card border border-border rounded-lg w-full max-w-lg mx-4">
      <!-- 标题栏 -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-border">
        <h3 class="text-lg font-medium">添加订阅</h3>
        <Button variant="ghost" size="icon" class="rounded-full" title="关闭" aria-label="关闭" @click="$emit('close')">
          <XMarkIcon class="h-6 w-6" />
        </Button>
      </div>

      <!-- 表单内容 -->
      <div class="p-6">
        <div class="space-y-4">
          <!-- URL输入 -->
          <div>
            <label class="block text-sm font-medium text-muted-foreground mb-1">订阅地址</label>
            <input 
              v-model="channelUrl"
              type="url"
              placeholder="支持频道地址或播放列表地址"
              class="w-full px-3 py-2 bg-muted rounded border border-border focus:border-ring focus:ring-2 focus:ring-ring focus:outline-none text-foreground text-sm"
              :disabled="loading"
            >
            <p class="mt-2 text-xs text-muted-foreground">
              支持：YouTube频道/播放列表、Bilibili用户空间/合集/收藏夹
            </p>
          </div>

          <!-- 错误提示 -->
          <p v-if="error" class="text-destructive text-sm">{{ error }}</p>
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="px-6 py-4 border-t border-border flex justify-end space-x-4">
        <Button size="sm" variant="ghost" :disabled="loading" @click="$emit('close')">取消</Button>
        <Button size="sm" variant="destructive" :disabled="!channelUrl || loading" @click="handleSubmit">
          <Loader2 v-if="loading" class="h-4 w-4 animate-spin" />
          确认添加
        </Button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue';
import { XMarkIcon } from '@heroicons/vue/24/outline';
import { Loader2 } from 'lucide-vue-next'
import { subscribe } from '@/api'
import { Button } from '@/components/ui/button';

const props = defineProps({
  show: Boolean
});

const emit = defineEmits(['close', 'added']);

const channelUrl = ref('');
const loading = ref(false);
const error = ref('');

// 监听 show 属性的变化，当对话框关闭时重置表单
watch(() => props.show, (newVal) => {
  if (!newVal) {
    channelUrl.value = '';
    error.value = '';
  }
});

const handleSubmit = async () => {
  if (!channelUrl.value) return;
  
  loading.value = true;
  error.value = '';
  
  const result = await subscribe(channelUrl.value)

  if (!result.error) {
    emit('added');
    emit('close');
    loading.value = false
    return
  }

  error.value = result.error?.message || '添加频道失败，请检查地址是否正确'
  loading.value = false
};
</script> 
