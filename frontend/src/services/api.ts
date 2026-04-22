import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const workflowsApi = {
  getAll: () => api.get('/workflows'),
  getById: (id: number) => api.get(`/workflows/${id}`),
  create: (data: any) => api.post('/workflows', data),
  getNodes: (id: number) => api.get(`/workflows/${id}/nodes`),
  updateStatus: (id: number, status: string) => api.patch(`/workflows/${id}/status`, { status }),
};

export const tasksApi = {
  getAll: () => api.get('/tasks'),
  getById: (id: number) => api.get(`/tasks/${id}`),
  create: (data: any) => api.post('/tasks', data),
  updateStatus: (id: number, status: string) => api.patch(`/tasks/${id}/status`, { status }),
  delete: (id: number) => api.delete(`/tasks/${id}`),
};

export const productsApi = {
  getAll: (params?: any) => api.get('/products', { params }),
  getById: (id: number) => api.get(`/products/${id}`),
  create: (data: any) => api.post('/products', data),
  togglePublish: (id: number, is_published: boolean) => api.patch(`/products/${id}/publish`, { is_published }),
  delete: (id: number) => api.delete(`/products/${id}`),
};

export const dashboardApi = {
  getStats: () => api.get('/dashboard/stats'),
  getLogs: (params?: any) => api.get('/dashboard/logs', { params }),
};

export default api;
