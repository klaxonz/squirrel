<template>
  <div class="min-h-screen flex items-center justify-center bg-[#0f0f0f] px-4">
    <div class="max-w-md w-full space-y-8">
      <!-- Logo -->
      <div class="flex flex-col items-center">
        <img src="/squirrel-icon.svg" class="w-16 h-16" alt="Logo">
        <h2 class="mt-6 text-3xl font-bold text-white">登录到 Squirrel</h2>
      </div>

      <!-- 登录表单 -->
      <form class="mt-8 space-y-6" @submit.prevent="handleSubmit">
        <div class="space-y-4">
          <div>
            <label for="email" class="sr-only">邮箱</label>
            <input
              id="email"
              v-model="form.email"
              type="email"
              required
              class="appearance-none relative block w-full px-3 py-2 border border-[#272727] bg-[#1f1f1f] placeholder-[#aaaaaa] text-white rounded focus:outline-none focus:ring-[#cc0000] focus:border-[#cc0000] focus:z-10 sm:text-sm"
              placeholder="邮箱"
            >
          </div>
          <div>
            <label for="password" class="sr-only">密码</label>
            <input
              id="password"
              v-model="form.password"
              type="password"
              required
              class="appearance-none relative block w-full px-3 py-2 border border-[#272727] bg-[#1f1f1f] placeholder-[#aaaaaa] text-white rounded focus:outline-none focus:ring-[#cc0000] focus:border-[#cc0000] focus:z-10 sm:text-sm"
              placeholder="密码"
            >
          </div>
        </div>

        <div>
          <button
            type="submit"
            :disabled="loading"
            class="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-[#cc0000] hover:bg-[#aa0000] focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span v-if="loading">登录中...</span>
            <span v-else>登录</span>
          </button>
        </div>

        <div class="flex items-center justify-center">
          <router-link
            to="/register"
            class="text-sm text-[#aaaaaa] hover:text-white transition-colors"
          >
            还没有账号？立即注册
          </router-link>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import useCustomToast from '../composables/useToast';
import { useUser } from '../composables/useUser';

const router = useRouter();
const { displayToast } = useCustomToast();
const { login } = useUser();
const loading = ref(false);
const form = ref({
  email: '',
  password: ''
});

const handleSubmit = async () => {
  loading.value = true;
  try {
    const response = await login(form.value);
    localStorage.setItem('token', response.data.access_token);
    await router.push('/');
  } catch (error) {
    displayToast(error.response?.data?.msg || '登录失败', { type: 'error' });
  } finally {
    loading.value = false;
  }
};
</script> 