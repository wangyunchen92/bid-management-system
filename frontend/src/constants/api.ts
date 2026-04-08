const API_PREFIX = '/api/v1';

export const AUTH_API = {
  LOGIN: `${API_PREFIX}/auth/login`,
  LOGOUT: `${API_PREFIX}/auth/logout`,
  REFRESH: `${API_PREFIX}/auth/refresh`,
  ME: `${API_PREFIX}/auth/me`,
  CHANGE_PASSWORD: `${API_PREFIX}/auth/password`,
} as const;

export const SYSTEM_API = {
  DICT_TYPE_LIST: `${API_PREFIX}/system/dict-types`,
  DICT_TYPE_CREATE: `${API_PREFIX}/system/dict-types`,
  DICT_TYPE_UPDATE: (id: number) => `${API_PREFIX}/system/dict-types/${id}`,
  DICT_TYPE_DELETE: (id: number) => `${API_PREFIX}/system/dict-types/${id}`,
  DICT_ITEM_LIST: (typeId: number) => `${API_PREFIX}/system/dict-types/${typeId}/items`,
  DICT_ITEM_CREATE: (typeId: number) => `${API_PREFIX}/system/dict-types/${typeId}/items`,
  DICT_ITEM_UPDATE: (id: number) => `${API_PREFIX}/system/dict-items/${id}`,
  DICT_ITEM_DELETE: (id: number) => `${API_PREFIX}/system/dict-items/${id}`,
  DICT_BY_CODE: (code: string) => `${API_PREFIX}/system/dicts/${code}`,
} as const;
