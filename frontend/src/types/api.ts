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
