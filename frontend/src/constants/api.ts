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
  // 部门
  DEPT_TREE: `${API_PREFIX}/system/departments/tree`,
  DEPT_CREATE: `${API_PREFIX}/system/departments`,
  DEPT_DETAIL: (id: number) => `${API_PREFIX}/system/departments/${id}`,
  DEPT_UPDATE: (id: number) => `${API_PREFIX}/system/departments/${id}`,
  DEPT_DELETE: (id: number) => `${API_PREFIX}/system/departments/${id}`,
  // 用户
  USER_LIST: `${API_PREFIX}/system/users`,
  USER_CREATE: `${API_PREFIX}/system/users`,
  USER_UPDATE: (id: number) => `${API_PREFIX}/system/users/${id}`,
  USER_DELETE: (id: number) => `${API_PREFIX}/system/users/${id}`,
  USER_RESET_PWD: (id: number) => `${API_PREFIX}/system/users/${id}/reset-password`,
  // 角色
  ROLE_LIST: `${API_PREFIX}/system/roles`,
  ROLE_CREATE: `${API_PREFIX}/system/roles`,
  ROLE_UPDATE: (id: number) => `${API_PREFIX}/system/roles/${id}`,
  ROLE_DELETE: (id: number) => `${API_PREFIX}/system/roles/${id}`,
  USER_ROLES: (id: number) => `${API_PREFIX}/system/users/${id}/roles`,
  ASSIGN_ROLES: (id: number) => `${API_PREFIX}/system/users/${id}/roles`,
} as const;

export const APPROVAL_API = {
  SUBMIT: `${API_PREFIX}/approval/submit`,
  MY_PENDING: `${API_PREFIX}/approval/my-pending`,
  MY_INITIATED: `${API_PREFIX}/approval/my-initiated`,
  DETAIL: (id: number) => `${API_PREFIX}/approval/${id}`,
  APPROVE: (id: number) => `${API_PREFIX}/approval/${id}/approve`,
  REJECT: (id: number) => `${API_PREFIX}/approval/${id}/reject`,
  TRANSFER: (id: number) => `${API_PREFIX}/approval/${id}/transfer`,
} as const;

export const DECISION_API = {
  LIST: `${API_PREFIX}/decision/list`,
  CREATE: `${API_PREFIX}/decision`,
  DETAIL: (id: number) => `${API_PREFIX}/decision/${id}`,
  UPDATE: (id: number) => `${API_PREFIX}/decision/${id}`,
  DELETE: (id: number) => `${API_PREFIX}/decision/${id}`,
  BY_TENDER: (tenderId: number) => `${API_PREFIX}/decision/by-tender/${tenderId}`,
} as const;

export const OPENING_API = {
  LIST: `${API_PREFIX}/opening/list`,
  CREATE: `${API_PREFIX}/opening`,
  DETAIL: (id: number) => `${API_PREFIX}/opening/${id}`,
  UPDATE: (id: number) => `${API_PREFIX}/opening/${id}`,
  DELETE: (id: number) => `${API_PREFIX}/opening/${id}`,
  BY_TENDER: (tenderId: number) => `${API_PREFIX}/opening/by-tender/${tenderId}`,
} as const;

export const LIBRARY_API = {
  // 资质证书
  QUAL_LIST: `${API_PREFIX}/library/qualifications`,
  QUAL_CREATE: `${API_PREFIX}/library/qualifications`,
  QUAL_UPDATE: (id: number) => `${API_PREFIX}/library/qualifications/${id}`,
  QUAL_DELETE: (id: number) => `${API_PREFIX}/library/qualifications/${id}`,
  // 业绩案例
  ACHV_LIST: `${API_PREFIX}/library/achievements`,
  ACHV_CREATE: `${API_PREFIX}/library/achievements`,
  ACHV_UPDATE: (id: number) => `${API_PREFIX}/library/achievements/${id}`,
  ACHV_DELETE: (id: number) => `${API_PREFIX}/library/achievements/${id}`,
  // 人员证书
  PCERT_LIST: `${API_PREFIX}/library/personnel-certs`,
  PCERT_CREATE: `${API_PREFIX}/library/personnel-certs`,
  PCERT_UPDATE: (id: number) => `${API_PREFIX}/library/personnel-certs/${id}`,
  PCERT_DELETE: (id: number) => `${API_PREFIX}/library/personnel-certs/${id}`,
  // 产品/设备
  PROD_LIST: `${API_PREFIX}/library/products`,
  PROD_CREATE: `${API_PREFIX}/library/products`,
  PROD_UPDATE: (id: number) => `${API_PREFIX}/library/products/${id}`,
  PROD_DELETE: (id: number) => `${API_PREFIX}/library/products/${id}`,
} as const;

export const BID_API = {
  // 项目
  PROJECT_LIST: `${API_PREFIX}/bid/projects`,
  PROJECT_CREATE: `${API_PREFIX}/bid/projects`,
  PROJECT_DETAIL: (id: number) => `${API_PREFIX}/bid/projects/${id}`,
  PROJECT_UPDATE: (id: number) => `${API_PREFIX}/bid/projects/${id}`,
  PROJECT_DELETE: (id: number) => `${API_PREFIX}/bid/projects/${id}`,
  PROJECT_BY_TENDER: (tenderId: number) => `${API_PREFIX}/bid/projects/by-tender/${tenderId}`,
  // 章节
  SECTION_TREE: (projectId: number) => `${API_PREFIX}/bid/projects/${projectId}/sections`,
  SECTION_CREATE: `${API_PREFIX}/bid/sections`,
  SECTION_DETAIL: (id: number) => `${API_PREFIX}/bid/sections/${id}`,
  SECTION_UPDATE: (id: number) => `${API_PREFIX}/bid/sections/${id}`,
  SECTION_DELETE: (id: number) => `${API_PREFIX}/bid/sections/${id}`,
  SECTION_REORDER: (projectId: number) => `${API_PREFIX}/bid/projects/${projectId}/sections/reorder`,
  SECTION_AI_GENERATE: (sectionId: number) => `${API_PREFIX}/bid/sections/${sectionId}/ai-generate`,
  SECTION_AI_GENERATE_STREAM: (sectionId: number) => `${API_PREFIX}/bid/sections/${sectionId}/ai-generate-stream`,
  PROJECT_CHECK: (projectId: number) => `${API_PREFIX}/bid/projects/${projectId}/check`,
  PROJECT_EXPORT: (projectId: number) => `${API_PREFIX}/bid/projects/${projectId}/export`,
} as const;

export const TENDER_DOC_API = {
  UPLOAD: `${API_PREFIX}/tender-doc/upload`,
  DETAIL: (id: number) => `${API_PREFIX}/tender-doc/${id}`,
  BY_PROJECT: (projectId: number) => `${API_PREFIX}/tender-doc/by-project/${projectId}`,
  BY_TENDER: (tenderId: number) => `${API_PREFIX}/tender-doc/by-tender/${tenderId}`,
  DELETE: (id: number) => `${API_PREFIX}/tender-doc/${id}`,
} as const;

export const TENDER_API = {
  LIST: `${API_PREFIX}/tender/list`,
  CREATE: `${API_PREFIX}/tender`,
  DETAIL: (id: number) => `${API_PREFIX}/tender/${id}`,
  UPDATE: (id: number) => `${API_PREFIX}/tender/${id}`,
  DELETE: (id: number) => `${API_PREFIX}/tender/${id}`,
  UPDATE_STATUS: (id: number) => `${API_PREFIX}/tender/${id}/status`,
  UPDATE_FOLLOWER: (id: number) => `${API_PREFIX}/tender/${id}/follower`,
  CALENDAR: `${API_PREFIX}/tender/calendar`,
  STATS: `${API_PREFIX}/tender/stats`,
  EXPIRING: `${API_PREFIX}/tender/expiring`,
} as const;
