const API_PREFIX = '/api/v1';

export const AUTH_API = {
  LOGIN: `${API_PREFIX}/auth/login`,
  LOGOUT: `${API_PREFIX}/auth/logout`,
  REFRESH: `${API_PREFIX}/auth/refresh`,
  ME: `${API_PREFIX}/auth/me`,
  CHANGE_PASSWORD: `${API_PREFIX}/auth/password`,
} as const;
