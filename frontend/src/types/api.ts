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
