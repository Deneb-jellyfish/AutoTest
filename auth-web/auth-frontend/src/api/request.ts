import axios, { type AxiosRequestConfig } from 'axios';
import type { ApiResult } from './types';

const baseURL = import.meta.env.VITE_API_BASE || '/api/zdmj';

const instance = axios.create({
  baseURL,
  timeout: 15000
});

instance.interceptors.request.use(config => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export async function request<T>(config: AxiosRequestConfig): Promise<{
  data: T | null;
  error: string | null;
}> {
  try {
    const response = await instance.request<ApiResult<T>>(config);
    const body = response.data;
    if (body.code === 0) {
      return { data: body.data, error: null };
    }
    return { data: null, error: body.msg || '请求失败' };
  } catch (e: unknown) {
    const err = e as { response?: { data?: ApiResult<unknown> }; message?: string };
    const msg = err.response?.data?.msg || err.message || '网络错误';
    return { data: null, error: msg };
  }
}
