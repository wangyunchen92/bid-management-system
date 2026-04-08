/** 统一 API 响应 */
interface ApiResponse<T = unknown> {
  code: number;
  message: string;
  data: T;
  timestamp: number;
}

/** 分页响应 */
interface PaginatedData<T = unknown> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

/** 当前用户 */
interface CurrentUser {
  id: number;
  username: string;
  real_name: string;
  phone?: string;
  email?: string;
  avatar?: string;
  role: string;
  permissions: string[];
}

/** 登录参数 */
interface LoginParams {
  username: string;
  password: string;
}

/** 登录结果 */
interface LoginResult {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

/** 字典类型 */
interface DictType {
  id: number;
  dict_name: string;
  dict_code: string;
  description?: string;
  status: number;
  created_at?: string;
}

/** 字典项 */
interface DictItem {
  id: number;
  dict_type_id: number;
  item_label: string;
  item_value: string;
  sort_order: number;
  status: number;
  description?: string;
}

/** 部门 */
interface Department {
  id: number;
  dept_name: string;
  dept_code: string;
  parent_id?: number;
  leader_id?: number;
  sort_order: number;
  status: number;
  created_at?: string;
  children?: Department[];
}

/** 用户角色信息 */
interface UserRoleInfo {
  role_id: number;
  role_name: string;
  role_code: string;
}

/** 系统用户 */
interface SystemUser {
  id: number;
  username: string;
  real_name: string;
  phone?: string;
  email?: string;
  avatar?: string;
  dept_id?: number;
  dept_name?: string;
  position?: string;
  role: string;
  status: number;
  last_login_at?: string;
  created_at?: string;
  roles?: UserRoleInfo[];
}

/** 角色 */
interface SysRole {
  id: number;
  role_name: string;
  role_code: string;
  description?: string;
  sort_order: number;
  status: number;
  created_at?: string;
}
