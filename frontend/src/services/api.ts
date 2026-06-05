import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

type ApiPayload = Record<string, unknown>;
type ApiParams = Record<string, string | number | boolean | null | undefined>;

export const workflowsApi = {
  getAll: () => api.get('/workflows'),
  getById: (id: number) => api.get(`/workflows/${id}`),
  create: (data: ApiPayload) => api.post('/workflows', data),
  getNodes: (id: number) => api.get(`/workflows/${id}/nodes`),
  updateStatus: (id: number, status: string) => api.patch(`/workflows/${id}/status`, { status }),
};

export const tasksApi = {
  getAll: () => api.get('/tasks'),
  getById: (id: number) => api.get(`/tasks/${id}`),
  create: (data: ApiPayload) => api.post('/tasks', data),
  updateStatus: (id: number, status: string) => api.patch(`/tasks/${id}/status`, { status }),
  runNow: (id: number, data?: ApiPayload) => api.post(`/tasks/${id}/run`, data ?? {}),
  delete: (id: number) => api.delete(`/tasks/${id}`),
};

export const productsApi = {
  getAll: (params?: ApiParams) => api.get('/products', { params }),
  getById: (id: number) => api.get(`/products/${id}`),
  create: (data: ApiPayload) => api.post('/products', data),
  togglePublish: (id: number, is_published: boolean) => api.patch(`/products/${id}/publish`, { is_published }),
  content: (id: number) => api.get(`/products/${id}/content`),
  downloadUrl: (id: number) => `${API_BASE_URL}/products/${id}/download`,
  delete: (id: number) => api.delete(`/products/${id}`),
};

export const dashboardApi = {
  getStats: () => api.get('/dashboard/stats'),
  getOverview: (params?: ApiParams) => api.get('/dashboard/overview', { params }),
  getLogs: (params?: ApiParams) => api.get('/dashboard/logs', { params }),
};

export const runsApi = {
  list: () => api.get('/runs'),
  plan: (data: ApiPayload) => api.post('/runs/', data),
  status: (runId: string) => api.get(`/runs/${runId}/status`),
  fnlVerify: (runId: string) => api.post(`/runs/${runId}/fnl-verify`, {}),
  submit: (runId: string, data: ApiPayload) => api.post(`/runs/${runId}/submit`, data),
  logs: (runId: string, params?: ApiParams) => api.get(`/runs/${runId}/logs`, { params }),
  diagnose: (runId: string) => api.get(`/runs/${runId}/diagnose`),
  context: (runId: string, params?: ApiParams) => api.get(`/runs/${runId}/context`, { params }),
  retry: (runId: string, data: ApiPayload) => api.post(`/runs/${runId}/retry`, data),
  cancel: (runId: string, data: ApiPayload) => api.post(`/runs/${runId}/cancel`, data),
  products: (runId: string) => api.get(`/runs/${runId}/products`),
  syncProducts: (runId: string) => api.post(`/runs/${runId}/sync-products`, {}),
};

export const fnlApi = {
  verifyServer: (data: ApiPayload) => api.post('/fnl/verify-server', data),
  repair: (data: ApiPayload) => api.post('/fnl/repair', data),
  coverage: (params?: ApiParams) => api.get('/fnl/coverage', { params }),
};

export const agentApi = {
  tick: (data: ApiPayload) => api.post('/agent/tick', data),
  actions: (params?: ApiParams) => api.get('/agent/actions', { params }),
};

export default api;
