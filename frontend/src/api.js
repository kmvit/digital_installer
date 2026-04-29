import axios from 'axios';
import { enqueueRequest } from './sync';

function resolveApiBaseUrl() {
  const configured = import.meta.env.VITE_API_URL;
  if (!configured) return '/api';

  try {
    const parsed = new URL(configured, window.location.origin);
    const isLocalApiHost = ['localhost', '127.0.0.1', '::1'].includes(parsed.hostname);
    const isLocalFrontendHost = ['localhost', '127.0.0.1', '::1'].includes(window.location.hostname);

    // В production сборках часто случайно оставляют localhost API.
    // В таком случае отправляем запросы на тот же домен через /api.
    if (isLocalApiHost && !isLocalFrontendHost) {
      return '/api';
    }
  } catch {
    return '/api';
  }

  return configured;
}

const api = axios.create({
  baseURL: resolveApiBaseUrl(),
});
const authBaseUrl = api.defaults.baseURL || '/api';

const NETWORK_ERROR_MESSAGE = 'Не удалось подключиться к серверу. Проверьте, что backend запущен.';

export function getApiErrorMessage(error, fallback = 'Произошла ошибка при выполнении запроса') {
  if (!error?.response) {
    if (error?.code === 'ERR_NETWORK' || error?.message === 'Network Error') {
      return NETWORK_ERROR_MESSAGE;
    }
    return fallback;
  }

  const { status, data } = error.response;

  if (typeof data === 'string' && data.trim()) return data;
  if (data?.error) return data.error;
  if (data?.detail) {
    if (data.detail === 'You do not have permission to perform this action.') {
      return 'Недостаточно прав для выполнения этого действия.';
    }
    return data.detail;
  }
  if (Array.isArray(data?.non_field_errors) && data.non_field_errors.length > 0) {
    return data.non_field_errors[0];
  }

  if (data && typeof data === 'object') {
    for (const [field, value] of Object.entries(data)) {
      if (Array.isArray(value) && value.length > 0) {
        return `${field}: ${value[0]}`;
      }
      if (typeof value === 'string' && value.trim()) {
        return `${field}: ${value}`;
      }
    }
  }

  if (status === 401) return 'Сессия истекла. Войдите в систему заново.';
  if (status === 403) return 'Недостаточно прав для выполнения этого действия.';
  if (status === 404) return 'Данные не найдены.';
  if (status >= 500) return 'Ошибка сервера. Попробуйте позже.';

  return fallback;
}

// JWT interceptor
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Refresh token on 401
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;

    // Refresh token
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      const refresh = localStorage.getItem('refresh_token');
      if (refresh) {
        try {
          const { data } = await axios.post(`${authBaseUrl}/auth/token/refresh/`, {
            refresh,
          });
          localStorage.setItem('access_token', data.access);
          original.headers.Authorization = `Bearer ${data.access}`;
          return api(original);
        } catch {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
        }
      }
    }

    // Офлайн: сохранить POST/PATCH/DELETE в очередь
    if (!error.response && error.code === 'ERR_NETWORK' && original.method !== 'get') {
      const hasFile = original.headers?.['Content-Type']?.includes('multipart');
      await enqueueRequest(original.method, original.url, original.data, hasFile);
      // Вернуть "успех" чтобы UI не ломался
      return {
        data: { _offline: true, _message: 'Сохранено офлайн. Будет отправлено при восстановлении сети.' },
        status: 202,
        _offline: true,
      };
    }

    return Promise.reject(error);
  }
);

// --- Auth ---
export const authApi = {
  login: (username, password) =>
    api.post('/auth/token/', { username, password }),
  me: () => api.get('/auth/me/'),
};

// --- Workday ---
export const workdayApi = {
  clockIn: (formData) =>
    api.post('/workday/clock-in/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  clockOut: (formData) =>
    api.post('/workday/clock-out/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  current: () => api.get('/workday/current/'),
  history: (params) => api.get('/workday/history/', { params }),
  detail: (id) => api.get(`/workday/${id}/detail/`),
  summary: (id) => api.get(`/workday/${id}/summary/`),

  // Сессии
  arrive: (workdayId, formData) =>
    api.post(`/workday/${workdayId}/arrive/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  depart: (workdayId, formData) =>
    api.post(`/workday/${workdayId}/depart/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  sessions: (workdayId) => api.get(`/workday/${workdayId}/sessions/`),

  // Оборудование
  getEquipment: (workdayId) => api.get(`/workday/${workdayId}/equipment/`),
  submitEquipment: (workdayId, data) =>
    api.post(`/workday/${workdayId}/equipment/`, data),
  equipmentDiff: (workdayId) => api.get(`/workday/${workdayId}/equipment/diff/`),

  // GPS-чек бригады
  gpsCheckList: (workdayId) => api.get(`/workday/${workdayId}/gps-check/`),
  gpsCheckSubmit: (workdayId, data) => api.post(`/workday/${workdayId}/gps-check/`, data),

  // Приёмка
  pendingApproval: () => api.get('/workday/pending-approval/'),
  approve: (id, data) => api.post(`/workday/${id}/approve/`, data),
  reject: (id, data) => api.post(`/workday/${id}/reject/`, data),
};

// --- Работы ---
export const worksApi = {
  bySession: (sessionId) => api.get(`/workday/works/by-session/${sessionId}/`),
  create: (sessionId, data) =>
    api.post(`/workday/works/by-session/${sessionId}/`, data),
  update: (workId, data) =>
    api.patch(`/workday/works/${workId}/manage/`, data),
  delete: (workId) =>
    api.delete(`/workday/works/${workId}/manage/`),
  addPhoto: (workId, formData) =>
    api.post(`/workday/works/${workId}/photos/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  start: (workId, formData) =>
    api.post(`/workday/works/${workId}/start/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  finish: (workId, formData) =>
    api.post(`/workday/works/${workId}/finish/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  myAssignments: () => api.get('/workday/works/my-assignments/'),
};

// --- Мобильные эндпоинты (доступны бригадиру/монтажнику) ---
export const mobileApi = {
  myBrigade: () => api.get('/workday/my-brigade/'),
  myObjects: () => api.get('/workday/my-objects/'),
  priceItems: (params = {}) =>
    api.get('/workday/price-items/', { params }),
};

// --- Отчётность ---
export const reportsApi = {
  filters: () => api.get('/workday/reports/filters/'),
  timesheet: (params) => api.get('/workday/reports/timesheet/', { params }),
  piecework: (params) => api.get('/workday/reports/piecework/', { params }),
  completionAct: (params) => api.get('/workday/reports/completion-act/', { params }),
  equipmentAct: (params) => api.get('/workday/reports/equipment-act/', { params }),
  kpi: (params) => api.get('/workday/reports/kpi/', { params }),
  objectTime: (params) => api.get('/workday/reports/object-time/', { params }),
  ks2: (params) => api.get('/workday/reports/ks2/', { params }),
  ks3: (params) => api.get('/workday/reports/ks3/', { params }),
  ks11: (params) => api.get('/workday/reports/ks11/', { params }),
  exportReport: (format, params) =>
    api.get(`/workday/reports/export/${format}/`, {
      params,
      responseType: 'blob',
    }),
};

// --- Дашборды ---
export const dashboardsApi = {
  director: () => api.get('/workday/dashboards/director/'),
  master: () => api.get('/workday/dashboards/master/'),
  pm: () => api.get('/workday/dashboards/pm/'),
  objectProgress: (objectId) => api.get(`/workday/dashboards/object-progress/${objectId}/`),
  objectsWithPlans: () => api.get('/workday/dashboards/objects-with-plans/'),
};

export default api;
