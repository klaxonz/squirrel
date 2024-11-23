// src/utils/axios.js
import axios from 'axios';

const instance = axios.create({
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
instance.interceptors.request.use(
  (config) => {
    // 可以在这里添加授权令牌
    // config.headers.Authorization = `Bearer ${token}`;
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
    // 可以在这里进行错误处理
    return Promise.reject(error);
  }
);

export default instance;
