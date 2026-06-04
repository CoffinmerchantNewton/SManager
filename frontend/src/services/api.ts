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

export const runsApi = {
  list: () => api.get('/runs'),
  plan: (data: any) => api.post('/runs/', data),
  status: (runId: string) => api.get(`/runs/${runId}/status`),
  fnlVerify: (runId: string) => api.post(`/runs/${runId}/fnl-verify`, {}),
  submit: (runId: string, data: any) => api.post(`/runs/${runId}/submit`, data),
  logs: (runId: string, params?: any) => api.get(`/runs/${runId}/logs`, { params }),
  diagnose: (runId: string) => api.get(`/runs/${runId}/diagnose`),
  retry: (runId: string, data: any) => api.post(`/runs/${runId}/retry`, data),
  products: (runId: string) => api.get(`/runs/${runId}/products`),
  syncProducts: (runId: string) => api.post(`/runs/${runId}/sync-products`, {}),
};

export const fnlApi = {
  verifyServer: (data: any) => api.post('/fnl/verify-server', data),
  repair: (data: any) => api.post('/fnl/repair', data),
  coverage: (params?: any) => api.get('/fnl/coverage', { params }),
};

export const agentApi = {
  tick: (data: any) => api.post('/agent/tick', data),
  actions: (params?: any) => api.get('/agent/actions', { params }),
};

export default api;
