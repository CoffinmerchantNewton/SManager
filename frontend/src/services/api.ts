import axios from 'axios';

const configuredApiUrl = import.meta.env.VITE_API_URL;
const API_BASE_URL =
  import.meta.env.PROD && configuredApiUrl?.includes('localhost') ? '/api/v1' : configuredApiUrl || '/api/v1';
const AUTH_TOKEN_KEY = 'smanager.auth.token';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = getAuthToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      clearAuthToken();
      if (window.location.pathname.startsWith('/admin')) {
        window.location.assign(`/login?from=${encodeURIComponent(window.location.pathname)}`);
      }
    }
    return Promise.reject(error);
  },
);

type ApiPayload = Record<string, unknown>;
type ApiParams = Record<string, string | number | boolean | null | undefined>;

export function getAuthToken() {
  return window.localStorage.getItem(AUTH_TOKEN_KEY);
}

export function setAuthToken(token: string) {
  window.localStorage.setItem(AUTH_TOKEN_KEY, token);
}

export function clearAuthToken() {
  window.localStorage.removeItem(AUTH_TOKEN_KEY);
}

export const authApi = {
  login: (username: string, password: string) => api.post('/auth/login', { username, password }),
  me: () => api.get('/auth/me'),
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
  list: (params?: ApiParams) => api.get('/runs', { params }),
  plan: (data: ApiPayload) => api.post('/runs/', data),
  status: (runKey: string) => api.get(`/runs/${encodeRunKey(runKey)}/status`),
  fnlVerify: (runKey: string) => api.post(`/runs/${encodeRunKey(runKey)}/fnl-verify`, {}),
  submit: (runKey: string, data: ApiPayload) => api.post(`/runs/${encodeRunKey(runKey)}/submit`, data),
  logs: (runKey: string, params?: ApiParams) => api.get(`/runs/${encodeRunKey(runKey)}/logs`, { params }),
  diagnose: (runKey: string) => api.get(`/runs/${encodeRunKey(runKey)}/diagnose`),
  context: (runKey: string, params?: ApiParams) => api.get(`/runs/${encodeRunKey(runKey)}/context`, { params }),
  retry: (runKey: string, data: ApiPayload) => api.post(`/runs/${encodeRunKey(runKey)}/retry`, data),
  cancel: (runKey: string, data: ApiPayload) => api.post(`/runs/${encodeRunKey(runKey)}/cancel`, data),
  products: (runKey: string) => api.get(`/runs/${encodeRunKey(runKey)}/products`),
  syncProducts: (runKey: string) => api.post(`/runs/${encodeRunKey(runKey)}/sync-products`, {}),
};

export const serverApi = {
  health: () => api.get('/server/health'),
  status: () => api.get('/server/status'),
  config: () => api.get('/server/config'),
  updateConfig: (data: ApiPayload) => api.put('/server/config', data),
  regions: () => api.get('/server/regions'),
  slurmJobs: () => api.get('/server/slurm/jobs'),
  tick: (params?: ApiParams) => api.post('/server/tick', null, { params }),
  submitForecast: (data: ApiPayload) => api.post('/server/forecast/submit', data),
  enableSchedule: () => api.post('/server/schedule/enable'),
  disableSchedule: () => api.post('/server/schedule/disable'),
  reconcile: () => api.post('/server/reconcile'),
};

export const fnlApi = {
  verifyServer: (data: ApiPayload) => api.post('/fnl/verify-server', data),
  repair: (data?: ApiPayload) => api.post('/fnl/repair', data ?? {}),
  repairOne: (filename: string, params?: ApiParams) =>
    api.post(`/fnl/repair/${encodeURIComponent(filename)}`, null, { params }),
  downloadOne: (filename: string, params?: ApiParams) =>
    api.post(`/fnl/download/${encodeURIComponent(filename)}`, null, { params }),
  coverage: (params?: ApiParams) => api.get('/fnl/coverage', { params }),
  repairRequests: (params?: ApiParams) => api.get('/fnl/repair-requests', { params }),
};

export function encodeRunKey(runKey: string) {
  return runKey.split('/').map((part) => encodeURIComponent(part)).join('/');
}

export function buildRunKey(season: string, region: string, runId: string) {
  return `${season}/${region}/${runId}`;
}

export function runDetailPath(run: { run_key?: string; season?: string; region?: string; run_id?: string }) {
  if (run.run_key) {
    return `/admin/runs/${run.run_key.split('/').map((part) => encodeURIComponent(part)).join('/')}`;
  }
  if (run.season && run.region && run.run_id) {
    return `/admin/runs/${encodeURIComponent(run.season)}/${encodeURIComponent(run.region)}/${encodeURIComponent(run.run_id)}`;
  }
  return `/admin/runs/${encodeURIComponent(run.run_id || '')}`;
}

export default api;
