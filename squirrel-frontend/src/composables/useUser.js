import { ref } from 'vue';
import axios from '../utils/axios';

// 创建全局状态
const currentUser = ref(null);
const isAuthenticated = ref(false);
const loading = ref(false);
const error = ref(null);

export function useUser() {
  const register = async (data) => {
    loading.value = true;
    error.value = null;
    try {
      const response = await axios.post('/api/users/register', data);
      if (response.data.code !== 0) {
        throw new Error(response.data.msg);
      }
      return response.data;
    } catch (err) {
      if (err.response?.data) {
        error.value = err.response.data.msg;
        throw new Error(err.response.data.msg);
      }
      error.value = err.message || '注册失败';
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const login = async (data) => {
    loading.value = true;
    error.value = null;
    try {
      const response = await axios.post('/api/users/login', data);
      if (response.data.code !== 0) {
        throw new Error(response.data.msg);
      }
      currentUser.value = response.data.data.user;
      isAuthenticated.value = true;
      return response.data;
    } catch (err) {
      error.value = err.message || '登录失败';
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    currentUser.value = null;
    isAuthenticated.value = false;
  };

  const getCurrentUser = async () => {
    if (!localStorage.getItem('token')) {
      isAuthenticated.value = false;
      currentUser.value = null;
      return null;
    }

    loading.value = true;
    error.value = null;
    try {
      const response = await axios.get('/api/users/me');
      if (response.data.code !== 0) {
        throw new Error(response.data.msg);
      }
      currentUser.value = response.data.data;
      isAuthenticated.value = true;
      return response.data;
    } catch (err) {
      error.value = err.message || '获取用户信息失败';
      if (err.response?.status === 401) {
        logout();
      }
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const updateProfile = async (data) => {
    loading.value = true;
    error.value = null;
    try {
      const response = await axios.put('/api/users/me', data);
      currentUser.value = response.data;
      return response.data;
    } catch (err) {
      error.value = err.response?.data?.detail || '更新用户信息失败';
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const getUserById = async (userId) => {
    loading.value = true;
    error.value = null;
    try {
      const response = await axios.get(`/api/users/${userId}`);
      return response.data;
    } catch (err) {
      error.value = err.response?.data?.detail || '获取用户信息失败';
      throw err;
    } finally {
      loading.value = false;
    }
  };

  return {
    currentUser,
    isAuthenticated,
    loading,
    error,
    register,
    login,
    logout,
    getCurrentUser,
    updateProfile,
    getUserById
  };
} 