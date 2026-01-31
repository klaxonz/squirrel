// src/utils/axios.js
import axios from 'axios';
import { logoutAndRedirect } from './auth'

const instance = axios.create({
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
instance.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
instance.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    // 如果是后端返回的错误消息
    if (error.response?.data?.msg) {
      error.message = error.response.data.msg;
    }

    // 处理 401 错误
    if (error.response?.status === 401) {
      logoutAndRedirect()
    }
    return Promise.reject(error);
  }
);

export default instance;
