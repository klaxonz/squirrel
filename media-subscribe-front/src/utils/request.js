import axios from './axios';

export const handleRequest = async (promise) => {
  try {
    const response = await promise;
    if (response.data.code === 0) {
      return {
        data: response.data.data,
        error: null
      };
    }
    return {
      data: null,
      error: response.data.msg
    };
  } catch (err) {
    return {
      data: null,
      error: '网络请求失败'
    };
  }
};

export const get = (url, params) => handleRequest(axios.get(url, { params }));
export const post = (url, data) => handleRequest(axios.post(url, data)); 