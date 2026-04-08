import axios from 'axios';

const api = axios.create({
  baseURL: 'http://127.0.0.1:8000/api',
});

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
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      const refresh = localStorage.getItem('refresh_token');
      if (refresh) {
        try {
          const { data } = await axios.post('http://127.0.0.1:8000/api/auth/token/refresh/', {
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
};

// --- Мобильные эндпоинты (доступны бригадиру/монтажнику) ---
export const mobileApi = {
  myBrigade: () => api.get('/workday/my-brigade/'),
  myObjects: () => api.get('/workday/my-objects/'),
  priceItems: (priceListId) =>
    api.get('/workday/price-items/', { params: { price_list: priceListId } }),
};

export default api;
